"""The typed output contract for the triage agent — the one fixed boundary.

`TriageDecision` is what the improved arm is forced to emit and what every scorer
reads. The baseline arm is free to emit anything; the harness attempts to parse
its output into this same shape, and a parse failure is itself a measured signal
(schema non-compliance), not an error to paper over.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Action(str, Enum):
    """The finite, closed set of operational next steps the agent may choose.

    A closed set is the point: a governed agent cannot invent an action outside
    what the clinic has sanctioned. Anything the model returns outside this set
    is a containment failure, caught deterministically.
    """

    schedule_appointment = "schedule_appointment"
    send_self_care_info = "send_self_care_info"
    request_more_info = "request_more_info"
    escalate_to_nurse = "escalate_to_nurse"
    escalate_emergency = "escalate_emergency"
    billing_handoff = "billing_handoff"
    human_handoff = "human_handoff"
    no_action = "no_action"


class EscalationTier(str, Enum):
    """Clinical urgency. The safety-critical axis — scored deterministically."""

    none = "none"
    routine = "routine"
    urgent = "urgent"
    emergency = "emergency"


_TIER_RANK: dict[EscalationTier, int] = {
    EscalationTier.none: 0,
    EscalationTier.routine: 1,
    EscalationTier.urgent: 2,
    EscalationTier.emergency: 3,
}


def tier_rank(tier: EscalationTier) -> int:
    """Ordinal rank so under/over-escalation is a simple comparison."""
    return _TIER_RANK[tier]


class TriageDecision(BaseModel):
    """Strict typed decision. The improved arm validates against this; failures
    to validate are the schema-compliance metric, not exceptions to swallow."""

    # Surplus keys are ignored, not rejected: schema-compliance measures whether
    # the required typed fields and valid enum values are present, so the baseline
    # is not penalised for adding a harmless extra field. This biases the delta
    # toward conservative (against the improved arm), which is the honest direction.
    model_config = {"extra": "ignore"}

    action: Action
    escalation_tier: EscalationTier
    patient_message: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    evidence_used: list[str] = Field(default_factory=list)
