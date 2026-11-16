"""Čia surašyta VISA PAIEŠKOS EIGA nuo pradžios iki pabaigos.

KĄ ŠIS FAILAS DARO
------------------
Jis pats beveik nieko neskaičiuoja. Jo darbas — teisinga tvarka pakviesti
kitus ir perduoti rezultatus toliau. Maždaug kaip receptas: jame surašyta,
ką daryti ir kada, bet pjausto ir verda kiti failai.

Devyni žingsniai, visada ta pačia tvarka:

    1. Patikrinti svorius               -> scoring.validate_weights
    2. Patikrinti filtrus ir limitus    -> čia pat, _validate_filters
    3. Rasti užklausos dainą            -> repo.get_track
    4. Paimti kandidatus su filtrais    -> repo.fetch_candidates
    5. Suskaičiuoti kandidatų           -> čia pat, _compute_pairwise
       tarpusavio panašumus
    6. Suskaičiuoti balus ir surikiuoti -> scoring.score_all
    7. Dublikatai, atlikėjas, įvairovė  -> selection.*
    8. Paaiškinimai                     -> explain.explain
    9. Surinkti atsakymą                -> models.SearchResult

Pirmi du žingsniai yra patikros. Jos daromos PIRMA sąmoningai: nėra prasmės
skaityti katalogą, jei užklausa vis tiek bloga.

KODĖL ČIA NEŽINOMA, IŠ KUR ATEINA DAINOS
----------------------------------------
Šis failas niekada nemini nei JSON, nei duomenų bazės. Jis žino tik, kad
gaus kažką, kas moka tris dalykus: `get_track`, `fetch_candidates` ir
`remove_track`. Tas „kažkas" paduodamas į konstruktorių.

Praktinė nauda: testuose paduodamas atminties katalogas (greitas, nieko
neskaito iš disko), o paleidžiant — JSON failas. Tas pats kodas, skirtingi
duomenų šaltiniai. Norint pereiti prie duomenų bazės, užtektų parašyti dar
vieną tokį „kažką" ir pakeisti vieną eilutę cli.py.

Terminas, kurio ieškotum vadovėlyje: priklausomybių injekcija.

VIENINTELIS DALYKAS, KURĮ ŠIS FAILAS TIKRAI SKAIČIUOJA
------------------------------------------------------
5 žingsnis: kiek kandidatai panašūs vienas į kitą (`pairwise`).

To reikia dublikatams ir įvairovei. Skaičiuojama būtent čia, o ne
`domain/selection.py`, kad `domain` galėtų tuos skaičius GAUTI. Kodėl tai
svarbu — paaiškinta `domain/selection.py` viršuje.
"""

from collections.abc import Mapping

from ..domain.constants import (
    DEFAULT_ARTIST_LIMIT,
    DEFAULT_LIMIT,
    DEFAULT_WEIGHTS,
    POOL_SIZE,
)
from ..domain.errors import ErrorCode, TimbreError
from ..domain.explain import explain
from ..domain.models import (
    CandidatePool,
    FilterSpec,
    ResultItem,
    SearchResult,
    Track,
)
from ..domain.scoring import (
    DEFAULT_STRATEGIES,
    CriterionStrategy,
    cosine,
    score_all,
    validate_weights,
)
from ..domain.selection import (
    apply_artist_limit,
    pairwise_key,
    remove_duplicates,
    select_diverse,
)
from ..ports.repository import CatalogRepository


