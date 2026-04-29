"""Common types for risk gate rules."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class RuleResult:
    """Result of a single risk gate rule check."""

    rule_id: str
    rule_name: str
    passed: bool
    value: Any
    threshold: Any
    reason: str = ""
