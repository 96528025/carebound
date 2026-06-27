from __future__ import annotations

import os

from app.data import HOUSEHOLD_ID, MEMBERS
from app.scalekit_agentkit import configured as scalekit_configured


def identity_mode() -> str:
    has_scalekit = scalekit_configured()
    demo_forced = os.getenv("DEMO_IDENTITY_MODE", "true").lower() == "true"
    if has_scalekit and not demo_forced:
        return "live Scalekit adapter"
    if has_scalekit:
        return "demo identity mode with Scalekit credentials available"
    return "demo identity mode"


def resolve_user(user_id: str | None) -> dict:
    member_id = user_id if user_id in MEMBERS else "alice"
    member = MEMBERS[member_id]
    return {
        "id": member.id,
        "name": member.name,
        "role": member.role,
        "relationship": member.relationship,
        "age": member.age,
        "is_guardian": member.is_guardian,
        "is_minor": member.is_minor,
        "household_id": HOUSEHOLD_ID,
        "identity_mode": identity_mode(),
        "scalekit_identifier": member.id,
        "scalekit_configured": scalekit_configured(),
    }
