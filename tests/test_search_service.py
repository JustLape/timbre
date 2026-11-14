"""Paieškos scenarijaus testai. Specifikacijos 12 skyrius.

Katalogas visur yra `InMemoryCatalog`, todėl testai nieko neskaito iš disko ir
nepaveikia nei vienas kito, nei demonstracijos duomenų.
"""

import pytest

from timbre.adapters.in_memory import InMemoryCatalog
from timbre.app.search_service import SearchService
from timbre.domain.errors import ErrorCode, TimbreError
from timbre.domain.constants import MOOD_INSTRUMENTAL
from timbre.domain.models import FilterSpec

from tests.conftest import build_features, build_track


def make_service(tracks) -> SearchService:
    return SearchService(InMemoryCatalog(tracks))


def test_per_siauras_filtras_grazina_dalini_rezultata(filter_catalog_tracks):
    # Arrange — filtrą praeina tik 4 dainos, o prašoma 10
    service = make_service(filter_catalog_tracks)

    # Act
    result = service.search(
        tenant_id="t-77",
        song_id="Q",
        filters=FilterSpec(bpm_min=121.0, bpm_max=123.0),
        limit=10,
    )

    # Assert — ne klaida ir ne tuščias sąrašas
    assert len(result.items) == 4
    assert result.dalinis_rezultatas is True


def test_dalinis_rezultatas_nurodo_labiausiai_ribojusi_filtra(filter_catalog_tracks):
    # Arrange
    service = make_service(filter_catalog_tracks)

    # Act
    result = service.search(
        tenant_id="t-77",
        song_id="Q",
        filters=FilterSpec(bpm_min=121.0, bpm_max=123.0),
        limit=10,
    )

    # Assert
    assert result.labiausiai_ribojes_filtras == "bpm"


def test_dublikatu_salinimas_nenurodo_ribojusio_filtro(document_query, document_candidates):
    # Arrange — jokių filtrų; rezultatų mažiau vien dėl dublikatų ir atlikėjo limito
    service = make_service([document_query] + document_candidates)

    # Act
    result = service.search(
        tenant_id="t-77", song_id="Q", filters=FilterSpec(), limit=10
    )

    # Assert
    assert result.dalinis_rezultatas is True
    assert result.labiausiai_ribojes_filtras is None


def test_nerastos_dainos_uzklausa_kelia_daina_nerasta(document_query, document_candidates):
    # Arrange
    service = make_service([document_query] + document_candidates)

    # Act & Assert
    with pytest.raises(TimbreError) as info:
        service.search(
            tenant_id="t-77", song_id="nera-tokios", filters=FilterSpec(), limit=10
        )
    assert info.value.code is ErrorCode.DAINA_NERASTA


def test_kiekvienas_rezultatas_turi_bent_du_paaiskinimus(document_query, document_candidates):
    # Arrange
    service = make_service([document_query] + document_candidates)

    # Act
    result = service.search(
        tenant_id="t-77", song_id="Q", filters=FilterSpec(), limit=10
    )

    # Assert
    assert result.items
    assert all(len(item.explanations) >= 2 for item in result.items)


def test_pirmas_rezultatas_turi_auksciausia_bala(filter_catalog_tracks):
    """Specifikacijos lentelėje šis testas pavadintas „balai mažėja".

    Toks jis būti negali, ir tai ne kodo klaida. Patvirtinto dokumento
    1 scenarijus tikrai sako „balai mažėja", bet to paties dokumento
    skaičiavimo pavyzdys duoda eilę K1 (0,908) -> K5 (0,720) -> K4 (0,877):
    7 taisyklė (įvairovė) SĄMONINGAI perstato kandidatą su mažesniu balu į
    priekį, nes K4 per daug panaši į jau atrinktą K1. Dokumentas šiose dviejose
    vietose sau prieštarauja.

    Įgyvendinta 7 taisyklė, nes ji turi ir formulę, ir pilnai suskaičiuotą
    pavyzdį. Todėl čia tikrinama garantija, kuri tikrai laikosi: pirmas
    rezultatas visada yra didžiausio balo, nes įvairovės žingsnis pirmą
    kandidatą renka be baudos.
    """
    # Arrange
    service = make_service(filter_catalog_tracks)

    # Act
    result = service.search(
        tenant_id="t-77", song_id="Q", filters=FilterSpec(), limit=10
    )

    # Assert
    scores = [item.final_score for item in result.items]
    assert scores[0] == max(scores)


def test_ta_pati_uzklausa_duoda_ta_pacia_eile(filter_catalog_tracks):
    # Arrange — lygių balų atveju eilė neturi priklausyti nuo žodyno tvarkos
    service = make_service(filter_catalog_tracks)

    # Act
    orders = [
        [
            item.track.song_id
            for item in service.search(
                tenant_id="t-77", song_id="Q", filters=FilterSpec(), limit=10
            ).items
        ]
        for _ in range(5)
    ]

    # Assert
    assert all(order == orders[0] for order in orders)


