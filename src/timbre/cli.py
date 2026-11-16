"""Komandinės eilutės sąsaja. Specifikacijos 10 skyrius.

Čia yra tik `argparse` ir spausdinimas — jokios skaičiavimo logikos. Taip pat
čia ir TIK čia žinomos konkrečios realizacijos: `JsonCatalogRepository` ir
`DEFAULT_STRATEGIES` sujungiami ir paduodami `SearchService` per konstruktorių.
Norint pakeisti katalogą duomenų baze, keičiama viena eilutė šiame faile.

Išėjimo kodai: 0 pavyko · 1 TimbreError arba katalogo failo klaida ·
2 argumentų klaida (argparse).
"""

import argparse
import json
import sys
from collections.abc import Sequence

from .adapters.json_catalog import JsonCatalogRepository
from .app.search_service import SearchService
from .domain.constants import DEFAULT_ARTIST_LIMIT, DEFAULT_LIMIT, DEFAULT_WEIGHTS
from .domain.errors import ErrorCode, TimbreError
from .domain.models import FilterSpec, SearchResult

# Filtrų vardai naudotojui. Vidiniai vardai (`bpm`, `instrumental`) yra
# duomenų struktūros raktai, o čia — tik išvestis, todėl vertimas gyvena
# sąsajos sluoksnyje.
FILTER_NAMES = {"bpm": "tempas", "instrumental": "instrumentinės"}


