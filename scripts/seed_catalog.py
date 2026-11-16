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

Šis failas yra vienintelė vieta, kurią reikės pakeisti, kad kataloge atsirastų tikri
duomenys: `domain/` vektorių negamina, o tik gauna. Patikrinta, kad 256 skaičių
vektorius susideda iš AcousticBrainz CC0 iškrovų be jokio garso apdorojimo
(13 `mfcc.mean` + 91 kovariacijos viršutinis trikampis + tie patys 13 ir 91 iš `gfcc`
= 208, plius 48 spektriniai skaliarai). Užrašyta čia, kad nereikėtų ieškoti iš naujo.

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
    SHARED_CATALOG,
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

# Kiek dainų sugeneruoti BENDRAME kataloge. Bendras katalogas yra produkto
# esmė, todėl jis sąmoningai didelis, o klientų katalogai lieka maži: jie
# vaizduoja žmogaus įkeltas dainas, o ne biblioteką.
SHARED_FILLER = 600
SONGS_PER_ARTIST = 4

# Užpildo kosinusas su užklausa niekada neviršija šios ribos.
#
# KĄ ŠI RIBA GARANTUOJA. Dokumento pavyzdyje tie šeši kandidatai yra patys
# panašiausi kataloge — toks ir buvo pavyzdžio teiginys. Prie 0,55 geriausio
# užpildo bendras balas yra ~0,61, t. y. žemiau prasčiausio dokumento
# kandidato K5 „Copper Dust" (0,720). Todėl visi šeši dokumento balai lieka
# kataloge aukščiausi ir atsikuria tiksliai: 0,945 · 0,908 · 0,900 · 0,883 ·
# 0,877 · 0,720.
#
# KO JI NEGARANTUOJA. Galutinės dokumento EILĖS K1 -> K5 -> K4 didelis
# katalogas nebeatkuria, ir tai ne klaida, o įvairovės taisyklė, dirbanti taip,
# kaip aprašyta. Po K1 ir K4 atrinkimo K5 pataisyta vertė yra
#     0,7 x 0,720 - 0,3 x 0,801 = 0,264,
# nes K5 yra 0,80 panašus į jau atrinktą K1. Užpildo daina, kurios vektoriaus
# panašumas mažas, bet tempas ir nuotaika sutampa, gauna panašų balą ir
# KUR KAS mažesnę baudą, tad aplenkia K5. Su 59 dainomis tokių alternatyvų
# tiesiog nebuvo, todėl anksčiau K5 patekdavo.
#
# Tai geras, o ne blogas rezultatas: būtent taip matyti, kad įvairovės
# žingsnis realiai ką nors daro.
FILLER_MAX_COSINE = 0.55

ARTISTS_A = (
    "Halide Bloom", "Vesper Lane", "Quiet Ferrite", "Nordal Set", "Amber Kiln",
    "Soft Meridian", "Cobalt Hour", "Pale Orbit", "Tin Garden", "Low Signal",
    "Marrow Fields", "Glass Harbour", "Rust Chapel",
)
ARTISTS_B = ("Studio B Collective", "Ember Rota", "Null Coast", "Saltwire", "Dim Atlas")

# Bendro katalogo atlikėjai sudaromi iš dalių, nes jų reikia pusantro šimto.
ARTIST_FIRST = (
    "Northern", "Paper", "Velvet", "Granite", "Hollow", "Saffron", "Cedar",
    "Lunar", "Harbor", "Ashen", "Tundra", "Opal", "Cinder", "Willow", "Basalt",
)
ARTIST_SECOND = (
    "Union", "Theory", "Choir", "Division", "Society", "Parade", "Assembly",
    "Project", "Quartet", "Machine",
)

TITLE_PARTS_FIRST = (
    "Hollow", "Amber", "Quiet", "Distant", "Paper", "Iron", "Violet", "Slow",
    "Northern", "Dusty", "Second", "Winter", "Shallow", "Bright", "Soft",
    "Hidden", "Golden", "Silent", "Frozen", "Crimson", "Velvet", "Marble",
    "Copper", "Silver", "Midnight", "Morning", "Autumn", "Summer", "Narrow",
    "Open", "Pale", "Deep", "Wild", "Still", "Faded", "Broken", "Gentle",
    "Rising", "Endless", "Hazy",
)
TITLE_PARTS_SECOND = (
    "Harbour", "Signal", "Meridian", "Chapel", "Orbit", "Garden", "Tide",
    "Field", "Layer", "Dust", "Current", "Window", "Lantern", "Mirror", "Season",
    "Valley", "River", "Tower", "Bridge", "Shore", "Anchor", "Compass", "Ember",
    "Prism", "Echo", "Drift", "Shadow", "Circuit", "Horizon", "Pulse", "Canyon",
    "Terrace", "Beacon", "Thread", "Vessel", "Meadow", "Glacier", "Summit",
    "Corridor", "Spiral",
)


