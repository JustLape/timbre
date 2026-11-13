"""Katalogas iš JSON failo. Specifikacijos 3 ir 5 skyriai.

Failas nuskaitomas VIENĄ kartą konstruktoriuje ir toliau laikomas atmintyje.
Užklausų logikos šis adapteris nedubliuoja — jis naudoja `InMemoryCatalog`, o
pats atsako tik už failą: nuskaitymą, patikrą ir įrašymą.

Duomenų bazės čia sąmoningai nėra. II etape katalogas yra tekstinis JSON
failas, kurį dėstytojas gali atsidaryti ir pamatyti savo akimis; PostgreSQL su
pgvector numatytas III etapui ir atsiras kaip dar viena šios pačios sąsajos
realizacija, nekeičiant pagrindinio modulio.
"""

import json
import os
from pathlib import Path

from ..domain.models import CandidatePool, Features, FilterSpec, Track
from .in_memory import InMemoryCatalog

# Projekto šaknis: .../src/timbre/adapters/json_catalog.py -> parents[3]
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CATALOG_PATH = PROJECT_ROOT / "data" / "catalog.json"


class JsonCatalogRepository:
    """Katalogas, skaitomas iš `data/catalog.json`."""

    def __init__(self, path: str | os.PathLike[str] | None = None) -> None:
        self.path = Path(path) if path is not None else DEFAULT_CATALOG_PATH
        if not self.path.is_file():
            raise FileNotFoundError(
                f"katalogo failas nerastas: {self.path}. "
                f"Sugeneruokite jį komanda: python scripts/seed_catalog.py"
            )

        with self.path.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)

        self.feature_set: str = raw.get("feature_set", "synthetic-v1")
        self.generated_with_seed = raw.get("generated_with_seed")

        tracks: list[Track] = []
        skipped: list[tuple[str, str]] = []
        for entry in raw.get("tracks", []):
            song_id = str(entry.get("song_id", "?"))
            try:
                tracks.append(self._build_track(entry))
            except (ValueError, TypeError, KeyError) as error:
                # Patvirtinto dokumento 3 skyriaus "atsakymo tikrinimas":
                # netinkamų požymių daina NEINDEKSUOJAMA ir pažymima su
                # priežastimi, o ne verčia visą katalogą nebeįsikelti.
                skipped.append((song_id, str(error)))

        self.skipped: list[tuple[str, str]] = skipped
        self._catalog = InMemoryCatalog(tracks)

    def _build_track(self, entry: dict) -> Track:
        features_raw = entry["features"]
        features = Features(
            vector=tuple(float(x) for x in features_raw["vector"]),
            bpm=float(features_raw["bpm"]),
            key=str(features_raw.get("key", "")),
            key_confidence=float(features_raw.get("key_confidence", 0.0)),
            loudness_lufs=float(features_raw["loudness_lufs"]),
            moods={str(k): float(v) for k, v in features_raw.get("moods", {}).items()},
            feature_set=self.feature_set,
        )
        return Track(
            song_id=str(entry["song_id"]),
            tenant_id=str(entry["tenant_id"]),
            title=str(entry["title"]),
            artist=str(entry["artist"]),
            features=features,
        )

    # --- CatalogRepository sąsaja: skaitymas deleguojamas atminties katalogui ---

    def get_track(self, tenant_id: str, song_id: str) -> Track | None:
        return self._catalog.get_track(tenant_id, song_id)

    def fetch_candidates(
        self,
        tenant_id: str,
        query: Track,
        filters: FilterSpec,
        pool_size: int,
    ) -> CandidatePool:
        return self._catalog.fetch_candidates(tenant_id, query, filters, pool_size)

    def remove_track(self, tenant_id: str, song_id: str) -> bool:
        """Pašalina dainą ir, jei pavyko, įrašo katalogą atgal į failą."""
        removed = self._catalog.remove_track(tenant_id, song_id)
        if removed:
            self._save()
        return removed

    def _save(self) -> None:
        """Įrašo katalogą atgal per laikiną failą, kad jo nesugadintų."""
        payload = {
            "feature_set": self.feature_set,
            "generated_with_seed": self.generated_with_seed,
            "tracks": [
                {
                    "song_id": track.song_id,
                    "tenant_id": track.tenant_id,
                    "title": track.title,
                    "artist": track.artist,
                    "features": {
                        "vector": list(track.features.vector),
                        "bpm": track.features.bpm,
                        "key": track.features.key,
                        "key_confidence": track.features.key_confidence,
                        "loudness_lufs": track.features.loudness_lufs,
                        "moods": dict(track.features.moods),
                    },
                }
                for track in self._catalog.all_tracks()
            ],
        }
        temporary = self.path.with_suffix(".json.tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)
        temporary.replace(self.path)
