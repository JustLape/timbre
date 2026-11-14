"""Duomenų tipų patikrų testai. Specifikacijos 11 skyrius.

Šių testų plane nebuvo, ir mutacijų patikra parodė, kad visą
`Features.__post_init__` galima ištrinti, o testai lieka žali. Patikros yra
dokumento 3 skyriaus „atsakymo tikrinimo" dalis — vektorius su tuščiomis
reikšmėmis paieškai grąžintų šiukšles — todėl jos turi būti testuojamos.
"""

import math

import pytest

from timbre.domain.constants import VECTOR_DIM
from timbre.domain.models import Features

GERAS_VEKTORIUS = tuple([1.0] + [0.0] * (VECTOR_DIM - 1))


def make(**pakeitimai):
    laukai = dict(
        vector=GERAS_VEKTORIUS,
        bpm=124.0,
        key="8A",
        key_confidence=0.81,
        loudness_lufs=-8.2,
        moods={"instrumentinė": 0.93},
    )
    laukai.update(pakeitimai)
    return Features(**laukai)


def test_teisingi_pozymiai_sukuriami():
    # Act
    features = make()

    # Assert
    assert len(features.vector) == VECTOR_DIM
    assert features.feature_set == "synthetic-v1"


def test_per_trumpas_vektorius_kelia_value_error():
    # Act & Assert
    with pytest.raises(ValueError, match="ilgis"):
        make(vector=(1.0, 0.0))


def test_nan_vektoriuje_kelia_value_error():
    # Act & Assert
    with pytest.raises(ValueError, match="skaičius"):
        make(vector=(float("nan"),) + GERAS_VEKTORIUS[1:])


def test_begalybe_vektoriuje_kelia_value_error():
    # Act & Assert
    with pytest.raises(ValueError, match="skaičius"):
        make(vector=(float("inf"),) + GERAS_VEKTORIUS[1:])


@pytest.mark.parametrize("bloga_reiksme", [-0.1, 1.5])
def test_pasitikejimas_uz_intervalo_kelia_value_error(bloga_reiksme):
    # Act & Assert
    with pytest.raises(ValueError, match="key_confidence"):
        make(key_confidence=bloga_reiksme)


def test_pasitikejimo_kraštines_reiksmes_leidziamos():
    # Act & Assert — 0 ir 1 yra intervale [0; 1] imtinai
    assert make(key_confidence=0.0).key_confidence == 0.0
    assert make(key_confidence=1.0).key_confidence == 1.0


def test_vektoriaus_ilgis_tikrinamas_pries_reiksmes():
    # Arrange — trumpas vektorius su nan: turi suveikti ilgio patikra
    # Act & Assert
    with pytest.raises(ValueError, match="ilgis"):
        make(vector=(float("nan"), 1.0))


def test_begalybes_patikra_apima_visas_pozicijas():
    # Arrange — bloga reikšmė ne pirmoje vietoje
    blogas = list(GERAS_VEKTORIUS)
    blogas[200] = math.inf

    # Act & Assert
    with pytest.raises(ValueError, match="200"):
        make(vector=tuple(blogas))
