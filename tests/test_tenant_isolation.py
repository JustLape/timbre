"""Klientų duomenų atskyrimo testai. II etapo 4 reikalavimas.

Reikalavimas sako, kad vieno kliento kontekste negalima nei PERSKAITYTI, nei
PAKEISTI kito kliento duomenų, ir kad atskyrimą turi užtikrinti sistemos
logika, o ne paslėpti įrašai sąsajoje. Todėl čia yra abu keliai: skaitymo ir
keitimo.

Katalogas sąmoningai sudarytas taip, kad abu klientai turėtų tuos pačius
`song_id` — kitaip testas praeitų net ir visiškai neveikiant atskyrimui.
"""

import pytest

from timbre.adapters.in_memory import InMemoryCatalog
from timbre.app.search_service import SearchService
from timbre.domain.errors import ErrorCode, TimbreError
from timbre.domain.models import FilterSpec


def test_kliento_a_uzklausa_negrazina_kliento_b_dainu(two_tenant_tracks):
    # Arrange
    service = SearchService(InMemoryCatalog(two_tenant_tracks))

    # Act
    result = service.search(
        tenant_id="t-77", song_id="s-100", filters=FilterSpec(), limit=10
    )

    # Assert
    assert result.items
    assert all(item.track.tenant_id == "t-77" for item in result.items)


def test_kito_kliento_daina_nerandama_pagal_song_id(two_tenant_tracks):
    # Arrange — s-999 egzistuoja, bet tik klientui t-88
    catalog = InMemoryCatalog(two_tenant_tracks)
    assert catalog.get_track("t-88", "s-999") is not None
    service = SearchService(catalog)

    # Act & Assert — t-77 žino svetimą id, bet jam tos dainos nėra
    with pytest.raises(TimbreError) as info:
        service.search(
            tenant_id="t-77", song_id="s-999", filters=FilterSpec(), limit=10
        )
    assert info.value.code is ErrorCode.DAINA_NERASTA


def test_tenant_id_yra_privalomas_argumentas(two_tenant_tracks):
    # Arrange
    service = SearchService(InMemoryCatalog(two_tenant_tracks))

    # Act & Assert — be tenant_id kvietimas tiesiog nesuveikia
    with pytest.raises(TypeError):
        service.search(song_id="s-100", filters=FilterSpec(), limit=10)


def test_kito_kliento_dainos_negalima_pasalinti(two_tenant_tracks):
    # Arrange — s-999 priklauso tik t-88
    catalog = InMemoryCatalog(two_tenant_tracks)
    service = SearchService(catalog)

    # Act & Assert — t-77 bando pašalinti svetimą dainą
    with pytest.raises(TimbreError) as info:
        service.remove(tenant_id="t-77", song_id="s-999")
    assert info.value.code is ErrorCode.DAINA_NERASTA

    # Ir svarbiausia: t-88 daina tikrai liko kataloge
    assert catalog.get_track("t-88", "s-999") is not None


def test_savo_daina_pasalinama_nepaliecius_kito_kliento(two_tenant_tracks):
    # Arrange — teigiama kontrolė: be jos ankstesnis testas praeitų ir tuomet,
    # jei `remove` apskritai nieko nešalintų. s-201 turi ABU klientai.
    catalog = InMemoryCatalog(two_tenant_tracks)
    service = SearchService(catalog)

    # Act
    service.remove(tenant_id="t-77", song_id="s-201")

    # Assert — pašalinta tik savoji, kito kliento to paties id daina liko
    assert catalog.get_track("t-77", "s-201") is None
    assert catalog.get_track("t-88", "s-201") is not None
