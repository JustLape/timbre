"""Katalogas atmintyje. Specifikacijos 5 skyrius.

Naudojamas visuose testuose: jokio failo, tinklo ar duomenų bazės, todėl
testai greiti ir vienas kito nepaveikia.

Čia gyvena visa katalogo užklausų logika (matomumas, filtrai, rikiavimas pagal
vektorių). `JsonCatalogRepository` jos NEDUBLIUOJA — jis šį adapterį naudoja
vidumi, o pats tik nuskaito ir įrašo failą.
"""

from collections.abc import Sequence

from ..domain.constants import INSTRUMENTAL_THRESHOLD, MOOD_INSTRUMENTAL
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

    def _visible(self, tenant_id: str) -> list[Track]:
        """VIENINTELĖ vieta, kur sudaroma kliento matomumo sąlyga.

        Visi skaitymo ir keitimo metodai kviečia būtent šią funkciją, todėl
        „užmiršti sąlygą vienoje užklausoje" fiziškai nebėra kur. Tai
        programinė, ne duomenų bazės lygio apsauga — duomenų bazės eilučių
        lygio saugumas (RLS) numatytas III etapui.
        """
        return [track for track in self._tracks if track.tenant_id == tenant_id]

    def get_track(self, tenant_id: str, song_id: str) -> Track | None:
        for track in self._visible(tenant_id):
            if track.song_id == song_id:
                return track
        return None

    def fetch_candidates(
        self,
        tenant_id: str,
        query: Track,
        filters: FilterSpec,
        pool_size: int,
    ) -> CandidatePool:
        visible = [
            track
            for track in self._visible(tenant_id)
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
            survivors_per_filter=survivors_per_filter,
        )

    def remove_track(self, tenant_id: str, song_id: str) -> bool:
        """Pašalina dainą tik tada, kai ji priklauso TAM PAČIAM klientui."""
        for track in self._visible(tenant_id):
            if track.song_id == song_id:
                self._tracks.remove(track)
                return True
        return False

    def all_tracks(self) -> list[Track]:
        """Visos dainos be jokio kliento filtro — tik failo įrašymui."""
        return list(self._tracks)
