"""Action taxonomy and core enums for the rule engine.

Foil actions start from FERA's 12 classes (for direct comparison) and extend
with priority-relevant actions per PRD §8.1. Sabre has a separate taxonomy.
"""

from __future__ import annotations

from enum import IntEnum, StrEnum


class Weapon(StrEnum):
    """Fencing weapon."""

    FOIL = "foil"
    SABRE = "sabre"
    EPEE = "epee"


class Call(StrEnum):
    """Priority call — who gets the point on a double touch."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"
    NONE = "NONE"


class Fencer(StrEnum):
    """Fencer position on the strip."""

    LEFT = "LEFT"
    RIGHT = "RIGHT"


class LabelTier(IntEnum):
    """Labeling tier per PRD §9.2."""

    T0 = 0
    T1 = 1
    T2 = 2
    T3 = 3


class LabelPath(StrEnum):
    """Supervision path that produced the label. PRD §7.3."""

    A = "A"
    B = "B"


class FoilAction(StrEnum):
    """Foil action taxonomy — FERA's 12 classes + A1 extensions."""

    # FERA's 12
    STEP_FORWARD = "step_forward"
    STEP_BACKWARD = "step_backward"
    HALF_STEP_FORWARD = "half_step_forward"
    HALF_STEP_BACKWARD = "half_step_backward"
    LUNGE = "lunge"
    FLECHE = "fleche"
    WAIT = "wait"
    PARRY = "parry"
    BEAT = "beat"
    COUNTERATTACK = "counterattack"
    FAKE = "fake"
    HIT = "hit"
    # A1 extensions — each justified by its role in a priority decision
    REMISE = "remise"
    REDOUBLEMENT = "redoublement"
    REPRISE = "reprise"
    RIPOSTE_IMMEDIATE = "riposte_immediate"
    RIPOSTE_DELAYED = "riposte_delayed"
    COUNTER_PARRY = "counter_parry"
    POINT_IN_LINE_ESTABLISHED = "point_in_line_established"
    POINT_IN_LINE_BROKEN = "point_in_line_broken"
    DEROBEMENT = "derobement"
    STOP_HIT_IN_TEMPO = "stop_hit_in_tempo"
    ABSENCE_OF_BLADE = "absence_of_blade"


class SabreAction(StrEnum):
    """Sabre action taxonomy — overlapping with foil but not identical."""

    STEP_FORWARD = "step_forward"
    STEP_BACKWARD = "step_backward"
    HALF_STEP_FORWARD = "half_step_forward"
    HALF_STEP_BACKWARD = "half_step_backward"
    LUNGE = "lunge"
    FLECHE = "fleche"
    WAIT = "wait"
    PARRY = "parry"
    BEAT = "beat"
    COUNTERATTACK = "counterattack"
    FAKE = "fake"
    HIT = "hit"
    REMISE = "remise"
    REDOUBLEMENT = "redoublement"
    REPRISE = "reprise"
    RIPOSTE_IMMEDIATE = "riposte_immediate"
    RIPOSTE_DELAYED = "riposte_delayed"
    COUNTER_PARRY = "counter_parry"
    POINT_IN_LINE_ESTABLISHED = "point_in_line_established"
    POINT_IN_LINE_BROKEN = "point_in_line_broken"
    STOP_HIT_IN_TEMPO = "stop_hit_in_tempo"
    ABSENCE_OF_BLADE = "absence_of_blade"
    PREPARATION = "preparation"
    ATTACK_IN_PREPARATION = "attack_in_preparation"


class BladeLine(StrEnum):
    """Blade line — foil only."""

    FOUR = "4"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    OTHER = "other"


class CallConfidence(StrEnum):
    """Annotator confidence in a call."""

    HIGH = "high"
    MED = "med"
    LOW = "low"


class BladeMethod(StrEnum):
    """Method used for blade detection."""

    LEARNED = "learned"
    STREAK = "streak"
    LSD = "lsd"
    TRACK = "track"
    NONE = "none"


class ContactType(StrEnum):
    """Type of blade/body contact event.

    PRD amendment: these values are proposed, not yet in the PRD.
    """

    BLADE_BLADE = "blade_blade"
    BLADE_TARGET = "blade_target"
    BLADE_GUARD = "blade_guard"
    BLADE_PISTE = "blade_piste"
    UNKNOWN = "unknown"


class PredictionArm(StrEnum):
    """Model prediction arm."""

    DIRECT = "direct"
    RULE_GROUNDED = "rule_grounded"


class ErrorCategory(StrEnum):
    """Pre-declared failure taxonomy categories per PRD §10.5."""

    SIMULTANEOUS_INITIATION = "simultaneous_initiation"
    REMISE_VS_RIPOSTE = "remise_vs_riposte"
    COUNTERATTACK_VS_STOP_HIT = "counterattack_vs_stop_hit"
    PARRY_AMBIGUITY = "parry_ambiguity"
    POINT_IN_LINE = "point_in_line"
    ATTACK_LOSING_TEMPO = "attack_losing_tempo"
    OCCLUSION = "occlusion"
    CAMERA_ANGLE_DEGENERACY = "camera_angle_degeneracy"
    MOTION_BLUR = "motion_blur"
    APPARATUS_LABEL_ERROR = "apparatus_label_error"
    RULE_GENUINELY_AMBIGUOUS = "rule_genuinely_ambiguous"
