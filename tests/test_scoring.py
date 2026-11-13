"""Balų skaičiavimo testai. Specifikacijos 12 skyrius.

Visi testai tik atmintyje: jokio tinklo, failų sistemos ar duomenų bazės.
Arrange–Act–Assert, vienas tikrinamas dalykas viename teste.

Svarbiausias čia yra `test_dokumento_pavyzdys_atkuria_visus_sesis_balus` —
jis tiesiogiai įrodo, kad kodas atitinka dėstytojo patvirtintą I etapo
dokumentą. Jo skaičių niekada nekeisti „kad praeitų": jei nepraeina, klysta
kodas, o ne testas.
"""

import math

import pytest

from timbre.domain.constants import MOOD_DARK, MOOD_INSTRUMENTAL, VECTOR_DIM
from timbre.domain.errors import ErrorCode, TimbreError
from timbre.domain.models import Features, Track
from timbre.domain.scoring import (
    DEFAULT_STRATEGIES,
    KeyCriterion,
    MoodCriterion,
    TempoCriterion,
    score_all,
    validate_weights,
)

# Svoriai paimti tiesiai iš patvirtinto dokumento 3 skyriaus, o ne iš
# DEFAULT_WEIGHTS: atraminis testas turi būti nepriklausomas nuo konstantų
# failo, kad įrodytų sutapimą būtent su dokumentu.
DOCUMENT_WEIGHTS = {
    "vector": 0.70,
    "tempo": 0.10,
    "key": 0.05,
    "loudness": 0.05,
    "mood": 0.10,
}

# Užklausos vektorius — pirmoji bazės ašis. Bet kurio kandidato vektorius
# sudaromas kaip c = cos*q + sin*p, kur p statmenas q ir sin = sqrt(1-cos^2),
# todėl kosinusas su užklausa yra lygiai toks, kokio prašoma. Tą pačią
# konstrukciją naudoja ir scripts/seed_catalog.py (specifikacijos 4 skyrius).
QUERY_VECTOR = tuple([1.0] + [0.0] * (VECTOR_DIM - 1))


def unit_vector_with_cosine(target: float) -> tuple[float, ...]:
    """Vienetinis VECTOR_DIM vektorius, kurio kosinusas su QUERY_VECTOR = target."""
    values = [0.0] * VECTOR_DIM
    values[0] = target
    values[1] = math.sqrt(1.0 - target * target)
    return tuple(values)


def make_features(
    *,
    cosine_to_query: float = 1.0,
    bpm: float = 124.0,
    key: str = "8A",
    key_confidence: float = 0.81,
    loudness_lufs: float = -8.2,
    moods: dict[str, float] | None = None,
) -> Features:
    """Features su dokumento užklausos reikšmėmis kaip numatytosiomis."""
    return Features(
        vector=unit_vector_with_cosine(cosine_to_query),
        bpm=bpm,
        key=key,
        key_confidence=key_confidence,
        loudness_lufs=loudness_lufs,
        moods={MOOD_INSTRUMENTAL: 0.93, MOOD_DARK: 0.71} if moods is None else moods,
    )


def make_track(
    song_id: str,
    title: str,
    artist: str,
    features: Features,
    tenant_id: str = "t-77",
) -> Track:
    return Track(
        song_id=song_id,
        tenant_id=tenant_id,
        title=title,
        artist=artist,
        features=features,
    )


def document_query() -> Track:
    """Dokumento užklausa: 124 BPM, 8A (0,81), −8,2 LUFS, atlikėjas A-1021."""
    return make_track("Q", "Uzklausa", "A-1021", make_features())


def document_candidates() -> list[Track]:
    """Šeši dokumento 3 skyriaus kandidatai su visais jų požymiais."""
    rows = [
        # song_id, pavadinimas, atlikėjas, kosinusas, bpm, key, pasitikėjimas,
        # LUFS, instrumentinė, tamsi
        ("K1", "Nightfield", "Kepler Grove", 0.91, 126.0, "8A", 0.88, -7.5, 0.88, 0.69),
        ("K2", "Nightfield (Remix)", "Kepler Grove", 0.90, 126.0, "8A", 0.86, -7.4, 0.87, 0.70),
        ("K3", "Drift Layer", "Kepler Grove", 0.89, 122.0, "9A", 0.77, -8.8, 0.90, 0.66),
        ("K4", "Slow Tide", "Mara Vale", 0.86, 62.0, "8A", 0.75, -9.0, 0.95, 0.60),
        ("K5", "Copper Dust", "Juno Reef", 0.88, 138.0, "3B", 0.60, -6.0, 0.40, 0.80),
        ("K6", "Inner Field", "A-1021", 0.94, 124.0, "8A", 0.80, -8.0, 0.92, 0.72),
    ]
    return [
        make_track(
            song_id,
            title,
            artist,
            make_features(
                cosine_to_query=cosine_to_query,
                bpm=bpm,
                key=key,
                key_confidence=key_confidence,
                loudness_lufs=loudness_lufs,
                moods={MOOD_INSTRUMENTAL: instrumental, MOOD_DARK: dark},
            ),
        )
        for (
            song_id,
            title,
            artist,
            cosine_to_query,
            bpm,
            key,
            key_confidence,
            loudness_lufs,
            instrumental,
            dark,
        ) in rows
    ]


