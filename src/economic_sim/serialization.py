import hashlib
import json
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from enum import Enum

import numpy as np
from pydantic import BaseModel


def canonical_value(value):
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ValueError("Decimal non finito")
        return format(value, ".6f")
    if isinstance(value, BaseModel):
        return canonical_value(value.model_dump())
    if is_dataclass(value):
        return canonical_value(asdict(value))
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, np.ndarray):
        return canonical_value(value.tolist())
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, dict):
        keys = [str(k) for k in value]
        if len(set(keys)) != len(keys):
            raise ValueError("Collisione delle chiavi JSON")
        return {str(k): canonical_value(v) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return [canonical_value(v) for v in value]
    return value


def canonical_json(value) -> str:
    return json.dumps(
        canonical_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def checksum(value) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
