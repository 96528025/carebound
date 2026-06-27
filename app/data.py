from __future__ import annotations

from dataclasses import dataclass


HOUSEHOLD_ID = "chen"
HOUSEHOLD_NAME = "Chen Household"


@dataclass(frozen=True)
class Member:
    id: str
    name: str
    relationship: str
    age: int
    role: str
    is_guardian: bool = False
    is_minor: bool = False

    @property
    def medical_scope(self) -> str:
        return f"member_{self.id}_medical"


MEMBERS: dict[str, Member] = {
    "alice": Member("alice", "Alice Chen", "mom", 50, "guardian", True),
    "bob": Member("bob", "Bob Chen", "dad", 50, "guardian", True),
    "chris": Member("chris", "Chris Chen", "son", 30, "adult"),
    "david": Member("david", "David Chen", "son", 20, "adult"),
    "eva": Member("eva", "Eva Chen", "daughter", 10, "minor", False, True),
}

SCOPES = {
    "drug_reference_public",
    "household_chen_shared",
    "member_alice_medical",
    "member_bob_medical",
    "member_chris_medical",
    "member_david_medical",
    "member_eva_medical",
}

SEED_MEMORY: dict[str, list[str]] = {
    "drug_reference_public": [
        "Albuterol: a rescue inhaler commonly used for breathing symptoms such as asthma-related wheezing.",
        "Lisinopril: a blood pressure medication.",
        "Metformin: a medication commonly used for blood sugar management.",
        "Cetirizine: an allergy medication.",
        "Amoxicillin: an antibiotic; people with penicillin allergy should be careful and consult a clinician.",
    ],
    "household_chen_shared": [
        "Chen Household shared home address: 123 Market St, San Francisco, CA.",
        "Chen Household shared billing address: 123 Market St, San Francisco, CA.",
        "Chen Household shared insurance contact: Blue Shield Family Plan, member services 1-800-555-0142.",
    ],
    "member_alice_medical": [
        "Alice is allergic to penicillin.",
        "Alice takes metformin 500mg with dinner.",
    ],
    "member_bob_medical": [
        "Bob takes lisinopril 10mg every morning.",
    ],
    "member_chris_medical": [
        "Chris had knee surgery in 2022 and uses ibuprofen only as needed.",
    ],
    "member_david_medical": [
        "David has no saved daily medications.",
    ],
    "member_eva_medical": [
        "Eva uses an albuterol inhaler before soccer.",
        "Eva is allergic to peanuts.",
    ],
}

MOCK_AGENTKIT_IMPORTS = {
    "alice": "Imported from Alice's care email: appointment with Dr. Rivera next Tuesday at 3 PM.",
    "bob": "Imported from Bob's care email: annual blood pressure follow-up reminder.",
    "chris": "Imported from Chris's care email: physical therapy check-in reminder.",
    "david": "Imported from David's care email: campus clinic wellness visit reminder.",
    "eva": "Imported from Eva's care email: pediatric asthma check-in next month.",
}

# Sample appointment emails (with real-looking address + time) used by the
# appointment planner when Scalekit Gmail is not connected, so the
# email -> Google Maps -> Google Calendar flow can be demoed offline.
MOCK_APPOINTMENT_EMAILS = {
    "alice": (
        "Subject: Appointment Confirmation\n\n"
        "Hi Alice, your appointment with Dr. Rivera is confirmed for next Tuesday at 3:00 PM "
        "at UCSF Medical Center, 505 Parnassus Ave, San Francisco, CA. "
        "Please arrive 15 minutes early and bring your insurance card."
    ),
    "bob": (
        "Subject: Blood Pressure Follow-up\n\n"
        "Hi Bob, this confirms your annual blood pressure follow-up next Thursday at 10:00 AM "
        "at Sutter Health, 1200 Van Ness Ave, San Francisco, CA."
    ),
    "chris": (
        "Subject: Physical Therapy Check-in\n\n"
        "Hi Chris, your physical therapy session is scheduled for tomorrow at 9:00 AM "
        "at Bay Area PT Clinic, 88 Kearny St, San Francisco, CA."
    ),
    "david": (
        "Subject: Campus Clinic Wellness Visit\n\n"
        "Hi David, your wellness visit is booked for next Monday at 1:00 PM "
        "at SJSU Student Health Center, 211 S 9th St, San Jose, CA."
    ),
    "eva": (
        "Subject: Pediatric Asthma Check-in\n\n"
        "Hi, Eva's pediatric asthma check-in is scheduled for next Wednesday at 2:30 PM "
        "at Children's Health Clinic, 3700 California St, San Francisco, CA."
    ),
}
