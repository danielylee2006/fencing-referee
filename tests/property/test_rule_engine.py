"""Property tests for the rule engine.

The rule engine is a pure function — test it like one.
See PRD §8.2 and CLAUDE.md §10.
"""

from __future__ import annotations

from hypothesis import given
from hypothesis import strategies as st

from a1.rules.engine import (
    FencerState,
    StructuredState,
    decide,
    swap_call,
    swap_fencers,
)
from a1.rules.taxonomy import Call

fencer_states = st.builds(
    FencerState,
    has_attack=st.booleans(),
    attack_confidence=st.floats(min_value=0.0, max_value=1.0),
)

structured_states = st.builds(
    StructuredState,
    left=fencer_states,
    right=fencer_states,
)


class TestRuleEngineProperties:
    """Property-based tests for the rule engine."""

    @given(state=structured_states)
    def test_always_returns_valid_call(self, state: StructuredState) -> None:
        """The rule engine always returns a valid Call enum member."""
        call, _trace = decide(state)
        assert isinstance(call, Call)

    @given(state=structured_states)
    def test_swap_equivariance(self, state: StructuredState) -> None:
        """decide(swap(x)) == swap(decide(x)).

        This is a fundamental invariant: the model must not have a side bias.
        See PRD §10.6 swap-equivariance assertion.
        """
        call_original, _ = decide(state)
        call_swapped, _ = decide(swap_fencers(state))
        assert call_swapped == swap_call(call_original)

    @given(state=structured_states)
    def test_trace_is_nonempty(self, state: StructuredState) -> None:
        """Every decision produces at least one trace step."""
        _, trace = decide(state)
        assert len(trace.steps) > 0

    def test_single_attacker_left_gets_priority(self) -> None:
        """If only left attacks, left gets the call."""
        state = StructuredState(
            left=FencerState(has_attack=True),
            right=FencerState(has_attack=False),
        )
        call, trace = decide(state)
        assert call == Call.LEFT
        assert trace.article == "FIE t.56"

    def test_single_attacker_right_gets_priority(self) -> None:
        """If only right attacks, right gets the call."""
        state = StructuredState(
            left=FencerState(has_attack=False),
            right=FencerState(has_attack=True),
        )
        call, _trace = decide(state)
        assert call == Call.RIGHT

    def test_both_attack_no_priority(self) -> None:
        """If both attack, no priority can be determined."""
        state = StructuredState(
            left=FencerState(has_attack=True),
            right=FencerState(has_attack=True),
        )
        call, _ = decide(state)
        assert call == Call.NONE

    def test_neither_attacks_no_priority(self) -> None:
        """If neither attacks, no priority."""
        state = StructuredState(
            left=FencerState(has_attack=False),
            right=FencerState(has_attack=False),
        )
        call, _ = decide(state)
        assert call == Call.NONE