def test_dokumento_pavyzdys_atkuria_visus_sesis_balus():
    # Arrange
    query = document_query()
    candidates = document_candidates()
    expected = {
        "K1": 0.908,
        "K2": 0.900,
        "K3": 0.883,
        "K4": 0.877,
        "K5": 0.720,
        "K6": 0.945,
    }

    # Act
    scored = score_all(query, candidates, DOCUMENT_WEIGHTS, DEFAULT_STRATEGIES)

    # Assert
    actual = {item.track.song_id: item.total_score for item in scored}
    assert actual == pytest.approx(expected, abs=0.001)


def test_tempo_dvigubinimas_124_ir_62_duoda_viena():
    # Arrange
    query = make_features(bpm=124.0)
    candidate = make_features(bpm=62.0)

    # Act
    score = TempoCriterion().score(query, candidate)

    # Assert
    assert score == pytest.approx(1.0, abs=0.001)


def test_tempo_14_bpm_skirtumas_beveik_nulis():
    # Arrange
    query = make_features(bpm=124.0)
    candidate = make_features(bpm=138.0)

    # Act
    score = TempoCriterion().score(query, candidate)

    # Assert
    assert score == pytest.approx(0.0043, abs=0.0001)


def test_tonacijos_balas_mazinamas_mazesniu_pasitikejimu():
    # Arrange
    query = make_features(key="8A", key_confidence=0.81)
    candidate = make_features(key="8A", key_confidence=0.88)

    # Act
    score = KeyCriterion().score(query, candidate)

    # Assert
    assert score == pytest.approx(0.81, abs=0.001)


def test_tonacijos_8a_ir_3b_duoda_nuli():
    # Arrange
    query = make_features(key="8A", key_confidence=1.0)
    candidate = make_features(key="3B", key_confidence=1.0)

    # Act
    score = KeyCriterion().score(query, candidate)

    # Assert
    assert score == 0.0


def test_nezinoma_tonacija_duoda_nuli():
    # Arrange
    query = make_features(key="", key_confidence=1.0)
    candidate = make_features(key="8A", key_confidence=1.0)

    # Act
    score = KeyCriterion().score(query, candidate)

    # Assert
    assert score == 0.0


def test_nuotaikos_balas_be_bendru_raktu_yra_nulis():
    # Arrange
    query = make_features(moods={MOOD_INSTRUMENTAL: 0.93})
    candidate = make_features(moods={"energinga": 0.93})

    # Act
    score = MoodCriterion().score(query, candidate)

    # Assert
    assert score == 0.0


def test_svoris_uz_intervalo_kelia_netinkamas_svoris():
    # Arrange
    too_low = {"vector": -0.1, "tempo": 0.5}
    too_high = {"vector": 1.5, "tempo": 0.5}

    # Act & Assert
    for weights in (too_low, too_high):
        with pytest.raises(TimbreError) as info:
            validate_weights(weights, DEFAULT_STRATEGIES)
        assert info.value.code is ErrorCode.NETINKAMAS_SVORIS


def test_nezinomas_kriterijaus_vardas_kelia_netinkamas_svoris():
    # Arrange
    weights = {"foo": 1.0}

    # Act & Assert
    with pytest.raises(TimbreError) as info:
        validate_weights(weights, DEFAULT_STRATEGIES)
    assert info.value.code is ErrorCode.NETINKAMAS_SVORIS


def test_nuliniu_svoriu_suma_kelia_nuliniai_svoriai():
    # Arrange
    weights = {"vector": 0.0, "tempo": 0.0, "key": 0.0, "loudness": 0.0, "mood": 0.0}

    # Act & Assert
    with pytest.raises(TimbreError) as info:
        validate_weights(weights, DEFAULT_STRATEGIES)
    assert info.value.code is ErrorCode.NULINIAI_SVORIAI


def test_visi_kriteriju_balai_intervale_nuo_nulio_iki_vieno():
    # Arrange — kelios atsitiktinai parinktos, bet fiksuotos poros: ribiniai
    # kosinusai (įskaitant negatyvų), dvigubinimo tempai, nežinoma tonacija,
    # nuliniai pasitikėjimai, nesutampantys nuotaikų raktai.
    pairs = [
        (make_features(), make_features(cosine_to_query=1.0)),
        (make_features(), make_features(cosine_to_query=0.0, bpm=180.0, key="1A")),
        (
            make_features(key="", key_confidence=0.0),
            make_features(cosine_to_query=-0.5, bpm=60.0, key="12B", loudness_lufs=-14.0),
        ),
        (
            make_features(moods={MOOD_DARK: 1.0}),
            make_features(cosine_to_query=0.5, moods={MOOD_INSTRUMENTAL: 0.0}),
        ),
        (
            make_features(key_confidence=1.0, loudness_lufs=-5.0),
            make_features(cosine_to_query=0.33, bpm=61.0, key="7B", key_confidence=1.0),
        ),
    ]

    # Act & Assert
    for query, candidate in pairs:
        for name, strategy in DEFAULT_STRATEGIES.items():
            score = strategy.score(query, candidate)
            assert 0.0 <= score <= 1.0, f"{name} = {score}"
