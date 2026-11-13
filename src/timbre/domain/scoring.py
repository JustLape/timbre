"""Penki panašumo kriterijai, Strategy registras ir svorinė suma.

Specifikacijos 6 skyrius; formulės — patvirtinto I etapo dokumento 3 skyrius.

Šis modulis yra grynas: jokio I/O, tinklo, failų, `print`, `random` ar laiko.
Viskas gaunama per argumentus ir grąžinama per reikšmes. Tai svarbiausias
dokumento projektavimo sprendimas — būtent dėl jo testui pakanka ranka
sugalvotų skaičių, be duomenų bazės ir be garso failų.

Strategy šablonas: kiekvienas kriterijus yra atskira klasė su `name` ir
`score`, o `DEFAULT_STRATEGIES` yra registras, susidedantis iš pačių
strategijų vardų. Šeštas kriterijus reiškia vieną naują klasę ir vieną įrašą
registre — nei `score_track`, nei svorių apdorojimas, nei CLI nesikeičia.
"""

import math
from collections.abc import Mapping, Sequence
from typing import Protocol

from .constants import KEY_MAX_STEPS, LOUDNESS_SCALE, TEMPO_SIGMA
from .errors import ErrorCode, TimbreError
from .models import Features, ScoredTrack, Track


class CriterionStrategy(Protocol):
    """Vieno kriterijaus sąsaja.

    Visi penki kriterijai sutelpa į šią vieną sąsają, nes visi reikalingi
    duomenys yra `Features`. Būtent tai ir daro Strategy šabloną čia natūralų,
    o ne prilipintą.
    """

    name: str

    def score(self, query: Features, candidate: Features) -> float: ...


