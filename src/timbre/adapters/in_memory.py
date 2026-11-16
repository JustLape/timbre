"""Katalogas atmintyje. Specifikacijos 5 skyrius.

Naudojamas visuose testuose: jokio failo, tinklo ar duomenų bazės, todėl
testai greiti ir vienas kito nepaveikia.

Čia gyvena visa katalogo užklausų logika (matomumas, filtrai, rikiavimas pagal
vektorių). `JsonCatalogRepository` jos NEDUBLIUOJA — jis šį adapterį naudoja
vidumi, o pats tik nuskaito ir įrašo failą.
"""

from collections.abc import Sequence

from ..domain.constants import (
    INSTRUMENTAL_THRESHOLD,
    MOOD_INSTRUMENTAL,
    SHARED_CATALOG,
)
from ..domain.models import CandidatePool, FilterSpec, Track
from ..domain.scoring import cosine


def passes_bpm(track: Track, filters: FilterSpec) -> bool:
    """Ar daina praeina tempo filtrą? Nenurodytas filtras praleidžia visas."""
    bpm = track.features.bpm
    if filters.bpm_min is not None and bpm < filters.bpm_min:
        return False
    if filters.bpm_max is not None and bpm > filters.bpm_max:
        return False
    return True


def passes_instrumental(track: Track, filters: FilterSpec) -> bool:
    """Ar daina praeina instrumentalumo filtrą?

    Instrumentalumas nėra atskiras laukas — jis skaitomas iš nuotaikų, kad
    būtų vienas tiesos šaltinis, o ne du, kurie gali nesutapti.
    """
    if not filters.instrumental_only:
        return True
    return track.features.moods.get(MOOD_INSTRUMENTAL, 0.0) >= INSTRUMENTAL_THRESHOLD


class InMemoryCatalog:
    """Katalogas, laikomas Python sąraše."""

    def __init__(self, tracks: Sequence[Track]) -> None:
        self._tracks: list[Track] = list(tracks)

    # TRYS matomumo sritys, ne viena. Jos skiriasi sąmoningai, nes klausimai
    # skirtingi: „ką galiu paimti kaip užklausą", „ką galiu gauti atsakyme" ir
    # „ką galiu pakeisti". Visi viešieji metodai kviečia būtent šias funkcijas,
    # todėl „užmiršti sąlygą vienoje užklausoje" fiziškai nebėra kur.
    #
    # Tai programinė, ne duomenų bazės lygio apsauga — eilučių lygio saugumas
    # (RLS) numatytas III etapui.

    def _readable(self, tenant_id: str) -> list[Track]:
        """UŽKLAUSAI: bendras katalogas ir paties kliento įkeltos dainos."""
        return [
            track
            for track in self._tracks
            if track.tenant_id in (SHARED_CATALOG, tenant_id)
        ]

    def _searchable(self) -> list[Track]:
        """ATSAKYMUI: tik bendras katalogas.

        Kliento įkelta daina niekada negrįžta rezultatuose — nei svetimam
        klientui, nei jam pačiam. Dėl to įkelta daina negali nutekėti kitam
        net netiesiogiai, per panašumo rezultatą.
        """
        return [track for track in self._tracks if track.tenant_id == SHARED_CATALOG]

    def _owned(self, tenant_id: str) -> list[Track]:
        """KEITIMUI: tik paties kliento įkeltos dainos.

        Bendras katalogas yra tik skaitomas — jo nekeičia niekas, įskaitant
        neprisijungusį naudotoją, kurio tenant_id ir yra `bendras`.
        """
        if tenant_id == SHARED_CATALOG:
            return []
        return [track for track in self._tracks if track.tenant_id == tenant_id]

    def get_track(self, tenant_id: str, song_id: str) -> Track | None:
        for track in self._readable(tenant_id):
            if track.song_id == song_id:
                return track
        return None

    def find_by_title_artist(
        self, tenant_id: str, title: str, artist: str | None = None
    ) -> list[Track]:
        """Randa dainas pagal pavadinimą ir, jei nurodytas, atlikėją.

        Grąžinamas SĄRAŠAS, o ne viena daina, ir tai sąmoningas sprendimas.
        Tikruose kataloguose tas pats pavadinimas su tuo pačiu atlikėju
        atitinka daug įrašų: patikrinta, kad „Billie Jean" ir Michael Jackson
        MusicBrainz duomenyse duoda 152 įrašus, o kanoninis yra tik penktas.
        Tyliai paėmus pirmą būtų ieškoma panašių į visai kitą kūrinį, ir
        naudotojas apie tai nesužinotų. Pasirinkimą palieka kviečiančiajam.

        Lyginama per casefold().strip(), kad didžiosios raidės ir tarpai
        kraštuose nekliudytų.
        """
        wanted_title = title.casefold().strip()
        wanted_artist = artist.casefold().strip() if artist is not None else None
        found = [
            track
            for track in self._readable(tenant_id)
            if track.title.casefold().strip() == wanted_title
            and (
                wanted_artist is None
                or track.artist.casefold().strip() == wanted_artist
            )
        ]
        found.sort(key=lambda track: track.song_id)
        return found

    def fetch_candidates(
        self,
        tenant_id: str,
        query: Track,
        filters: FilterSpec,
        pool_size: int,
    ) -> CandidatePool:
        visible = [
            track
            for track in self._searchable()
            if track.song_id != query.song_id
        ]

        # Kiekvienam filtrui ATSKIRAI, o ne pakopomis: jei skaičiuotume
        # pakopomis, paskutinis filtras visada atrodytų ribojantis labiausiai
        # vien dėl eilės tvarkos.
        survivors_per_filter = {
            "bpm": sum(1 for track in visible if passes_bpm(track, filters)),
            "instrumental": sum(
                1 for track in visible if passes_instrumental(track, filters)
            ),
        }

        # Filtrai taikomi PAIEŠKOS METU, prieš balų skaičiavimą, o ne po jo.
        matching = [
            track
            for track in visible
            if passes_bpm(track, filters) and passes_instrumental(track, filters)
        ]
        matching.sort(
            key=lambda track: (
                -cosine(query.features.vector, track.features.vector),
                track.song_id,
            )
        )

        return CandidatePool(
            candidates=matching[:pool_size],
            visible_count=len(visible),
            survivors_per_filter=survivors_per_filter,
        )

    def remove_track(self, tenant_id: str, song_id: str) -> bool:
        """Pašalina dainą tik tada, kai klientas ją pats įkėlė.

        Bendro katalogo dainos nepašalina niekas, nors ji puikiai matoma
        paieškoje: matyti ir keisti yra du skirtingi dalykai.
        """
        for track in self._owned(tenant_id):
            if track.song_id == song_id:
                self._tracks.remove(track)
                return True
        return False

    def all_tracks(self) -> list[Track]:
        """Visos dainos be jokio kliento filtro — tik failo įrašymui."""
        return list(self._tracks)
