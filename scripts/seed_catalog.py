"""Determinuotas katalogo generatorius. Specifikacijos 4 skyrius.

Paleidimas iš projekto šaknies:

    python scripts/seed_catalog.py

Determinuotas: naudojamas `random.Random(SEED)`, o ne globalus `random.seed()`;
jokio laiko, aplinkos ar tinklo. Tas pats paleidimas visada duoda tą patį failą,
todėl `data/catalog.json` galima commitinti ir dėstytojas, nuklonavęs
repozitoriją, iš karto turi duomenis.

Požymiai čia SUGENERUOTI, o ne išvesti iš tikro garso. Tai sąmoningas II etapo
supaprastinimas: formulės ir balų skaičiavimas yra tikri ir vykdomi užklausos
metu, bet vektoriai nėra neuroninio tinklo išvestis. Laukas `feature_set`
tam ir yra — III etape kataloge galės būti abu rinkiniai.

Vektorių konstrukcija ir kodėl būtent tokia
-------------------------------------------
Užklausos vektorius yra pirmoji bazės ašis q = e0. Kiekvienai kitai dainai
imama SAVA statmena ašis e_i ir vektorius sudaromas kaip

    c_i = cos_i * q + sin_i * e_i,   sin_i = sqrt(1 - cos_i^2)

Tada cos(q, c_i) = cos_i tiksliai, o cos(c_i, c_j) = cos_i * cos_j.

Sava ašis kiekvienai dainai yra būtina, ne kosmetika. Jei visos dainos
naudotų tą pačią statmeną ašį, jos gulėtų vienoje plokštumoje ir jų tarpusavio
kosinusai būtų ~0,99 — tada dublikatų taisyklė (> 0,98) išmestų beveik visus
kandidatus ir paieška grąžintų tuščią sąrašą.
"""

import json
import math
import random
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from timbre.domain.constants import (  # noqa: E402
    MOOD_DARK,
    MOOD_INSTRUMENTAL,
    VECTOR_DIM,
)

SEED = 20261113
FEATURE_SET = "synthetic-v1"
OUTPUT_PATH = PROJECT_ROOT / "data" / "catalog.json"

CAMELOT_KEYS = [f"{number}{letter}" for letter in ("A", "B") for number in range(1, 13)]

# Patvirtinto I etapo dokumento 3 skyriaus rinkinys.
# song_id, pavadinimas, atlikėjas, kosinusas, bpm, tonacija, pasitikėjimas,
# LUFS, instrumentinė, tamsi
DOCUMENT_TRACKS = (
    ("t-0001", "Nightfield", "Kepler Grove", 0.91, 126.0, "8A", 0.88, -7.5, 0.88, 0.69),
    ("t-0002", "Nightfield (Remix)", "Kepler Grove", 0.90, 126.0, "8A", 0.86, -7.4, 0.87, 0.70),
    ("t-0003", "Drift Layer", "Kepler Grove", 0.89, 122.0, "9A", 0.77, -8.8, 0.90, 0.66),
    ("t-0004", "Slow Tide", "Mara Vale", 0.86, 62.0, "8A", 0.75, -9.0, 0.95, 0.60),
    ("t-0005", "Copper Dust", "Juno Reef", 0.88, 138.0, "3B", 0.60, -6.0, 0.40, 0.80),
    ("t-0006", "Inner Field", "A-1021", 0.94, 124.0, "8A", 0.80, -8.0, 0.92, 0.72),
)

TENANT_A = "t-77"
TENANT_B = "t-88"

ARTISTS_A = (
    "Halide Bloom", "Vesper Lane", "Quiet Ferrite", "Nordal Set", "Amber Kiln",
    "Soft Meridian", "Cobalt Hour", "Pale Orbit", "Tin Garden", "Low Signal",
    "Marrow Fields", "Glass Harbour", "Rust Chapel",
)
ARTISTS_B = ("Studio B Collective", "Ember Rota", "Null Coast", "Saltwire", "Dim Atlas")

TITLE_PARTS_FIRST = (
    "Hollow", "Amber", "Quiet", "Distant", "Paper", "Iron", "Violet", "Slow",
    "Northern", "Dusty", "Second", "Winter", "Shallow", "Bright", "Soft",
)
TITLE_PARTS_SECOND = (
    "Harbour", "Signal", "Meridian", "Chapel", "Orbit", "Garden", "Tide",
    "Field", "Layer", "Dust", "Current", "Window", "Lantern", "Mirror", "Season",
)


def unit_vector(cosine_to_query: float, axis: int) -> list[float]:
    """Vienetinis vektorius, kurio kosinusas su e0 yra cosine_to_query."""
    if axis <= 0 or axis >= VECTOR_DIM:
        raise ValueError(f"statmena ašis {axis} netelpa į {VECTOR_DIM} matavimų")
    values = [0.0] * VECTOR_DIM
    values[0] = cosine_to_query
    values[axis] = math.sqrt(max(0.0, 1.0 - cosine_to_query * cosine_to_query))
    return [round(value, 6) for value in values]


