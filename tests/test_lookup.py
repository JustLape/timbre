"""Dainos radimo pagal pavadinimą testai.

Tai „nuorodos" eiga be tinklo: žmogus be paskyros nežino `song_id`, bet iš
nuorodos gaunamas atlikėjas ir pavadinimas. Čia tikrinama, kad jie virsta
kataloge esančia daina.

Du dalykai čia svarbesni už patį radimą:

1. Radus kelias dainas grąžinamos VISOS. Pavadinimas nėra unikalus raktas, ir
   tyliai paėmus pirmą būtų ieškoma panašių į visai kitą kūrinį.
2. Paieška pagal pavadinimą paklūsta tam pačiam matomumui kaip ir paieška
   pagal id. Kitaip ji būtų skylė atskyrime: svetimos dainos id atspėti sunku,
   o pavadinimą — lengva.
"""

import pytest

from timbre.adapters.in_memory import InMemoryCatalog
from timbre.app.search_service import SearchService
from timbre.domain.constants import SHARED_CATALOG
from timbre.domain.errors import ErrorCode, TimbreError

from tests.conftest import build_track


def test_daina_randama_pagal_pavadinima_ir_atlikeja(catalog_with_two_accounts):
    # Arrange
    service = SearchService(InMemoryCatalog(catalog_with_two_accounts))

    # Act
    found = service.find_song(
        tenant_id=SHARED_CATALOG,
        title="Bendra daina 0",
        artist="Bendras atlikejas 0",
    )

    # Assert
    assert [track.song_id for track in found] == ["s-900"]


def test_pavadinimo_paieska_nejautri_raidziu_dydziui(catalog_with_two_accounts):
    # Arrange
    service = SearchService(InMemoryCatalog(catalog_with_two_accounts))

    # Act — kitas raidžių dydis ir tarpai kraštuose
    found = service.find_song(
        tenant_id=SHARED_CATALOG, title="  BENDRA DAINA 0  "
    )

    # Assert
    assert [track.song_id for track in found] == ["s-900"]


def test_atlikejas_nebutinas(catalog_with_two_accounts):
    # Arrange
    service = SearchService(InMemoryCatalog(catalog_with_two_accounts))

    # Act — tik pavadinimas, be atlikėjo
    found = service.find_song(tenant_id=SHARED_CATALOG, title="Bendra daina 1")

    # Assert
    assert [track.song_id for track in found] == ["s-901"]


def test_netinkamas_atlikejas_dainos_neranda(catalog_with_two_accounts):
    # Arrange
    service = SearchService(InMemoryCatalog(catalog_with_two_accounts))

    # Act & Assert — pavadinimas sutampa, atlikėjas ne
    with pytest.raises(TimbreError) as info:
        service.find_song(
            tenant_id=SHARED_CATALOG,
            title="Bendra daina 0",
            artist="Kazkas Kitas",
        )
    assert info.value.code is ErrorCode.DAINA_NERASTA


def test_nerastas_pavadinimas_kelia_daina_nerasta(catalog_with_two_accounts):
    # Arrange
    service = SearchService(InMemoryCatalog(catalog_with_two_accounts))

    # Act & Assert
    with pytest.raises(TimbreError) as info:
        service.find_song(tenant_id=SHARED_CATALOG, title="Tokios dainos nera")
    assert info.value.code is ErrorCode.DAINA_NERASTA


def test_vienodi_pavadinimai_grazinami_visi():
    # Arrange — du skirtingi to paties atlikėjo įrašai tuo pačiu pavadinimu.
    # Realiose bazėse tai norma, ne retenybė.
    tracks = [
        build_track("s-1", title="Billie Jean", artist="Michael Jackson", axis=1),
        build_track("s-2", title="Billie Jean", artist="Michael Jackson", axis=2),
    ]
    service = SearchService(InMemoryCatalog(tracks))

    # Act
    found = service.find_song(
        tenant_id=SHARED_CATALOG, title="Billie Jean", artist="Michael Jackson"
    )

    # Assert — abu grąžinami, pasirinkimas paliekamas naudotojui
    assert [track.song_id for track in found] == ["s-1", "s-2"]


def test_svetimos_paskyros_daina_nerandama_pagal_pavadinima(catalog_with_two_accounts):
    # Arrange — „Tik t-88 daina" priklauso tik paskyrai t-88
    service = SearchService(InMemoryCatalog(catalog_with_two_accounts))

    # Act & Assert — t-77 žino pavadinimą, bet jam tos dainos nėra
    with pytest.raises(TimbreError) as info:
        service.find_song(tenant_id="t-77", title="Tik t-88 daina")
    assert info.value.code is ErrorCode.DAINA_NERASTA


def test_savo_ikelta_daina_randama_pagal_pavadinima(catalog_with_two_accounts):
    # Arrange — teigiama kontrolė ankstesniam testui: be jos jis praeitų ir
    # tuomet, jei paieška pagal pavadinimą apskritai nieko nerastų.
    service = SearchService(InMemoryCatalog(catalog_with_two_accounts))

    # Act
    found = service.find_song(tenant_id="t-88", title="Tik t-88 daina")

    # Assert
    assert [track.song_id for track in found] == ["s-999"]
