# -*- coding: utf-8 -*-
"""Frozen surname-vs-given token role probabilities."""

from __future__ import annotations

import json
import math
from functools import lru_cache
from pathlib import Path
from typing import Optional, Tuple


MODEL_PATH = Path(__file__).with_name("name_role_counts.json")
JMNEDICT_MODEL_PATH = Path(__file__).with_name("jmnedict_role_counts.json")
SSA_CENSUS_MODEL_PATH = Path(__file__).with_name("ssa_census_role_counts.json")


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


@lru_cache(maxsize=1)
def _jmnedict_counts() -> dict[str, list[int]]:
    payload = json.loads(JMNEDICT_MODEL_PATH.read_text(encoding="utf-8"))
    return payload["counts"]


def get_jmnedict_role(token: str) -> Optional[Tuple[float, int]]:
    """Return JMnedict surname/given log-odds and entry support."""
    values = _jmnedict_counts().get(token.lower())
    if not values:
        return None
    surname_count, given_count = values
    return math.log((surname_count + 1.0) / (given_count + 1.0)), surname_count + given_count


@lru_cache(maxsize=1)
def _ssa_census_payload() -> dict:
    return json.loads(SSA_CENSUS_MODEL_PATH.read_text(encoding="utf-8"))


def get_ssa_census_role(token: str) -> Optional[Tuple[float, int]]:
    """Return normalized US surname-vs-given log-odds and support."""
    payload = _ssa_census_payload()
    values = payload["counts"].get(token.lower())
    if not values:
        return None
    surname_count, given_count = values
    totals = payload["totals"]
    vocabulary = totals["vocabulary"]
    surname_probability = (surname_count + 1.0) / (totals["surname"] + vocabulary)
    given_probability = (given_count + 1.0) / (totals["given"] + vocabulary)
    return math.log(surname_probability / given_probability), surname_count + given_count