def unit_vector(cosine_to_query: float, axis: int) -> list[float]:
    """Vienetinis vektorius, kurio kosinusas su e0 yra cosine_to_query."""
    if axis <= 0 or axis >= VECTOR_DIM:
        raise ValueError(f"statmena ašis {axis} netelpa į {VECTOR_DIM} matavimų")
    values = [0.0] * VECTOR_DIM
    values[0] = cosine_to_query
    values[axis] = math.sqrt(max(0.0, 1.0 - cosine_to_query * cosine_to_query))
    return [round(value, 6) for value in values]


def random_vector(rng: random.Random, cosine_to_query: float) -> list[float]:
    """Vienetinis vektorius, kurio kosinusas su e0 yra tiksliai nurodytas.

    Skiriasi nuo `unit_vector` tuo, kad statmenoji dalis yra ATSITIKTINĖ
    kryptis, o ne atskira bazės ašis. Tai būtina: ašių yra tik 255, tad ašių
    būdu daugiau nei 255 dainų sugeneruoti fiziškai neįmanoma, o bendrame
    kataloge jų reikia šimtų.

    Ar tai saugu dublikatų taisyklei (> 0,98)? Taip. Dviejų tokių dainų
    tarpusavio kosinusas yra cos_i*cos_j + sin_i*sin_j*r, kur r yra dviejų
    atsitiktinių krypčių sandauga — jos vidurkis 0, o standartinis nuokrypis
    1/sqrt(255) = 0,063. Blogiausiu atveju (abu kosinusai lygūs 0,85 ribai,
    r nukrypęs per keturis nuokrypius) gaunama 0,72 + 0,07 = 0,79, t. y. gerai
    po riba. Dokumento kandidatai lieka ant ašių, tad jų skaičiai nesikeičia.
    """
    rest = [rng.gauss(0.0, 1.0) for _ in range(VECTOR_DIM - 1)]
    norm = math.sqrt(sum(value * value for value in rest))
    scale = math.sqrt(max(0.0, 1.0 - cosine_to_query * cosine_to_query)) / norm
    return [round(cosine_to_query, 6)] + [round(value * scale, 6) for value in rest]


def shared_artists(count: int) -> list[str]:
    """Determinuotas bendro katalogo atlikėjų sąrašas."""
    names = [
        f"{first} {second}" for second in ARTIST_SECOND for first in ARTIST_FIRST
    ]
    if count > len(names):
        raise RuntimeError(f"reikia {count} atlikėjų, o sudaromi tik {len(names)}")
    return names[:count]


def unique_title(rng: random.Random, used: set[str]) -> str:
    """Sugeneruoja dar nenaudotą pavadinimą.

    Be unikalumo patikros iš 15x15 dalių traukiant penkias dešimtis kartų
    atsitiktiniai sutapimai yra beveik neišvengiami, ir tada dublikatų
    taisyklė išmeta dainas, kurių niekas sąmoningai nepadarė dublikatais —
    demonstracijoje tai atrodo kaip klaida. Vienintelis sąmoningas dublikatas
    turi likti „Nightfield (Remix)".
    """
    for _ in range(500):
        title = f"{rng.choice(TITLE_PARTS_FIRST)} {rng.choice(TITLE_PARTS_SECOND)}"
        if title not in used:
            used.add(title)
            return title
    raise RuntimeError("nepavyko sugeneruoti unikalaus pavadinimo")


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


