"""Rule engine — pure function from structured state to (call, trace).

Implements the FIE technical rules for priority as a deterministic,
unit-tested decision procedure. Each branch cites the relevant article.
See PRD §8.2.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from a1.rules.taxonomy import Call


@dataclass(frozen=True)
class FencerState:
    """Structured state for one fencer in a phrase."""

    has_attack: bool = False
    attack_confidence: float = 1.0


@dataclass(frozen=True)
class StructuredState:
    """Structured state of a phrase for the rule engine."""

    left: FencerState = field(default_factory=FencerState)
    right: FencerState = field(default_factory=FencerState)


@dataclass(frozen=True)
class RuleTrace:
    """Trace of the rule engine's decision procedure."""

    steps: list[str] = field(default_factory=list)
    article: str | None = None


def swap_fencers(state: StructuredState) -> StructuredState:
    """Swap left and right fencers in a structured state."""
    return StructuredState(left=state.right, right=state.left)


def swap_call(call: Call) -> Call:
    """Swap a call's fencer assignment."""
    if call == Call.LEFT:
        return Call.RIGHT
    if call == Call.RIGHT:
        return Call.LEFT
    return Call.NONE


def decide(state: StructuredState) -> tuple[Call, RuleTrace]:
    """Apply priority rules to a structured state.

    Current implementation: one rule — established attack grants priority.
    If exactly one fencer has an established attack, that fencer gets
    priority. Otherwise NONE.

    This is a genuine rule under both foil (FIE t.56) and sabre (FIE t.75)
    priority and will not need rewriting when the full engine is built.

    Returns:
        A (Call, RuleTrace) tuple.
    """
    left_attacks = state.left.has_attack
    right_attacks = state.right.has_attack

    if left_attacks and not right_attacks:
        return Call.LEFT, RuleTrace(
            steps=["Left has established attack, right does not -> priority LEFT"],
            article="FIE t.56",
        )

    if right_attacks and not left_attacks:
        return Call.RIGHT, RuleTrace(
            steps=["Right has established attack, left does not -> priority RIGHT"],
            article="FIE t.56",
        )

    if left_attacks and right_attacks:
        return Call.NONE, RuleTrace(
            steps=["Both fencers have established attacks -> cannot determine priority"],
            article=None,
        )

    return Call.NONE, RuleTrace(
        steps=["Neither fencer has an established attack -> no priority"],
        article=None,
    )