def test_uzklausos_daina_negrazinama_tarp_rezultatu(filter_catalog_tracks):
    # Arrange
    service = make_service(filter_catalog_tracks)

    # Act
    result = service.search(
        tenant_id="t-77", song_id="Q", filters=FilterSpec(), limit=10
    )

    # Assert
    assert "Q" not in [item.track.song_id for item in result.items]


def test_filtro_neatitinkanciu_dainu_rezultatuose_nera(filter_catalog_tracks):
    # Arrange — nepraeinančios dainos turi didesnį vektoriaus panašumą,
    # tad be filtravimo paieškos metu jos būtų pirmos
    service = make_service(filter_catalog_tracks)

    # Act
    result = service.search(
        tenant_id="t-77",
        song_id="Q",
        filters=FilterSpec(bpm_min=121.0, bpm_max=123.0),
        limit=10,
    )

    # Assert
    assert all(121.0 <= item.track.features.bpm <= 123.0 for item in result.items)


# --- Testai, pridėti po mutacijų audito -------------------------------------
# `NETINKAMAS_FILTRAS` — vienas iš keturių dokumento klaidų kodų — iki audito
# neturėjo nė vieno testo.


def test_nulinis_rezultatu_kiekis_kelia_netinkamas_filtras(filter_catalog_tracks):
    # Act & Assert
    with pytest.raises(TimbreError) as info:
        make_service(filter_catalog_tracks).search(
            tenant_id="t-77", song_id="Q", filters=FilterSpec(), limit=0
        )
    assert info.value.code is ErrorCode.NETINKAMAS_FILTRAS


def test_apverstas_tempo_intervalas_kelia_netinkamas_filtras(filter_catalog_tracks):
    # Act & Assert
    with pytest.raises(TimbreError) as info:
        make_service(filter_catalog_tracks).search(
            tenant_id="t-77",
            song_id="Q",
            filters=FilterSpec(bpm_min=130.0, bpm_max=118.0),
            limit=10,
        )
    assert info.value.code is ErrorCode.NETINKAMAS_FILTRAS


def test_nulinis_atlikejo_limitas_kelia_netinkamas_filtras(filter_catalog_tracks):
    """Be šios patikros `--artist-limit 0` tyliai grąžindavo tuščią sąrašą."""
    # Act & Assert
    with pytest.raises(TimbreError) as info:
        make_service(filter_catalog_tracks).search(
            tenant_id="t-77",
            song_id="Q",
            filters=FilterSpec(),
            limit=10,
            artist_limit=0,
        )
    assert info.value.code is ErrorCode.NETINKAMAS_FILTRAS


def test_pasalinimo_skaitikliai_tikrai_skaiciuoja(document_query, document_candidates):
    """Mutacija, paverčianti visus `removal_counts` nuliais, nebuvo pagauta."""
    # Arrange — dokumento rinkinyje K2 yra dublikatas, o K6 ir K3 krenta
    # pagal atlikėjo limitą
    service = make_service([document_query] + document_candidates)

    # Act
    result = service.search(
        tenant_id="t-77", song_id="Q", filters=FilterSpec(), limit=10
    )

    # Assert
    assert result.removal_counts["duplicates"] >= 1
    assert result.removal_counts["artist_limit"] >= 2


def test_abu_filtrai_atmete_ta_pati_rinkini_vis_tiek_nurodo_filtra():
    """Ankstesnė versija nefiltruotų kandidatų kiekį spėdavo kaip didžiausią
    `survivors_per_filter` reikšmę. Kai abu filtrai aktyvūs ir atmeta tą patį
    rinkinį, visos reikšmės lygios, ir laukas tyliai likdavo tuščias — CLI
    rašydavo „filtrai nieko neatmetė", nors atmetė."""
    # Arrange — 6 matomos dainos, abu filtrai praleidžia tas pačias 2
    tracks = [build_track("Q", title="Uzklausa", artist="A-1021", axis=1)]
    for index in range(2):
        tracks.append(
            build_track(
                f"G{index}",
                title=f"Gera {index}",
                artist=f"Geras {index}",
                features=build_features(
                    cosine_to_query=0.8,
                    axis=2 + index,
                    bpm=122.0,
                    moods={MOOD_INSTRUMENTAL: 0.9},
                ),
            )
        )
    for index in range(4):
        tracks.append(
            build_track(
                f"B{index}",
                title=f"Bloga {index}",
                artist=f"Blogas {index}",
                features=build_features(
                    cosine_to_query=0.9,
                    axis=10 + index,
                    bpm=60.0,
                    moods={MOOD_INSTRUMENTAL: 0.1},
                ),
            )
        )

    # Act
    result = make_service(tracks).search(
        tenant_id="t-77",
        song_id="Q",
        filters=FilterSpec(bpm_min=121.0, bpm_max=123.0, instrumental_only=True),
        limit=10,
    )

    # Assert
    assert len(result.items) == 2
    assert result.labiausiai_ribojes_filtras is not None
