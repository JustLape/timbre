"""Paaiškinimų testai.

Šio failo specifikacijos 12 skyriaus plane nebuvo, ir dėl to `explain.py`
iki audito neturėjo nė vieno testo: mutacijų patikra parodė, kad visą modulį
galima sulaužyti, o testai lieka žali. Dokumento išvesties kontraktas
garantuoja bent du paaiškinimus kiekvienam rezultatui, tad garantija turi būti
tikrinama, o ne tik pažadėta.
"""

from timbre.domain.constants import MOOD_DARK, MOOD_INSTRUMENTAL
from timbre.domain.explain import explain
from timbre.domain.scoring import DEFAULT_STRATEGIES, score_track

from tests.conftest import DOCUMENT_WEIGHTS, build_features, build_track


def score(query, candidate):
    return score_track(query, candidate, DOCUMENT_WEIGHTS, DEFAULT_STRATEGIES)


def test_kiekvienas_rezultatas_turi_bent_du_paaiskinimus():
    # Arrange — kandidatas, kuris nepanašus niekuo: nulinis vektorius,
    # nežinoma tonacija, nesutampantys nuotaikos raktai, tolimas tempas
    query = build_track("Q", artist="A")
    candidate = build_track(
        "C",
        artist="B",
        features=build_features(
            cosine_to_query=0.05, axis=7, bpm=71.0, key="", moods={"kita": 0.1}
        ),
    )

    # Act
    explanations = explain(query, score(query, candidate))

    # Assert
    assert len(explanations) >= 2


def test_garantija_laikosi_ir_kai_prasoma_daugiau_nei_dvieju():
    # Arrange
    query = build_track("Q", artist="A")
    candidate = build_track(
        "C",
        artist="B",
        features=build_features(
            cosine_to_query=0.05, axis=7, bpm=71.0, key="", moods={"kita": 0.1}
        ),
    )

    # Act
    explanations = explain(query, score(query, candidate), min_count=5)

    # Assert
    assert len(explanations) >= 5


def test_tempo_dvigubinimas_paaiskinamas_atskiru_tekstu():
    # Arrange — dokumento K4 atvejis: 124 ir 62 BPM
    query = build_track("Q", artist="A", bpm=124.0)
    candidate = build_track(
        "C", artist="B", features=build_features(cosine_to_query=0.86, axis=4, bpm=62.0)
    )

    # Act
    explanations = explain(query, score(query, candidate))

    # Assert
    assert any("dvigubai" in text for text in explanations)
    assert any("124 ir 62 BPM" in text for text in explanations)


def test_artimas_tempas_paaiskinamas_be_dvigubinimo_zymes():
    # Arrange — dokumento K1 atvejis: 124 ir 126 BPM
    query = build_track("Q", artist="A", bpm=124.0)
    candidate = build_track(
        "C", artist="B", features=build_features(cosine_to_query=0.91, axis=4, bpm=126.0)
    )

    # Act
    explanations = explain(query, score(query, candidate))

    # Assert
    assert "124 ir 126 BPM" in explanations


def test_abi_instrumentines_paaiskinamos():
    # Arrange
    query = build_track("Q", artist="A", moods={MOOD_INSTRUMENTAL: 0.93, MOOD_DARK: 0.7})
    candidate = build_track(
        "C",
        artist="B",
        features=build_features(
            cosine_to_query=0.9,
            axis=4,
            moods={MOOD_INSTRUMENTAL: 0.88, MOOD_DARK: 0.69},
        ),
    )

    # Act
    explanations = explain(query, score(query, candidate))

    # Assert
    assert "abi instrumentinės" in explanations


def test_nederanti_tonacija_neduoda_tonaciju_dera():
    # Arrange — 8A ir 3B yra 6 žingsniai, balas 0
    query = build_track("Q", artist="A", key="8A", key_confidence=1.0)
    candidate = build_track(
        "C",
        artist="B",
        features=build_features(
            cosine_to_query=0.9, axis=4, key="3B", key_confidence=1.0
        ),
    )

    # Act
    explanations = explain(query, score(query, candidate))

    # Assert
    assert "tonacijos dera" not in explanations
