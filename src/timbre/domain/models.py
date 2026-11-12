from dataclasses import dataclass, field


@dataclass(frozen=True)
class Features:
    vector: tuple[float, ...]
    bpm: float
    key: str
    key_confidence: float
    loudness_lufs: float
    valence: float
    energy: float
    instrumental: bool
    feature_set: str = "synthetic-v1"


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