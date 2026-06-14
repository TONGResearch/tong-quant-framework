import gzip
import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path
from typing import Any

import pandas as pd

from tong_quant.data.models import RawDataset


@dataclass(frozen=True, slots=True)
class CacheEntry:
    dataset: RawDataset
    hit: bool


class DataFrameCache:
    def __init__(
        self,
        root: Path,
        ttl: timedelta,
        *,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._root = root
        self._ttl = ttl
        self._clock = clock or (lambda: datetime.now(UTC))

    def key(self, dataset: str, parameters: dict[str, Any]) -> str:
        payload = json.dumps(
            {"dataset": dataset, "parameters": parameters},
            sort_keys=True,
            separators=(",", ":"),
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def get(self, dataset: str, parameters: dict[str, Any]) -> RawDataset | None:
        path = self._path(self.key(dataset, parameters))
        if not path.exists():
            return None
        with gzip.open(path, "rt", encoding="utf-8") as cache_file:
            payload = json.load(cache_file)
        retrieved_at = datetime.fromisoformat(payload["retrieved_at"])
        if self._clock() - retrieved_at > self._ttl:
            return None
        frame = pd.read_json(StringIO(payload["frame"]), orient="table")
        return RawDataset(
            dataset=dataset,
            frame=frame,
            retrieved_at=retrieved_at,
            source=payload["source"],
            parameters=payload["parameters"],
        )

    def put(self, dataset: RawDataset) -> None:
        self._root.mkdir(parents=True, exist_ok=True)
        path = self._path(self.key(dataset.dataset, dataset.parameters))
        payload = {
            "retrieved_at": dataset.retrieved_at.isoformat(),
            "source": dataset.source,
            "parameters": dataset.parameters,
            "frame": dataset.frame.to_json(orient="table", date_format="iso"),
        }
        with gzip.open(path, "wt", encoding="utf-8") as cache_file:
            json.dump(payload, cache_file, ensure_ascii=True, separators=(",", ":"))

    def _path(self, key: str) -> Path:
        return self._root / f"{key}.json.gz"