def make_filler(
    rng: random.Random,
    song_id: str,
    tenant_id: str,
    artist: str,
    used_titles: set[str],
    in_demo_window: bool,
) -> dict:
    """Viena užpildo daina su atsitiktine, bet determinuota kryptimi.

    `in_demo_window` dainą sąmoningai įstato į demonstracijos langą (tempas
    118–130, instrumentinė), kad po atlikėjo limito 1 tikrai susidarytų pilnas
    dešimtukas iš skirtingų atlikėjų.
    """
    bpm = rng.uniform(118.0, 130.0) if in_demo_window else rng.uniform(60.0, 180.0)
    instrumental = rng.uniform(0.6, 1.0) if in_demo_window else rng.uniform(0.0, 1.0)
    return {
        "song_id": song_id,
        "tenant_id": tenant_id,
        "title": unique_title(rng, used_titles),
        "artist": artist,
        "features": {
            "vector": random_vector(rng, rng.uniform(0.10, FILLER_MAX_COSINE)),
            "bpm": round(bpm, 1),
            "key": rng.choice(CAMELOT_KEYS),
            "key_confidence": round(rng.uniform(0.40, 0.95), 2),
            "loudness_lufs": round(rng.uniform(-14.0, -5.0), 1),
            "moods": {
                MOOD_INSTRUMENTAL: round(instrumental, 2),
                MOOD_DARK: round(rng.uniform(0.0, 1.0), 2),
            },
        },
    }


def build_catalog() -> dict:
    """Sudaro katalogą iš trijų dalių: bendro katalogo ir dviejų paskyrų.

    Dalijimas atitinka matomumo taisyklę (`adapters/in_memory.py`):

        bendras   atsakymų šaltinis, matomas visiems
        t-77      paskyros įkeltos dainos, matomos tik jai
        t-88      kitos paskyros įkeltos dainos

    Dokumento pavyzdys gyvena BENDRAME kataloge, nes atsakymai imami tik iš
    jo. Būtent todėl `--tenant bendras --song-id t-0000` atkuria patvirtinto
    I etapo dokumento eilę.
    """
    rng = random.Random(SEED)
    tracks: list[dict] = []
    # Dokumento pavadinimai užimami iš anksto, kad užpildas su jais nesutaptų
    # ir nepadarytų atsitiktinio dublikato.
    used_titles: set[str] = {row[1] for row in DOCUMENT_TRACKS}

    # --- Bendras katalogas: dokumento užklausa ---
    # Užklausos vektorius yra pati ašis e0, todėl kosinusas su kandidatu
    # lygus to kandidato cos reikšmei.
    query = make_entry(
        "t-0000", SHARED_CATALOG, "Pateikta daina", "A-1021",
        cosine_to_query=1.0, axis=1, bpm=124.0, key="8A", key_confidence=0.81,
        loudness_lufs=-8.2, instrumental=0.93, dark=0.71,
    )
    query["features"]["vector"] = [1.0] + [0.0] * (VECTOR_DIM - 1)
    tracks.append(query)

    # --- Bendras katalogas: dokumento kandidatai ---
    # Šie lieka ant atskirų ašių, kad dokumento skaičiai atsikurtų tiksliai.
    axis = 1
    for row in DOCUMENT_TRACKS:
        (song_id, title, artist, cosine_to_query, bpm, key,
         key_confidence, loudness_lufs, instrumental, dark) = row
        tracks.append(
            make_entry(song_id, SHARED_CATALOG, title, artist, cosine_to_query,
                       axis, bpm, key, key_confidence, loudness_lufs,
                       instrumental, dark)
        )
        axis += 1

    # --- Bendras katalogas: užpildas ---
    song_number = 7
    for artist in shared_artists(SHARED_FILLER // SONGS_PER_ARTIST):
        for position in range(SONGS_PER_ARTIST):
            tracks.append(
                make_filler(rng, f"t-{song_number:04d}", SHARED_CATALOG,
                            artist, used_titles, in_demo_window=position == 0)
            )
            song_number += 1

    # --- Paskyra t-77: jos pačios įkeltos dainos ---
    # Jos NIEKADA nebūna atsakyme, net savininkui: jos skirtos tik tam, kad
    # žmogus galėtų ieškoti panašių į savo dainą.
    song_number = 2000
    for artist in ARTISTS_A:
        for position in range(SONGS_PER_ARTIST):
            tracks.append(
                make_filler(rng, f"t-{song_number:04d}", TENANT_A,
                            artist, used_titles, in_demo_window=position == 0)
            )
            song_number += 1

    # --- Paskyra t-88: kitos paskyros įkeltos dainos ---
    song_number = 3000
    for artist in ARTISTS_B:
        for position in range(SONGS_PER_ARTIST):
            tracks.append(
                make_filler(rng, f"t-{song_number:04d}", TENANT_B,
                            artist, used_titles, in_demo_window=position == 0)
            )
            song_number += 1

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
