"""Bendri testų duomenys — pytest fixtures.

Čia gyvena patvirtinto dokumento 3 skyriaus rinkinys (užklausa + šeši
kandidatai K1–K6), kad jo nereikėtų perrašyti kiekviename testų faile.

`tests/test_scoring.py` sąmoningai šių fixtures NENAUDOJA: atraminis testas
turi būti savarankiškas ir skaitomas be jokio kito failo, nes būtent jis
įrodo sutapimą su dėstytojo patvirtintu dokumentu.

Visi duomenys tik atmintyje: jokio tinklo, failų sistemos ar duomenų bazės.
"""

import math

import pytest

from timbre.domain.constants import MOOD_DARK, MOOD_INSTRUMENTAL, VECTOR_DIM
from timbre.domain.models import Features, ScoredTrack, Track
from timbre.domain.scoring import DEFAULT_STRATEGIES, score_all

# Svoriai iš patvirtinto dokumento 3 skyriaus.
DOCUMENT_WEIGHTS = {
    "vector": 0.70,
    "tempo": 0.10,
    "key": 0.05,
    "loudness": 0.05,
    "mood": 0.10,
}

# Užklausos vektorius — pirmoji bazės ašis.
QUERY_VECTOR = tuple([1.0] + [0.0] * (VECTOR_DIM - 1))

# Dokumento kandidatai: song_id, pavadinimas, atlikėjas, kosinusas su
# užklausa, bpm, tonacija, pasitikėjimas, LUFS, instrumentinė, tamsi.
DOCUMENT_ROWS = (
    ("K1", "Nightfield", "Kepler Grove", 0.91, 126.0, "8A", 0.88, -7.5, 0.88, 0.69),
    ("K2", "Nightfield (Remix)", "Kepler Grove", 0.90, 126.0, "8A", 0.86, -7.4, 0.87, 0.70),
    ("K3", "Drift Layer", "Kepler Grove", 0.89, 122.0, "9A", 0.77, -8.8, 0.90, 0.66),
    ("K4", "Slow Tide", "Mara Vale", 0.86, 62.0, "8A", 0.75, -9.0, 0.95, 0.60),
    ("K5", "Copper Dust", "Juno Reef", 0.88, 138.0, "3B", 0.60, -6.0, 0.40, 0.80),
    ("K6", "Inner Field", "A-1021", 0.94, 124.0, "8A", 0.80, -8.0, 0.92, 0.72),
)

# Kandidatų tarpusavio kosinusai iš dokumento įvairovės žingsnio.
DOCUMENT_PAIRWISE = {
    ("K1", "K2"): 0.99,
    ("K1", "K4"): 0.95,
    ("K1", "K5"): 0.55,
}


def unit_vector_with_cosine(target: float) -> tuple[float, ...]:
    """Vienetinis VECTOR_DIM vektorius, kurio kosinusas su QUERY_VECTOR = target.

    Konstrukcija: c = cos*q + sin*p, kur p statmenas q ir sin = sqrt(1-cos^2).
    Tą pačią naudoja ir scripts/seed_catalog.py.
    """
    values = [0.0] * VECTOR_DIM
    values[0] = target
    values[1] = math.sqrt(1.0 - target * target)
    return tuple(values)


def build_features(
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


def build_track(
    song_id: str,
    *,
    title: str = "Daina",
    artist: str = "Atlikejas",
    tenant_id: str = "t-77",
    features: Features | None = None,
    **feature_kwargs: object,
) -> Track:
    """Track su protingomis numatytosiomis reikšmėmis."""
    return Track(
        song_id=song_id,
        tenant_id=tenant_id,
        title=title,
        artist=artist,
        features=features if features is not None else build_features(**feature_kwargs),  # type: ignore[arg-type]
    )


def sort_scored(scored: list[ScoredTrack]) -> list[ScoredTrack]:
    """Rikiuoja mažėjančiai pagal balą, antrinis raktas — song_id."""
    return sorted(scored, key=lambda s: (-s.total_score, s.track.song_id))


@pytest.fixture
def document_query() -> Track:
    """Dokumento užklausa: 124 BPM, 8A (0,81), -8,2 LUFS, atlikėjas A-1021."""
    return build_track("Q", title="Uzklausa", artist="A-1021")


@pytest.fixture
def document_candidates() -> list[Track]:
    """Šeši dokumento kandidatai su visais jų požymiais."""
    return [
        build_track(
            song_id,
            title=title,
            artist=artist,
            features=build_features(
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
        ) in DOCUMENT_ROWS
    ]


@pytest.fixture
def document_scored(
    document_query: Track, document_candidates: list[Track]
) -> list[ScoredTrack]:
    """Dokumento kandidatai, suskaičiuoti ir surikiuoti mažėjančiai."""
    scored = score_all(
        document_query, document_candidates, DOCUMENT_WEIGHTS, DEFAULT_STRATEGIES
    )
    return sort_scored(scored)


@pytest.fixture
def document_pairwise() -> dict[tuple[str, str], float]:
    """Kandidatų tarpusavio kosinusai iš dokumento."""
    return dict(DOCUMENT_PAIRWISE)


@pytest.fixture
def scored_factory():
    """Grąžina funkciją ScoredTrack kūrimui su nurodytu balu."""

    def make(
        song_id: str,
        total_score: float,
        *,
        title: str = "Daina",
        artist: str = "Atlikejas",
        tenant_id: str = "t-77",
    ) -> ScoredTrack:
        return ScoredTrack(
            track=build_track(
                song_id, title=title, artist=artist, tenant_id=tenant_id
            ),
            total_score=total_score,
            criterion_scores={},
        )

    return make
