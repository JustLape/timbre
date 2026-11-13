"""Atrankos testai. Specifikacijos 12 skyrius.

Tikrina tris dokumento 3 skyriaus taisykles: dublikatus (5), atlikėjo limitą
(6) ir įvairovę (7). Visi duomenys tik atmintyje.
"""

import pytest

from timbre.domain.selection import (
    apply_artist_limit,
    normalize_title,
    remove_duplicates,
    select_diverse,
)


def test_remix_atmetamas_kaip_dublikatas_pagal_pavadinima(scored_factory):
    # Arrange
    scored = [
        scored_factory("K1", 0.908, title="Nightfield", artist="Kepler Grove"),
        scored_factory("K2", 0.900, title="Nightfield (Remix)", artist="Kepler Grove"),
    ]

    # Act
    kept, removed = remove_duplicates(scored, {})

    # Assert
    assert [item.track.song_id for item in kept] == ["K1"]


def test_dublikatas_atmetamas_pagal_kosinusa_virs_098(scored_factory):
    # Arrange — pavadinimai visiškai skirtingi, sutampa tik vektoriai
    scored = [
        scored_factory("A", 0.90, title="Nightfield"),
        scored_factory("B", 0.88, title="Visai Kitas Pavadinimas"),
    ]
    pairwise = {("A", "B"): 0.99}

    # Act
    kept, removed = remove_duplicates(scored, pairwise)

    # Assert
    assert [item.track.song_id for item in kept] == ["A"]


def test_panasus_bet_skirtingas_pavadinimas_nera_dublikatas(scored_factory):
    # Arrange — tarpas pavadinime yra reikšmingas, kosinusas po ribos
    scored = [
        scored_factory("A", 0.90, title="Nightfield"),
        scored_factory("B", 0.88, title="Night Field"),
    ]
    pairwise = {("A", "B"): 0.95}

    # Act
    kept, removed = remove_duplicates(scored, pairwise)

    # Assert
    assert [item.track.song_id for item in kept] == ["A", "B"]


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("Nightfield (Remix)", "nightfield"),
        ("Nightfield - Radio Edit", "nightfield"),
        ("Nightfield feat. Mara Vale", "nightfield"),
        ("Nightfield [Live]", "nightfield"),
        ("Night Field", "night field"),
    ],
)
def test_pavadinimo_norminimas_nuima_skliaustus_ir_zymes(raw, expected):
    # Act & Assert — visi penki pavyzdžiai iš specifikacijos 7 skyriaus
    assert normalize_title(raw) == expected


def test_uzklausos_atlikejo_daina_ismetama_visada(document_scored):
    # Arrange — K6 yra užklausos atlikėjo (A-1021) daina ir turi aukščiausią balą
    assert document_scored[0].track.song_id == "K6"

    # Act
    kept, removed = apply_artist_limit(document_scored, "A-1021", per_artist=1)

    # Assert
    assert "K6" not in [item.track.song_id for item in kept]


def test_atlikejo_limitas_palieka_auksciausia_bala(document_scored):
    # Arrange — K1 (0,908) ir K3 (0,883) abi yra Kepler Grove dainos
    # Act
    kept, removed = apply_artist_limit(document_scored, "A-1021", per_artist=1)

    # Assert
    kepler = [
        item.track.song_id
        for item in kept
        if item.track.artist == "Kepler Grove"
    ]
    assert kepler == ["K1"]


def test_ivairove_duoda_k1_k5_k4_eile(document_scored, document_pairwise):
    # Arrange — po dublikatų ir atlikėjo limito lieka K1, K4, K5
    survivors = [
        item for item in document_scored if item.track.song_id in ("K1", "K4", "K5")
    ]

    # Act
    selected = select_diverse(survivors, document_pairwise, limit=3)

    # Assert — K5 aplenkia K4, nors jos balas mažesnis: K4 per daug panaši į K1
    assert [item.track.song_id for item in selected] == ["K1", "K5", "K4"]


def test_ivairove_be_pairwise_rikiuoja_pagal_bala(scored_factory):
    # Arrange
    scored = [
        scored_factory("A", 0.90),
        scored_factory("B", 0.80),
        scored_factory("C", 0.70),
    ]

    # Act
    selected = select_diverse(scored, {}, limit=3)

    # Assert
    assert [item.track.song_id for item in selected] == ["A", "B", "C"]
