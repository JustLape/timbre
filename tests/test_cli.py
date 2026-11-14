"""Komandinės eilutės testai.

Šių testų plane nebuvo, todėl `parse_weights` buvo visai netestuotas, nors
būtent jis verčia naudotojo įvestį į svorius ir yra vienas iš kelių, kuriais
gaunamas `NETINKAMAS_SVORIS`.

Čia netikrinama nei paieška, nei katalogo failas — tik argumentų apdorojimas,
todėl testai lieka grynai atmintyje.
"""

import pytest

from timbre.cli import FILTER_NAMES, build_parser, parse_weights
from timbre.domain.errors import ErrorCode, TimbreError


def test_svoriai_parsinami_i_zodyna():
    # Act
    weights = parse_weights("vector=0.7,tempo=0.1")

    # Assert
    assert weights == {"vector": 0.7, "tempo": 0.1}


def test_tarpai_aplink_svorius_nekliudo():
    # Act
    weights = parse_weights(" vector = 0.7 , tempo = 0.1 ")

    # Assert
    assert weights == {"vector": 0.7, "tempo": 0.1}


def test_svoris_be_lygybes_kelia_netinkamas_svoris():
    # Act & Assert
    with pytest.raises(TimbreError) as info:
        parse_weights("blogai")
    assert info.value.code is ErrorCode.NETINKAMAS_SVORIS


def test_ne_skaicius_kelia_netinkamas_svoris():
    # Act & Assert
    with pytest.raises(TimbreError) as info:
        parse_weights("vector=daug")
    assert info.value.code is ErrorCode.NETINKAMAS_SVORIS


def test_tuscias_svoriu_sarasas_kelia_netinkamas_svoris():
    # Act & Assert
    with pytest.raises(TimbreError) as info:
        parse_weights(",,")
    assert info.value.code is ErrorCode.NETINKAMAS_SVORIS


def test_song_id_ir_tenant_yra_privalomi():
    # Act & Assert — argparse klaida baigia procesą kodu 2
    with pytest.raises(SystemExit) as info:
        build_parser().parse_args(["--song-id", "t-0000"])
    assert info.value.code == 2


def test_filtru_vardai_isversti_naudotojui():
    # Assert — vidiniai raktai ir naudotojui matomi vardai yra atskirti
    assert FILTER_NAMES["bpm"] == "tempas"
    assert set(FILTER_NAMES) == {"bpm", "instrumental"}
