"""
Intent value object.

Document 3 Section 21 (INTENT ENGINE): intent is what the LLM/NLU layer
PROPOSES, never what it decides to execute — the LLM != Authority
invariant applies here as much as anywhere. `confidence` exists so
downstream ambiguity handling (Section 22) has something concrete to
threshold on, rather than treating every intent as certain.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True, slots=True)
class Intent:
    intent_type: str
    confidence: float
    parameters: dict[str, str] = field(default_factory=dict)

    def is_confident(self, *, threshold: float = 0.7) -> bool:
        return self.confidence >= threshold
