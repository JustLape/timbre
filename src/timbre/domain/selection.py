"""Atranka: dublikatai, atlikėjo limitas, įvairovė. Specifikacijos 7 skyrius.

Taisyklės iš patvirtinto I etapo dokumento 3 skyriaus (5, 6 ir 7 taisyklės).
Tvarka yra verslo taisyklė, ne įgyvendinimo detalė:

    dublikatai -> atlikėjo limitas -> įvairovė

Visos trys funkcijos gauna JAU pagal balą mažėjančiai surikiuotą sąrašą ir
grąžina pašalintų kiekį, kad app/search_service.py galėtų užpildyti
removal_counts.

Kandidatų tarpusavio panašumai (pairwise) čia PRIIMAMI argumentu ir niekada
neskaičiuojami iš vektorių. Taip yra dėl dviejų priežasčių. Pirma, tai leidžia
atkurti dokumento pavyzdį: jame tarpusavio kosinusai pateikti kaip
ilustratyvūs duomenys, nepriklausomi nuo vektorių (prie cos(q,K1) = 0,91 ir
cos(q,K5) = 0,88 trikampio nelygybė leistų cos(K1,K5) tik intervale
[0,6039; 0,9977], o pavyzdyje nurodyta 0,55). Antra, tai ir teisingas
projektavimo sprendimas savaime: tarpusavio panašumus gali pateikti indeksas,
kuris juos jau turi.
"""

import re
from collections.abc import Mapping, Sequence

from .constants import (
    DEFAULT_ARTIST_LIMIT,
    DUPLICATE_COSINE,
    MMR_PENALTY,
    MMR_RELEVANCE,
)
from .models import ScoredTrack

# Versijos žymės, nuimamos norminant pavadinimą. Sąrašas yra TIKSLIAI toks,
# kaip patvirtintame dokumente — neplėsti savo nuožiūra, nes `edit` ar
# `version` atskirai išmestų ir teisėtus pavadinimus kaip „The Edit".
# Ilgesnės frazės tikrinamos pirmiau nei trumpesni žodžiai.
_VERSION_MARKERS = ("radio edit", "remastered", "remaster", "remix", "live")

_BRACKETS = re.compile(r"[\(\[][^\)\]]*[\)\]]")
_FEATURING = re.compile(r"\b(feat|ft|featuring)\b.*$")
_NON_WORD = re.compile(r"[^\w\s]")
_SPACES = re.compile(r"\s+")


def pairwise_key(a: str, b: str) -> tuple[str, str]:
    """Surikiuota pora, kad (A,B) ir (B,A) būtų tas pats raktas."""
    return (a, b) if a <= b else (b, a)


def normalize_title(title: str) -> str:
    """Sunormina pavadinimą dublikatų paieškai.

    Žingsniai būtent šia eilės tvarka (specifikacijos 7 skyrius):

    1. casefold (ne lower — korektiškiau su ne ASCII raidėmis).
    2. Išmesti skliaustų ir laužtinių skliaustų turinį su pačiais skliaustais.
    3. Nukirpti viską nuo bendraautorystės žymės iki eilutės galo, o ne tik
       pačią žymę. Tai būtina: nukirpus tik žymę, „Nightfield feat. Mara Vale"
       normalizuotųsi į „nightfield mara vale" ir dublikatas nebūtų pastebėtas.
    4. Išmesti versijos žymes kaip atskirus žodžius.
    5. Pašalinti visus simbolius, išskyrus raides, skaičius ir tarpus.
    6. Suspausti tarpus į vieną ir nukirpti kraštus.

    „Night Field" -> „night field" NĖRA tas pats kaip „nightfield":
    tarpas yra reikšmingas.
    """
    text = title.casefold()
    text = _BRACKETS.sub(" ", text)
    text = _FEATURING.sub(" ", text)
    for marker in _VERSION_MARKERS:
        text = re.sub(rf"\b{marker}\b", " ", text)
    text = _NON_WORD.sub(" ", text)
    return _SPACES.sub(" ", text).strip()