def make_entry(
    song_id: str,
    tenant_id: str,
    title: str,
    artist: str,
    cosine_to_query: float,
    axis: int,
    bpm: float,
    key: str,
    key_confidence: float,
    loudness_lufs: float,
    instrumental: float,
    dark: float,
) -> dict:
    return {
        "song_id": song_id,
        "tenant_id": tenant_id,
        "title": title,
        "artist": artist,
        "features": {
            "vector": unit_vector(cosine_to_query, axis),
            "bpm": round(bpm, 1),
            "key": key,
            "key_confidence": round(key_confidence, 2),
            "loudness_lufs": round(loudness_lufs, 1),
            "moods": {
                MOOD_INSTRUMENTAL: round(instrumental, 2),
                MOOD_DARK: round(dark, 2),
            },
        },
    }


def build_catalog() -> dict:
    rng = random.Random(SEED)
    tracks: list[dict] = []
    axis = 1

    # --- Klientas t-77: užklausos daina ---
    # Užklausos vektorius yra pati ašis e0, todėl kosinusas su kandidatu
    # lygus to kandidato cos reikšmei.
    query = make_entry(
        "t-0000", TENANT_A, "Pateikta daina", "A-1021",
        cosine_to_query=1.0, axis=1, bpm=124.0, key="8A", key_confidence=0.81,
        loudness_lufs=-8.2, instrumental=0.93, dark=0.71,
    )
    query["features"]["vector"] = [1.0] + [0.0] * (VECTOR_DIM - 1)
    tracks.append(query)

    # --- Klientas t-77: dokumento kandidatai ---
    for row in DOCUMENT_TRACKS:
        (song_id, title, artist, cosine_to_query, bpm, key,
         key_confidence, loudness_lufs, instrumental, dark) = row
        tracks.append(
            make_entry(song_id, TENANT_A, title, artist, cosine_to_query, axis,
                       bpm, key, key_confidence, loudness_lufs, instrumental, dark)
        )
        axis += 1

    # --- Klientas t-77: užpildas ---
    # Kiekvienam atlikėjui pirmoji daina sąmoningai patenka į demonstracijos
    # langą (tempas 118-130, instrumentinė), kad po atlikėjo limito 1 tikrai
    # susidarytų pilnas dešimtukas iš skirtingų atlikėjų.
    song_number = 7
    for artist_index, artist in enumerate(ARTISTS_A):
        for position in range(4):
            in_demo_window = position == 0
            bpm = rng.uniform(118.0, 130.0) if in_demo_window else rng.uniform(60.0, 180.0)
            instrumental = rng.uniform(0.6, 1.0) if in_demo_window else rng.uniform(0.0, 1.0)
            tracks.append(
                make_entry(
                    f"t-{song_number:04d}", TENANT_A,
                    f"{rng.choice(TITLE_PARTS_FIRST)} {rng.choice(TITLE_PARTS_SECOND)}",
                    artist,
                    cosine_to_query=rng.uniform(0.10, 0.85),
                    axis=axis,
                    bpm=bpm,
                    key=rng.choice(CAMELOT_KEYS),
                    key_confidence=rng.uniform(0.40, 0.95),
                    loudness_lufs=rng.uniform(-14.0, -5.0),
                    instrumental=instrumental,
                    dark=rng.uniform(0.0, 1.0),
                )
            )
            song_number += 1
            axis += 1

    # --- Klientas t-88: savo užklausa ir savo dainos ---
    tracks.append(
        make_entry(
            "t-0100", TENANT_B, "B pateikta daina", "Studio B Collective",
            cosine_to_query=0.99, axis=axis, bpm=120.0, key="5A",
            key_confidence=0.78, loudness_lufs=-7.9, instrumental=0.88, dark=0.55,
        )
    )
    axis += 1

    song_number = 101
    for artist in ARTISTS_B:
        for position in range(4):
            in_demo_window = position == 0
            bpm = rng.uniform(118.0, 130.0) if in_demo_window else rng.uniform(60.0, 180.0)
            instrumental = rng.uniform(0.6, 1.0) if in_demo_window else rng.uniform(0.0, 1.0)
            tracks.append(
                make_entry(
                    f"t-{song_number:04d}", TENANT_B,
                    f"{rng.choice(TITLE_PARTS_FIRST)} {rng.choice(TITLE_PARTS_SECOND)}",
                    artist,
                    cosine_to_query=rng.uniform(0.10, 0.85),
                    axis=axis,
                    bpm=bpm,
                    key=rng.choice(CAMELOT_KEYS),
                    key_confidence=rng.uniform(0.40, 0.95),
                    loudness_lufs=rng.uniform(-14.0, -5.0),
                    instrumental=instrumental,
                    dark=rng.uniform(0.0, 1.0),
                )
            )
            song_number += 1
            axis += 1

    return {
        "feature_set": FEATURE_SET,
        "generated_with_seed": SEED,
        "tracks": tracks,
    }


def main() -> int:
    catalog = build_catalog()
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_PATH.open("w", encoding="utf-8") as handle:
        json.dump(catalog, handle, ensure_ascii=False, indent=1)
        handle.write("\n")

    by_tenant: dict[str, int] = {}
    for track in catalog["tracks"]:
        by_tenant[track["tenant_id"]] = by_tenant.get(track["tenant_id"], 0) + 1
    size_kb = OUTPUT_PATH.stat().st_size / 1024

    print(f"Irasyta: {OUTPUT_PATH}")
    print(f"Dainu: {len(catalog['tracks'])} ({size_kb:.0f} KB), seed {SEED}")
    for tenant, count in sorted(by_tenant.items()):
        print(f"  klientas {tenant}: {count}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