def cosine(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    """Kosinuso panašumas tarp dviejų vektorių.

    Grąžinama neapvalinta ir neapribota reikšmė: `pairwise` skaičiavimui,
    dublikatų ribai ir įvairovės baudai reikia žalio kosinuso. Kriterijaus
    balą į [0; 1] apriboja `VectorCriterion`, o ne ši funkcija.

    Nulinio ilgio vektorius neturi krypties, todėl grąžinama 0,0 — tai
    sąžiningesnis atsakymas nei `ZeroDivisionError`.
    """
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for x, y in zip(a, b, strict=True):
        dot += x * y
        norm_a += x * x
        norm_b += y * y
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (math.sqrt(norm_a) * math.sqrt(norm_b))


def _parse_camelot(key: str) -> tuple[int, str] | None:
    """Išskiria "8A" į (8, "A"); grąžina None, jei raktas neparsinamas."""
    text = key.strip().upper()
    if len(text) < 2:
        return None
    number, letter = text[:-1], text[-1]
    if letter not in ("A", "B") or not number.isdecimal():
        return None
    position = int(number)
    if not 1 <= position <= 12:
        return None
    return position, letter


def camelot_steps(a: str, b: str) -> int:
    """Žingsniai Camelot rate.

    min(|n1-n2|, 12-|n1-n2|) + (1 jei raidės skiriasi).
    Patikrinta pagal dokumentą: 8A-8A = 0, 8A-9A = 1, 8A-3B = 6.

    Neparsinamas arba tuščias raktas grąžina int(KEY_MAX_STEPS) — tai
    reikšmė, prie kurios max(0, 1 - žingsniai/KEY_MAX_STEPS) yra lygiai 0.
    Nežinoma tonacija neturi duoti panašumo.
    """
    parsed_a = _parse_camelot(a)
    parsed_b = _parse_camelot(b)
    if parsed_a is None or parsed_b is None:
        return int(KEY_MAX_STEPS)
    position_a, letter_a = parsed_a
    position_b, letter_b = parsed_b
    distance = abs(position_a - position_b)
    return min(distance, 12 - distance) + (1 if letter_a != letter_b else 0)


class VectorCriterion:
    """Kosinuso panašumas tarp garso vektorių."""

    name = "vector"

    def score(self, query: Features, candidate: Features) -> float:
        # Apribojama iš apačios, nes kosinusas matematiškai gali būti
        # negatyvus net su visiškai taisyklingais normalizuotais vektoriais,
        # o CLAUDE.md kontraktas sako, kad visi balai yra tarp 0 ir 1.
        return max(0.0, cosine(query.vector, candidate.vector))


class TempoCriterion:
    """Tempo sutapimas, atsižvelgiant į dvigubinimą (dokumento 1 taisyklė)."""

    name = "tempo"

    def score(self, query: Features, candidate: Features) -> float:
        first, second = query.bpm, candidate.bpm
        delta = min(
            abs(first - second),
            abs(2 * first - second),
            abs(first - 2 * second),
        )
        return math.exp(-((delta / TEMPO_SIGMA) ** 2))


class KeyCriterion:
    """Tonacijų suderinamumas, sumažintas mažesniuoju pasitikėjimu."""

    name = "key"

    def score(self, query: Features, candidate: Features) -> float:
        steps = camelot_steps(query.key, candidate.key)
        compatibility = max(0.0, 1.0 - steps / KEY_MAX_STEPS)
        confidence = min(query.key_confidence, candidate.key_confidence)
        return compatibility * confidence


class LoudnessCriterion:
    """Garsumo artumas. Formulė NE kvadratinė: exp(-|delta|/6)."""

    name = "loudness"

    def score(self, query: Features, candidate: Features) -> float:
        delta = abs(query.loudness_lufs - candidate.loudness_lufs)
        return math.exp(-delta / LOUDNESS_SCALE)


class MoodCriterion:
    """Nuotaikų artumas: 1 - vidutinis absoliutus skirtumas.

    Vidurkis imamas TIK per bendrus raktus. Bendrų raktų nėra — balas 0,0:
    negalima teigti panašumo, kurio nėra kuo pamatuoti.
    """

    name = "mood"

    def score(self, query: Features, candidate: Features) -> float:
        shared = set(query.moods) & set(candidate.moods)
        if not shared:
            return 0.0
        total = sum(abs(query.moods[key] - candidate.moods[key]) for key in shared)
        return 1.0 - total / len(shared)


DEFAULT_STRATEGIES: dict[str, CriterionStrategy] = {
    strategy.name: strategy
    for strategy in (
        VectorCriterion(),
        TempoCriterion(),
        KeyCriterion(),
        LoudnessCriterion(),
        MoodCriterion(),
    )
}


def validate_weights(
    weights: Mapping[str, float],
    strategies: Mapping[str, CriterionStrategy],
) -> None:
    """Patikrina svorius; klaidos atveju kelia TimbreError.

    Trys patikros iš specifikacijos 6 skyriaus: svoris už [0; 1] ir nežinomas
    kriterijaus vardas duoda NETINKAMAS_SVORIS, nulinė suma —
    NULINIAI_SVORIAI. Nulinės sumos atveju visų dainų balas būtų 0 ir eilė
    taptų atsitiktinė, todėl geriau klaida nei apsimestinis rezultatas.

    Svorio nenurodyti galima — tada kriterijus tiesiog neįtraukiamas į sumą.
    """
    for name, weight in weights.items():
        if name not in strategies:
            known = ", ".join(sorted(strategies))
            raise TimbreError(
                ErrorCode.NETINKAMAS_SVORIS,
                f"nežinomas kriterijus {name!r}; galimi: {known}",
            )
        if not 0.0 <= weight <= 1.0:
            raise TimbreError(
                ErrorCode.NETINKAMAS_SVORIS,
                f"svoris {name!r} = {weight}, leistina tik [0; 1]",
            )
    if sum(weights.values()) == 0.0:
        raise TimbreError(
            ErrorCode.NULINIAI_SVORIAI,
            "svorių suma lygi nuliui, eilė būtų atsitiktinė",
        )


def score_track(
    query: Track,
    candidate: Track,
    weights: Mapping[str, float],
    strategies: Mapping[str, CriterionStrategy],
) -> ScoredTrack:
    """Suskaičiuoja vieno kandidato kriterijų balus ir bendrą svorinį balą.

    Bendras balas: (suma wi*balasi) / suma wi. Dalyba iš sumos užtikrina, kad
    balas visada yra tarp 0 ir 1.

    criterion_scores užpildomas VISIEMS registro kriterijams, net jei jų
    svoris 0 arba nenurodytas: paaiškinimams (8 skyrius) reikia ir mažą svorį
    turinčių kriterijų balų.

    validate_weights kviečiamas čia, nors specifikacijos 9 skyrius jį kviečia
    ir search_service pradžioje: patikra idempotentiška ir pigi, o funkcija
    dėl jos tampa pilna — nė vienas kviečiantysis negali gauti dalybos iš nulio.

    feature_set nesutapimo patikra čia SĄMONINGAI nedaroma: specifikacijos
    9 skyrius ją priskiria app sluoksniui.
    """
    validate_weights(weights, strategies)
    criterion_scores = {
        name: strategy.score(query.features, candidate.features)
        for name, strategy in strategies.items()
    }
    weighted_sum = sum(
        weights.get(name, 0.0) * score for name, score in criterion_scores.items()
    )
    return ScoredTrack(
        track=candidate,
        total_score=weighted_sum / sum(weights.values()),
        criterion_scores=criterion_scores,
    )


def score_all(
    query: Track,
    candidates: Sequence[Track],
    weights: Mapping[str, float],
    strategies: Mapping[str, CriterionStrategy],
) -> list[ScoredTrack]:
    """Suskaičiuoja visus kandidatus, išlaikydama jų pradinę eilę.

    Čia NERIKIUOJAMA: pagal total_score rikiuoja app/search_service.py
    (9 skyriaus 6 žingsnis), nes ten yra ir antrinis raktas song_id.
    """
    return [
        score_track(query, candidate, weights, strategies) for candidate in candidates
    ]
