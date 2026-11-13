"""Paaiškinimai, kodėl daina pateko į rezultatus. Specifikacijos 8 skyrius.

Dokumento išvesties kontraktas garantuoja, kad kiekvienas rezultatas turi bent
MIN_EXPLANATIONS paaiškinimus („kodėl": ["124 ir 126 BPM", "abi
instrumentinės", "tonacijos dera"]). Garantija laikoma besąlygiškai: jei
konkrečių požymių nepakanka, pridedamos bendros frazės iš vektoriaus balo.

Paaiškinimai renkami nuo stipriausio kriterijaus balo žemėjančiai, kad
pirmiausia būtų pasakyta tai, kas labiausiai sutampa.

Modulis grynas: tekstai grąžinami sąrašu, niekas nespausdinama.
"""

from collections.abc import Sequence

from .constants import INSTRUMENTAL_THRESHOLD, MIN_EXPLANATIONS, MOOD_INSTRUMENTAL
from .models import Features, ScoredTrack, Track


def _format_number(value: float) -> str:
    """124.0 -> „124", 123.5 -> „123,5" (lietuviškas dešimtainis skirtukas)."""
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}".replace(".", ",")


def _format_score(value: float) -> str:
    return f"{value:.2f}".replace(".", ",")


def _is_tempo_doubled(query: Features, candidate: Features) -> bool:
    """Ar mažiausią tempo skirtumą davė dvigubinimo atvejis?"""
    direct = abs(query.bpm - candidate.bpm)
    doubled = min(
        abs(2 * query.bpm - candidate.bpm),
        abs(query.bpm - 2 * candidate.bpm),
    )
    return doubled < direct


def _both_instrumental(query: Features, candidate: Features) -> bool:
    return (
        query.moods.get(MOOD_INSTRUMENTAL, 0.0) >= INSTRUMENTAL_THRESHOLD
        and candidate.moods.get(MOOD_INSTRUMENTAL, 0.0) >= INSTRUMENTAL_THRESHOLD
    )


def explain(
    query: Track,
    candidate: ScoredTrack,
    min_count: int = MIN_EXPLANATIONS,
) -> list[str]:
    """Suformuoja paaiškinimų sąrašą vienam rezultatui.

    Sąlygos ir tekstai — iš specifikacijos 8 skyriaus lentelės. Kiekvienam
    kriterijui paimamas tik vienas, labiausiai tinkantis tekstas.
    """
    query_features = query.features
    candidate_features = candidate.track.features
    scores = candidate.criterion_scores

    # (kriterijaus balas, tekstas) — rikiuojama pagal balą mažėjančiai.
    found: list[tuple[float, str]] = []

    tempo = scores.get("tempo", 0.0)
    if tempo >= 0.8:
        first = _format_number(query_features.bpm)
        second = _format_number(candidate_features.bpm)
        if _is_tempo_doubled(query_features, candidate_features):
            found.append((tempo, f"{first} ir {second} BPM - tas pats tempas dvigubai"))
        else:
            found.append((tempo, f"{first} ir {second} BPM"))

    mood = scores.get("mood", 0.0)
    if _both_instrumental(query_features, candidate_features):
        found.append((mood, "abi instrumentinės"))
    elif mood >= 0.9:
        found.append((mood, "panaši nuotaika"))

    key = scores.get("key", 0.0)
    if key >= 0.6:
        found.append((key, "tonacijos dera"))

    loudness = scores.get("loudness", 0.0)
    if loudness >= 0.85:
        found.append((loudness, "panašus garsumas"))

    vector = scores.get("vector", 0.0)
    if vector >= 0.85:
        found.append((vector, "labai panašus skambėjimas"))

    found.sort(key=lambda pair: -pair[0])
    explanations = [text for _, text in found]

    if len(explanations) < min_count:
        explanations.extend(
            _fallbacks(vector, candidate.total_score, min_count - len(explanations))
        )
    return explanations


def _fallbacks(vector_score: float, total_score: float, needed: int) -> Sequence[str]:
    """Bendros frazės, kad garantija „bent min_count" laikytųsi visada."""
    general = [
        f"bendras skambėjimo panašumas {_format_score(vector_score)}",
        f"bendras balas {_format_score(total_score)}",
    ]
    return general[:needed]
