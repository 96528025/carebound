from __future__ import annotations

from dataclasses import dataclass
import re

from app.data import MEMBERS, Member


PUBLIC_SCOPES = ["household_chen_shared", "drug_reference_public"]


@dataclass(frozen=True)
class PolicyDecision:
    intent: str
    query_scopes: list[str]
    blocked_scopes: list[str]
    reason: str
    enforcement_point: str = "before_vector_retrieval"

    @property
    def blocked_scope(self) -> str | None:
        return self.blocked_scopes[0] if self.blocked_scopes else None


def get_member(user_id: str) -> Member:
    return MEMBERS.get(user_id, MEMBERS["alice"])


def allowed_scopes(user_id: str) -> list[str]:
    member = get_member(user_id)
    scopes = ["household_chen_shared", "drug_reference_public", member.medical_scope]
    if member.is_guardian:
        scopes.append("member_eva_medical")
    return list(dict.fromkeys(scopes))


def blocked_scopes(user_id: str) -> list[str]:
    allowed = set(allowed_scopes(user_id))
    return [
        f"member_{member_id}_medical"
        for member_id in MEMBERS
        if f"member_{member_id}_medical" not in allowed
    ]


def requested_private_scope(message: str) -> str | None:
    text = message.lower()
    for member_id, member in MEMBERS.items():
        first = member.name.split()[0].lower()
        if re.search(rf"\b({member_id}|{first})\b", text):
            return member.medical_scope
    if re.search(r"\b(my|me|i|myself)\b", text):
        return "self"
    return None


def looks_medical_private(message: str) -> bool:
    text = message.lower()
    keywords = [
        "medication",
        "medicine",
        "taking",
        "allergy",
        "allergic",
        "medical",
        "record",
        "notes",
        "appointment",
        "inhaler",
        "before soccer",
        "surgery",
    ]
    return any(word in text for word in keywords)


def looks_household(message: str) -> bool:
    text = message.lower()
    return any(word in text for word in ["address", "billing", "insurance", "household", "home"])


def looks_prompt_injection(message: str) -> bool:
    text = message.lower()
    return any(
        phrase in text
        for phrase in [
            "ignore privacy",
            "ignore the privacy",
            "ignore previous",
            "bypass",
            "override",
            "break policy",
        ]
    )


def looks_household_aggregation(message: str) -> bool:
    text = message.lower()
    aggregation_terms = ["who in", "anyone", "everyone", "family", "household", "which member", "does anyone"]
    medical_terms = ["uses", "takes", "taking", "medication", "medicine", "allergy", "allergic", "appointment"]
    return any(term in text for term in aggregation_terms) and any(term in text for term in medical_terms)


def looks_mixed_shared_private(message: str) -> bool:
    return looks_household(message) and looks_medical_private(message)


def looks_drug_reference(message: str) -> bool:
    text = message.lower()
    reference_phrases = ["what is", "used for", "tell me about", "define"]
    return mentions_drug(message) and any(phrase in text for phrase in reference_phrases)


def mentions_drug(message: str) -> bool:
    text = message.lower()
    drug_terms = ["albuterol", "lisinopril", "metformin", "cetirizine", "amoxicillin"]
    return any(term in text for term in drug_terms)


def resolve_policy(user_id: str, message: str) -> PolicyDecision:
    allowed = allowed_scopes(user_id)
    requested = requested_private_scope(message)
    blocked = blocked_scopes(user_id)
    if looks_prompt_injection(message) and requested not in {None, "self"} and requested not in allowed:
        return PolicyDecision(
            "prompt_injection_private_memory_attack",
            [],
            [requested],
            "Prompt instructions cannot override identity-scoped memory policy.",
        )
    if requested and requested != "self" and requested not in allowed:
        return PolicyDecision("blocked_private_member_memory", [], [requested], "Requested member scope is outside the current identity.")
    if requested and requested != "self":
        query_scopes = [requested]
        if looks_mixed_shared_private(message):
            query_scopes = ["household_chen_shared", requested]
        return PolicyDecision("authorized_private_member_memory", query_scopes, [], "Requested member scope is allowed for this identity.")
    if looks_household_aggregation(message):
        query_scopes = ["drug_reference_public"] if mentions_drug(message) else []
        return PolicyDecision(
            "household_medical_aggregation",
            query_scopes,
            blocked,
            "Family-wide medical aggregation would require reading private member collections.",
        )
    if requested == "self":
        return PolicyDecision("own_private_memory", [get_member(user_id).medical_scope], [], "Current user owns this memory scope.")
    if looks_drug_reference(message):
        return PolicyDecision("public_drug_reference", ["drug_reference_public"], [], "General medication facts are not personal medical memory.")
    if looks_household(message):
        return PolicyDecision("shared_household_context", ["household_chen_shared"], [], "Household logistics are shared across the account.")
    if looks_medical_private(message):
        return PolicyDecision("own_private_memory", [get_member(user_id).medical_scope], [], "Medical query defaults to the current user's private memory.")
    return PolicyDecision("general_allowed_memory", allowed, [], "No private target detected, so only allowed scopes are searched.")


def resolve_query_scopes(user_id: str, message: str) -> tuple[list[str], str | None]:
    decision = resolve_policy(user_id, message)
    return decision.query_scopes, decision.blocked_scope


def can_write_scope(user_id: str, scope: str) -> bool:
    return scope in allowed_scopes(user_id) and scope.startswith("member_")