class SearchService:
    def __init__(
        self,
        repo: CatalogRepository,
        strategies: Mapping[str, CriterionStrategy] | None = None,
    ) -> None:
        self._repo = repo
        self._strategies = strategies if strategies is not None else DEFAULT_STRATEGIES

    def search(
        self,
        *,
        tenant_id: str,
        song_id: str,
        filters: FilterSpec,
        weights: Mapping[str, float] | None = None,
        limit: int = DEFAULT_LIMIT,
        artist_limit: int = DEFAULT_ARTIST_LIMIT,
    ) -> SearchResult:
        """Visas paieškos scenarijus nuo įvesties iki rezultato.

        `tenant_id` yra keyword-only ir be numatytosios reikšmės — kliento
        atskyrimas neturi priklausyti nuo to, ar kas nors nepamiršo parametro.
        """
        effective_weights = dict(DEFAULT_WEIGHTS if weights is None else weights)

        # 1. Svoriai.
        validate_weights(effective_weights, self._strategies)

        # 2. Filtrai ir limitai.
        self._validate_filters(filters, limit, artist_limit)

        # 3. Užklausos daina.
        query = self._repo.get_track(tenant_id, song_id)
        if query is None:
            raise TimbreError(
                ErrorCode.DAINA_NERASTA,
                f"dainos {song_id!r} kliento {tenant_id!r} kataloge nėra",
            )

        # 4. Kandidatai; filtrai pritaikomi paieškos metu.
        pool = self._repo.fetch_candidates(tenant_id, query, filters, POOL_SIZE)
        self._check_feature_sets(query, pool.candidates)

        # 5. Kandidatų tarpusavio kosinusai — `app` sluoksnio darbas.
        pairwise = self._compute_pairwise(pool.candidates)

        # 6. Balai ir rikiavimas; antrinis raktas song_id, kad eilė būtų determinuota.
        scored = score_all(query, pool.candidates, effective_weights, self._strategies)
        scored.sort(key=lambda item: (-item.total_score, item.track.song_id))

        # 7. Atranka: dublikatai -> atlikėjo limitas -> įvairovė.
        after_duplicates, removed_duplicates = remove_duplicates(scored, pairwise)
        after_artist, removed_artist = apply_artist_limit(
            after_duplicates, query.artist, artist_limit
        )
        selected = select_diverse(after_artist, pairwise, limit)

        # 8. Paaiškinimai.
        items = [
            ResultItem(
                track=item.track,
                final_score=item.total_score,
                criterion_scores=item.criterion_scores,
                explanations=explain(query, item),
            )
            for item in selected
        ]

        # 9. Rezultatas.
        return SearchResult(
            items=items,
            dalinis_rezultatas=len(items) < limit,
            labiausiai_ribojes_filtras=self._most_restricting_filter(pool),
            removal_counts={
                "duplicates": removed_duplicates,
                "artist_limit": removed_artist,
                "diversity": len(after_artist) - len(selected),
            },
        )

    def remove(self, *, tenant_id: str, song_id: str) -> None:
        """Pašalina kliento dainą iš katalogo.

        Svetimo kliento daina tam klientui tiesiog neegzistuoja, todėl
        grąžinamas tas pats `DAINA_NERASTA`, kaip ir visai nesančiai dainai.
        Taip neatskleidžiama, kad tas `song_id` kataloge yra.
        """
        if not self._repo.remove_track(tenant_id, song_id):
            raise TimbreError(
                ErrorCode.DAINA_NERASTA,
                f"dainos {song_id!r} kliento {tenant_id!r} kataloge nėra",
            )

    def find_song(
        self, *, tenant_id: str, title: str, artist: str | None = None
    ) -> list[Track]:
        """Randa užklausos dainą pagal pavadinimą, kai song_id nežinomas.

        Tai „nuorodos" eiga be jokio tinklo: iš nuorodos gaunamas atlikėjas ir
        pavadinimas, o čia jie paverčiami į kataloge esančią dainą. Būtent
        todėl paieška be paskyros apskritai įmanoma — žmogus nežino song_id.

        Nieko neradus keliama DAINA_NERASTA. Radus daugiau nei vieną,
        grąžinamos VISOS: pasirinkimas priklauso naudotojui, nes tyliai paėmus
        pirmą būtų ieškoma panašių į visai kitą kūrinį.
        """
        found = self._repo.find_by_title_artist(tenant_id, title, artist)
        if not found:
            kas = f"{title!r}" if artist is None else f"{title!r} ({artist})"
            raise TimbreError(
                ErrorCode.DAINA_NERASTA,
                f"dainos {kas} kliento {tenant_id!r} kataloge nėra",
            )
        return found

    @staticmethod
    def _validate_filters(filters: FilterSpec, limit: int, artist_limit: int) -> None:
        if limit <= 0:
            raise TimbreError(
                ErrorCode.NETINKAMAS_FILTRAS,
                f"rezultatų kiekis turi būti didesnis už nulį, gauta {limit}",
            )
        # Be šios patikros `--artist-limit 0` tyliai grąžintų tuščią sąrašą:
        # atlikėjo limitas išmestų visus kandidatus, ir naudotojas nesuprastų,
        # kodėl nieko nerado.
        if artist_limit <= 0:
            raise TimbreError(
                ErrorCode.NETINKAMAS_FILTRAS,
                f"dainų iš to paties atlikėjo turi būti bent viena, gauta {artist_limit}",
            )
        if (
            filters.bpm_min is not None
            and filters.bpm_max is not None
            and filters.bpm_min > filters.bpm_max
        ):
            raise TimbreError(
                ErrorCode.NETINKAMAS_FILTRAS,
                f"tempo intervalas tuščias: {filters.bpm_min} > {filters.bpm_max}",
            )

    @staticmethod
    def _check_feature_sets(query: Track, candidates: list[Track]) -> None:
        """Skirtingų modelių vektoriai nėra lyginami.

        Tai programuotojo, ne naudotojo klaida, todėl `ValueError`, o ne
        `TimbreError`.
        """
        expected = query.features.feature_set
        for candidate in candidates:
            if candidate.features.feature_set != expected:
                raise ValueError(
                    f"feature_set nesutampa: užklausa {expected!r}, "
                    f"kandidatas {candidate.song_id!r} {candidate.features.feature_set!r}"
                )

    @staticmethod
    def _compute_pairwise(candidates: list[Track]) -> dict[tuple[str, str], float]:
        pairwise: dict[tuple[str, str], float] = {}
        for index, first in enumerate(candidates):
            for second in candidates[index + 1 :]:
                key = pairwise_key(first.song_id, second.song_id)
                pairwise[key] = cosine(first.features.vector, second.features.vector)
        return pairwise

    @staticmethod
    def _most_restricting_filter(pool: CandidatePool) -> str | None:
        """Labiausiai apribojęs filtras — tik jei filtras tikrai ką nors atmetė.

        Jei rezultatų mažiau vien dėl dublikatų ar atlikėjo limito, laukas
        lieka `None`: priešingu atveju naudotojui būtų nurodyta atlaisvinti
        filtrą, kuris nieko neatmetė.

        Filtras ką nors atmetė tada ir tik tada, kai jį vieną praėjusių dainų
        yra mažiau, nei apskritai matomų kliento dainų. Todėl lyginama su
        `visible_count`, o ne su kandidatų sąrašo ilgiu ar su didžiausia
        `survivors_per_filter` reikšme — abu tie pakaitalai duoda neteisingą
        atsakymą. Didžiausia reikšmė klysta, kai visi filtrai aktyvūs ir atmeta
        tą patį rinkinį (tada laukas liktų tuščias, nors atmesta). Kandidatų
        sąrašo ilgis klysta, kai matomų dainų daugiau nei POOL_SIZE (tada būtų
        nurodytas filtras, kuris nieko neatmetė).
        """
        survivors = pool.survivors_per_filter
        if not survivors:
            return None
        if all(count >= pool.visible_count for count in survivors.values()):
            return None
        return min(survivors, key=lambda name: (survivors[name], name))
