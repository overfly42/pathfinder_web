"""Kleriker (Cleric) domains and subdomains (`scripts/import_kleriker.py`,
`scripts/import_kleriker_unterdomaenen.py`). The same domain/subdomain
ability rows are granted by the Druide's Naturdomäne and the Göttlicher
Jäger's Domäne too, so whatever is computed here applies to all three.

- Unterdomäne der Federn: Fliegen as a class skill (`CLASS_SKILL_GRANTS` on
  its "Verliehene Fähigkeiten" row); the +1 manoeuvrability step for flight
  spells stays text (partial note)."""

from uuid import UUID

from ..skill_ids import FLIEGEN_SKILL_ID

FEDERN_VERLIEHENE_FAEHIGKEITEN_ID = UUID("97073a45-991b-54a4-a598-b0f45fe4caec")

CLASS_SKILL_GRANTS: dict[UUID, frozenset[UUID]] = {
    FEDERN_VERLIEHENE_FAEHIGKEITEN_ID: frozenset({FLIEGEN_SKILL_ID}),
}
PARTIAL_EFFECT_NOTES: dict[UUID, str] = {
    FEDERN_VERLIEHENE_FAEHIGKEITEN_ID: "Manövrierfähigkeit beim Fliegen durch Zauber (+1 Stufe) nicht berechnet",
}
