"""Duomenų tipai. Specifikacijos 2 skyrius.

Visi tipai yra frozen dataclass'ai: domain sluoksnis gauna duomenis per
argumentus ir grąžina per reikšmes, nieko nekeisdamas vietoje.

Features turi dict lauką (moods), todėl yra nehashable. Tai nieko nelaužo:
pairwise raktai yra song_id eilutės, ne objektai.
"""

import math
from dataclasses import dataclass, field

from .constants import VECTOR_DIM


@dataclass(frozen=True)
class Features:
    vector: tuple[float, ...]        # VECTOR_DIM skaičių, normalizuotas (ilgis 1)
    bpm: float
    key: str                         # Camelot, pvz. "8A"; "" jei nežinoma
    key_confidence: float            # [0; 1]
    loudness_lufs: float
    moods: dict[str, float]          # {"instrumentinė": 0.93, "tamsi": 0.71}
    feature_set: str = "synthetic-v1"

    def __post_init__(self) -> None:
        """Specifikacijos 11 skyriaus patikros.

        Visos kelia ValueError, ne TimbreError: tai duomenų, o ne naudotojo
        klaida. Dokumento 3 skyriaus „atsakymo tikrinimas" reikalauja būtent
        to — vektorius su tuščiomis reikšmėmis paieškai grąžintų šiukšles.
        """
        if len(self.vector) != VECTOR_DIM:
            raise ValueError(
                f"vektoriaus ilgis {len(self.vector)}, turi būti {VECTOR_DIM}"
            )
        for i, x in enumerate(self.vector):
            if not math.isfinite(x):
                raise ValueError(f"vektoriaus reikšmė {i} nėra skaičius: {x!r}")
        if not 0.0 <= self.key_confidence <= 1.0:
            raise ValueError(
                f"key_confidence {self.key_confidence} už intervalo [0; 1]"
            )


@dataclass(frozen=True)
class Track:
    song_id: str
    tenant_id: str
    title: str
    artist: str
    features: Features


@dataclass(frozen=True)
class FilterSpec:
    bpm_min: float | None = None
    bpm_max: float | None = None
    instrumental_only: bool = False


@dataclass(frozen=True)
class CandidatePool:
    candidates: list[Track]
    # Kiek kliento dainų apskritai buvo matoma PRIEŠ filtrus (be užklausos
    # dainos). Be šio skaičiaus neįmanoma pasakyti, ar filtras ką nors atmetė:
    # survivors_per_filter reikšmės to neatskleidžia, kai visi filtrai aktyvūs
    # ir atmeta tą patį rinkinį. Laukas privalomas sąmoningai — jo pamiršti
    # negalima, nes be jo atsakymas būtų tyliai neteisingas.
    visible_count: int
    survivors_per_filter: dict[str, int] = field(default_factory=dict)


@dataclass(frozen=True)
class ScoredTrack:
    track: Track
    total_score: float
    criterion_scores: dict[str, float]


@dataclass(frozen=True)
class ResultItem:
    track: Track
    final_score: float
    criterion_scores: dict[str, float]
    explanations: list[str]


@dataclass(frozen=True)
class SearchResult:
    items: list[ResultItem]
    dalinis_rezultatas: bool
    labiausiai_ribojes_filtras: str | None = None
    removal_counts: dict[str, int] = field(default_factory=dict)
