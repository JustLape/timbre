"""Paieškos scenarijaus orkestracija. Specifikacijos 9 skyrius.

Šis sluoksnis nieko neskaičiuoja pats — jis sujungia `domain` funkcijas su
katalogu, gaunamu per `ports.repository.CatalogRepository` sąsają. Konkreti
katalogo realizacija čia nežinoma: ji paduodama per konstruktorių (priklausomybių
injekcija), todėl tą patį scenarijų galima paleisti ir ant JSON failo, ir ant
atminties katalogo testuose.

Vienas dalykas, kurį šis sluoksnis TIKRAI skaičiuoja, yra kandidatų tarpusavio
kosinusai (`pairwise`). Tai sąmoningas darbų padalijimas: `domain` juos priima
argumentu ir niekada neskaičiuoja iš vektorių, todėl testai gali perduoti
dokumento reikšmes, o paleidimas veikia su tikrais vektoriais.
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
from ..domain.models import FilterSpec, ResultItem, SearchResult, Track
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

        # 2. Filtrai ir limitas.
        self._validate_filters(filters, limit)

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

    @staticmethod
    def _validate_filters(filters: FilterSpec, limit: int) -> None:
        if limit <= 0:
            raise TimbreError(
                ErrorCode.NETINKAMAS_FILTRAS,
                f"rezultatų kiekis turi būti didesnis už nulį, gauta {limit}",
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
    def _most_restricting_filter(pool) -> str | None:
        """Labiausiai apribojęs filtras — tik jei filtras tikrai ką nors atmetė.

        Jei rezultatų mažiau vien dėl dublikatų ar atlikėjo limito, laukas
        lieka `None`: priešingu atveju naudotojui būtų nurodyta atlaisvinti
        filtrą, kuris nieko neatmetė.

        Nefiltruotų kandidatų kiekis atkuriamas kaip didžiausia
        `survivors_per_filter` reikšmė: nenaudojamas filtras praleidžia visas
        dainas, todėl jo reikšmė ir yra bendras kiekis.
        """
        survivors = pool.survivors_per_filter
        if not survivors:
            return None
        baseline = max(survivors.values())
        if len(pool.candidates) >= baseline:
            return None
        return min(survivors, key=lambda name: (survivors[name], name))