def remove_duplicates(
    scored: Sequence[ScoredTrack],
    pairwise: Mapping[tuple[str, str], float],
) -> tuple[list[ScoredTrack], int]:
    """Pašalina dublikatus, paliekant aukštesnį balą turinčią dainą.

    Kandidatas atmetamas, jei bent vienas jau paliktas kandidatas tenkina ARBA
    normalize_title sutapimą, ARBA pairwise > DUPLICATE_COSINE. Nėra poros
    pairwise žodyne — ta sąlyga tiesiog netenkinama (ne klaida).

    Palyginimas su riba yra GRIEŽTAS (>), ne >=. Tai svarbu: dokumento
    pavyzdyje cos(K1,K4) = 0,95, o riba 0,98, tad K4 privalo išlikti.
    """
    kept: list[ScoredTrack] = []
    kept_titles: set[str] = set()
    removed = 0

    for candidate in scored:
        title = normalize_title(candidate.track.title)
        is_duplicate = title in kept_titles
        if not is_duplicate:
            for already in kept:
                key = pairwise_key(candidate.track.song_id, already.track.song_id)
                similarity = pairwise.get(key)
                if similarity is not None and similarity > DUPLICATE_COSINE:
                    is_duplicate = True
                    break
        if is_duplicate:
            removed += 1
        else:
            kept.append(candidate)
            kept_titles.add(title)

    return kept, removed


def apply_artist_limit(
    scored: Sequence[ScoredTrack],
    query_artist: str,
    per_artist: int = DEFAULT_ARTIST_LIMIT,
) -> tuple[list[ScoredTrack], int]:
    """Pritaiko atlikėjo limitą.

    Užklausos atlikėjas išmetamas VISADA, nepriklausomai nuo per_artist:
    naudotojas ieško ne to paties atlikėjo. Iš kitų atlikėjų paliekamos
    per_artist aukščiausio balo dainos — sąrašas jau surikiuotas, todėl
    pakanka skaičiuoti, kiek kurio atlikėjo jau palikta.

    Atlikėjai lyginami per casefold().strip(), kad „Kepler Grove" ir
    „kepler grove" būtų tas pats.
    """
    query_key = query_artist.casefold().strip()
    seen: dict[str, int] = {}
    kept: list[ScoredTrack] = []
    removed = 0

    for candidate in scored:
        artist = candidate.track.artist.casefold().strip()
        if artist == query_key or seen.get(artist, 0) >= per_artist:
            removed += 1
            continue
        seen[artist] = seen.get(artist, 0) + 1
        kept.append(candidate)

    return kept, removed


def select_diverse(
    scored: Sequence[ScoredTrack],
    pairwise: Mapping[tuple[str, str], float],
    limit: int,
) -> list[ScoredTrack]:
    """Atrenka iki limit dainų, atsižvelgiant į įvairovę (MMR).

    Pirmas elementas — didžiausio balo. Toliau kiekvienam likusiam
    skaičiuojama pataisyta vertė:

        MMR_RELEVANCE*balas - MMR_PENALTY*max(pairwise su jau atrinktomis)

    ir imamas didžiausias. Nėra poros žodyne — ta pora į maksimumą
    neįtraukiama; nėra nė vienos — bauda yra 0.

    Be šio žingsnio dešimtuke atsirastų dešimt beveik vienodų dainų, nes
    arčiausios užklausai dainos paprastai artimos ir viena kitai.

    Lygios vertės laužiamos pagal song_id, kad eilė būtų determinuota ir du
    paleidimai duotų tą patį rezultatą.
    """
    remaining = list(scored)
    selected: list[ScoredTrack] = []

    while remaining and len(selected) < limit:
        if not selected:
            best = min(remaining, key=lambda c: (-c.total_score, c.track.song_id))
        else:
            best = min(
                remaining,
                key=lambda c: (-_adjusted_score(c, selected, pairwise), c.track.song_id),
            )
        selected.append(best)
        remaining.remove(best)

    return selected


def _adjusted_score(
    candidate: ScoredTrack,
    selected: Sequence[ScoredTrack],
    pairwise: Mapping[tuple[str, str], float],
) -> float:
    """Įvairovės pataisyta vertė vienam kandidatui."""
    similarities = [
        pairwise[key]
        for already in selected
        if (key := pairwise_key(candidate.track.song_id, already.track.song_id))
        in pairwise
    ]
    penalty = max(similarities, default=0.0)
    return MMR_RELEVANCE * candidate.total_score - MMR_PENALTY * penalty
