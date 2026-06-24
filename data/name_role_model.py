# -*- coding: utf-8 -*-
"""Frozen surname-vs-given token role probabilities."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple


MODEL_PATH = Path(__file__).with_name("name_role_counts.json")


@lru_cache(maxsize=1)
def _counts() -> dict[str, list[int]]:
    payload = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    return payload["counts"]


def get_token_role(token: str) -> Optional[Tuple[float, int]]:
    """Return smoothed surname log-odds and observed support."""
    values = _counts().get(token.lower())
    if not values:
        return None
    surname_count, given_count = values
    return math.log((surname_count + 1.0) / (given_count + 1.0)), surname_count + given_count