def _use_utf8_output() -> None:
    """Perjungia išvestį į UTF-8.

    Be šito Windows konsolėje (cp1252/cp1257) `print("instrumentinė")` kelia
    UnicodeEncodeError ir nukristų būtent klaidų demonstracija. Patikrinta
    šioje mašinoje — tai ne teorinė rizika.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr]
        except (AttributeError, OSError):
            pass


def parse_weights(text: str) -> dict[str, float]:
    """`"vector=0.7,tempo=0.1"` -> `{"vector": 0.7, "tempo": 0.1}`.

    Svoriai perduodami vardiniu registru, ne pozicijomis, kad kriterijų
    skaičius nebūtų įkaltas sąsajoje: šeštas kriterijus reiškia vieną naują
    klasę ir vieną įrašą registre, o CLI nesikeičia.
    """
    weights: dict[str, float] = {}
    for part in text.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" not in part:
            raise TimbreError(
                ErrorCode.NETINKAMAS_SVORIS,
                f"netinkamas svorio įrašas {part!r}; formatas: vardas=skaičius",
            )
        name, _, value = part.partition("=")
        try:
            weights[name.strip()] = float(value.strip())
        except ValueError:
            raise TimbreError(
                ErrorCode.NETINKAMAS_SVORIS,
                f"svoris {name.strip()!r} nėra skaičius: {value.strip()!r}",
            ) from None
    if not weights:
        raise TimbreError(
            ErrorCode.NETINKAMAS_SVORIS, "svorių sąrašas tuščias"
        )
    return weights


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m timbre",
        description="Timbre — panašiai skambančių dainų paieška pagal dainos garsą.",
    )
    # Dainą galima nurodyti DVIEM būdais, ir tai atitinka dvi produkto eigas:
    # prisijungęs žmogus žino savo įkeltos dainos id, o atėjęs su nuoroda
    # težino pavadinimą ir atlikėją. Grupė yra `required`, tad vieną iš dviejų
    # nurodyti privaloma, o abu kartu argparse atmeta pats.
    kas = parser.add_mutually_exclusive_group(required=True)
    kas.add_argument("--song-id", help="užklausos dainos id")
    kas.add_argument("--title", help="užklausos dainos pavadinimas")
    parser.add_argument("--artist", default=None,
                        help="atlikėjas, tikslinantis --title")
    parser.add_argument("--tenant", required=True,
                        help="kliento id, pvz. t-77; bendras katalogas — bendras")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help=f"rezultatų kiekis (numatyta {DEFAULT_LIMIT})")
    parser.add_argument("--artist-limit", type=int, default=DEFAULT_ARTIST_LIMIT,
                        help=f"dainų iš to paties atlikėjo (numatyta {DEFAULT_ARTIST_LIMIT})")
    parser.add_argument("--bpm-min", type=float, default=None, help="tempo filtro apatinė riba")
    parser.add_argument("--bpm-max", type=float, default=None, help="tempo filtro viršutinė riba")
    parser.add_argument("--instrumental-only", action="store_true",
                        help="tik instrumentinės dainos")
    parser.add_argument("--weights", default=None,
                        help="svoriai vardais, pvz. vector=0.7,tempo=0.1")
    parser.add_argument("--catalog", default=None,
                        help="katalogo failas (numatyta data/catalog.json)")
    parser.add_argument("--json", action="store_true",
                        help="išvestis I etapo dokumento JSON forma")
    parser.add_argument("--remove", action="store_true",
                        help="pašalinti savo įkeltą dainą (bendro katalogo – negalima)")
    return parser


def format_table(result: SearchResult) -> str:
    """Žmogui skaitoma lentelė."""
    lines = [
        f"{'#':>2}  {'Daina':24s} {'Atlikėjas':18s} {'Balas':>6s} {'BPM':>6s} {'Ton.':>5s}  Kodėl",
        "-" * 110,
    ]
    for position, item in enumerate(result.items, start=1):
        features = item.track.features
        lines.append(
            f"{position:>2}. {item.track.title[:24]:24s} "
            f"{item.track.artist[:18]:18s} "
            f"{item.final_score:6.3f} "
            f"{features.bpm:6.1f} "
            f"{(features.key or '-'):>5s}  "
            f"{'; '.join(item.explanations)}"
        )
    if not result.items:
        lines.append("    (nė vienos dainos neatitiko užklausos)")

    if result.dalinis_rezultatas:
        restricting = result.labiausiai_ribojes_filtras
        if restricting is not None:
            name = FILTER_NAMES.get(restricting, restricting)
            lines.append(
                f"\nRezultatų mažiau nei prašyta; labiausiai apribojo filtras: {name}"
            )
        else:
            lines.append(
                "\nRezultatų mažiau nei prašyta; filtrai nieko neatmetė "
                "(apribojo dublikatų šalinimas arba atlikėjo limitas)"
            )
    # Trečiasis skaičius NĖRA „įvairovė atmetė": įvairovės žingsnis rikiuoja,
    # o ne šalina. Tai dainos, kurios liko už prašyto kiekio ribos. Duomenų
    # rakto (`diversity`) nekeičiame — jis yra kontrakto dalis, o keičiamas
    # tik naudotojui matomas tekstas.
    lines.append(
        f"\nPašalinta: dublikatų {result.removal_counts.get('duplicates', 0)}, "
        f"pagal atlikėjo limitą {result.removal_counts.get('artist_limit', 0)}; "
        f"neįtilpo į prašytą kiekį {result.removal_counts.get('diversity', 0)}"
    )
    return "\n".join(lines)


def format_json(result: SearchResult) -> str:
    """Tiksliai I etapo dokumento išvesties forma."""
    payload = {
        "rezultatai": [
            {
                "daina": item.track.title,
                "atlikėjas": item.track.artist,
                "balas": round(item.final_score, 3),
                "tempas": item.track.features.bpm,
                "tonacija": item.track.features.key,
                "kodėl": item.explanations,
            }
            for item in result.items
        ],
        "dalinis_rezultatas": result.dalinis_rezultatas,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2)


def main(argv: Sequence[str] | None = None) -> int:
    _use_utf8_output()
    args = build_parser().parse_args(argv)

    try:
        weights = parse_weights(args.weights) if args.weights else dict(DEFAULT_WEIGHTS)
        repo = JsonCatalogRepository(args.catalog)
        service = SearchService(repo)

        if repo.skipped:
            print(
                f"Pastaba: {len(repo.skipped)} daina(-os) neindeksuota dėl netinkamų "
                f"požymių: {', '.join(song_id for song_id, _ in repo.skipped)}",
                file=sys.stderr,
            )

        # Pavadinimas paverčiamas į song_id PRIEŠ viską kitą: toliau visas
        # kodas dirba tik su id, tad dvi įvesties eigos susilieja į vieną.
        song_id = args.song_id
        if song_id is None:
            found = service.find_song(
                tenant_id=args.tenant, title=args.title, artist=args.artist
            )
            if len(found) > 1:
                print(
                    f"Pagal „{args.title}“ rasta {len(found)} dainos. "
                    f"Nurodyk vieną su --song-id:",
                    file=sys.stderr,
                )
                for track in found:
                    print(
                        f"  {track.song_id}  {track.title} — {track.artist}",
                        file=sys.stderr,
                    )
                return 1
            song_id = found[0].song_id

        if args.remove:
            service.remove(tenant_id=args.tenant, song_id=song_id)
            print(f"Daina {song_id} pašalinta iš kliento {args.tenant} katalogo.")
            return 0

        result = service.search(
            tenant_id=args.tenant,
            song_id=song_id,
            filters=FilterSpec(
                bpm_min=args.bpm_min,
                bpm_max=args.bpm_max,
                instrumental_only=args.instrumental_only,
            ),
            weights=weights,
            limit=args.limit,
            artist_limit=args.artist_limit,
        )
    except TimbreError as error:
        print(f"[{error.code.value}] {error.message}", file=sys.stderr)
        return 1
    except OSError as error:
        print(f"[KATALOGO_KLAIDA] {error}", file=sys.stderr)
        return 1

    print(format_json(result) if args.json else format_table(result))
    return 0
