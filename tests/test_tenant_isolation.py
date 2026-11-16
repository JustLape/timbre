"""Klientų duomenų atskyrimo testai. II etapo 4 reikalavimas.

Reikalavimas sako, kad vieno kliento kontekste negalima nei PERSKAITYTI, nei
PAKEISTI kito kliento duomenų, ir kad atskyrimą turi užtikrinti sistemos
logika, o ne paslėpti įrašai sąsajoje. Todėl čia yra abu keliai: skaitymo ir
keitimo.

Sistema turi TRIS matomumo sritis, ir kiekvienai čia yra testas:

    UŽKLAUSAI   bendras katalogas + paties kliento įkeltos dainos
    ATSAKYMUI   tik bendras katalogas
    KEITIMUI    tik paties kliento įkeltos dainos

Svarbiausias iš jų yra antrasis. Jis reiškia, kad paskyros įkelta daina negali
nutekėti kitam klientui net netiesiogiai — per panašumo rezultatą.

Katalogas sąmoningai sudarytas taip, kad abi paskyros turėtų tuos pačius
`song_id` — kitaip testas praeitų net ir visiškai neveikiant atskyrimui.
"""

import pytest

from timbre.adapters.in_memory import InMemoryCatalog
from timbre.app.search_service import SearchService
from timbre.domain.constants import SHARED_CATALOG
from timbre.domain.errors import ErrorCode, TimbreError
from timbre.domain.models import FilterSpec


def test_kliento_a_uzklausa_negrazina_kliento_b_dainu(catalog_with_two_accounts):
    # Arrange
    service = SearchService(InMemoryCatalog(catalog_with_two_accounts))

    # Act
    result = service.search(
        tenant_id="t-77", song_id="s-100", filters=FilterSpec(), limit=10
    )

    # Assert
    assert result.items
    assert all(item.track.tenant_id == SHARED_CATALOG for item in result.items)
    assert not any(item.track.tenant_id == "t-88" for item in result.items)


def test_savo_ikelta_daina_negrizta_atsakyme(catalog_with_two_accounts):
    # Arrange — t-77 turi savo įkeltų dainų, artimų užklausai
    service = SearchService(InMemoryCatalog(catalog_with_two_accounts))

    # Act
    result = service.search(
        tenant_id="t-77", song_id="s-100", filters=FilterSpec(), limit=10
    )

    # Assert — net savininkui jos negrįžta: atsakymų šaltinis tik vienas
    assert not any(item.track.tenant_id == "t-77" for item in result.items)


def test_bendro_katalogo_daina_matoma_abiem_paskyroms(catalog_with_two_accounts):
    # Arrange
    catalog = InMemoryCatalog(catalog_with_two_accounts)

    # Act & Assert — ta pati daina pasiekiama iš abiejų paskyrų ir be paskyros
    assert catalog.get_track("t-77", "s-900") is not None
    assert catalog.get_track("t-88", "s-900") is not None
    assert catalog.get_track(SHARED_CATALOG, "s-900") is not None


def test_be_paskyros_ieskoma_tik_bendrame_kataloge(catalog_with_two_accounts):
    # Arrange — neprisijungęs naudotojas paduoda patį `bendras`
    service = SearchService(InMemoryCatalog(catalog_with_two_accounts))

    # Act
    result = service.search(
        tenant_id=SHARED_CATALOG, song_id="s-900", filters=FilterSpec(), limit=10
    )

    # Assert
    assert result.items
    assert all(item.track.tenant_id == SHARED_CATALOG for item in result.items)


def test_kito_kliento_daina_nerandama_pagal_song_id(catalog_with_two_accounts):
    # Arrange — s-999 egzistuoja, bet tik paskyrai t-88
    catalog = InMemoryCatalog(catalog_with_two_accounts)
    assert catalog.get_track("t-88", "s-999") is not None
    service = SearchService(catalog)

    # Act & Assert — t-77 žino svetimą id, bet jam tos dainos nėra
    with pytest.raises(TimbreError) as info:
        service.search(
            tenant_id="t-77", song_id="s-999", filters=FilterSpec(), limit=10
        )
    assert info.value.code is ErrorCode.DAINA_NERASTA


def test_tenant_id_yra_privalomas_argumentas(catalog_with_two_accounts):
    # Arrange
    service = SearchService(InMemoryCatalog(catalog_with_two_accounts))

    # Act & Assert — be tenant_id kvietimas tiesiog nesuveikia
    with pytest.raises(TypeError):
        service.search(song_id="s-100", filters=FilterSpec(), limit=10)


def test_kito_kliento_dainos_negalima_pasalinti(catalog_with_two_accounts):
    # Arrange — s-999 priklauso tik t-88
    catalog = InMemoryCatalog(catalog_with_two_accounts)
    service = SearchService(catalog)

    # Act & Assert — t-77 bando pašalinti svetimą dainą
    with pytest.raises(TimbreError) as info:
        service.remove(tenant_id="t-77", song_id="s-999")
    assert info.value.code is ErrorCode.DAINA_NERASTA

    # Ir svarbiausia: t-88 daina tikrai liko kataloge
    assert catalog.get_track("t-88", "s-999") is not None


def test_bendro_katalogo_dainos_negalima_pasalinti(catalog_with_two_accounts):
    # Arrange — s-900 puikiai matoma visiems, bet ji ne paskyros
    catalog = InMemoryCatalog(catalog_with_two_accounts)
    service = SearchService(catalog)

    # Act & Assert — matyti ir keisti yra du skirtingi dalykai
    with pytest.raises(TimbreError) as info:
        service.remove(tenant_id="t-77", song_id="s-900")
    assert info.value.code is ErrorCode.DAINA_NERASTA
    assert catalog.get_track("t-77", "s-900") is not None


def test_bendro_katalogo_nepasalina_net_neprisijunges(catalog_with_two_accounts):
    # Arrange — `bendras` kaip tenant_id neduoda teisės trinti bendro katalogo
    catalog = InMemoryCatalog(catalog_with_two_accounts)
    service = SearchService(catalog)

    # Act & Assert
    with pytest.raises(TimbreError) as info:
        service.remove(tenant_id=SHARED_CATALOG, song_id="s-900")
    assert info.value.code is ErrorCode.DAINA_NERASTA
    assert catalog.get_track(SHARED_CATALOG, "s-900") is not None


def test_savo_daina_pasalinama_nepaliecius_kito_kliento(catalog_with_two_accounts):
    # Arrange — teigiama kontrolė: be jos ankstesni testai praeitų ir tuomet,
    # jei `remove` apskritai nieko nešalintų. s-201 turi ABI paskyros.
    catalog = InMemoryCatalog(catalog_with_two_accounts)
    service = SearchService(catalog)

    # Act
    service.remove(tenant_id="t-77", song_id="s-201")

    # Assert — pašalinta tik savoji, kitos paskyros to paties id daina liko
    assert catalog.get_track("t-77", "s-201") is None
    assert catalog.get_track("t-88", "s-201") is not None
