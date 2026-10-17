"""Vertrauter — the familiar's own abilities from the PRD's familiar table
(Magier, "Besondere Fähigkeiten des Vertrauten"; `scripts/import_familiars.py`),
unlocked by the master's familiar level (`app/companions.py`).

- "Zauberresistenz" (`FEATURE_SUMMARY_HANDLERS`): SR = master level + 5.
- "Vertrauten ausspähen": the master's Ausspähung 1/Tag — a read-out.
- "Wachsamkeit": the master's +2 Wahrnehmung/Motiv erkennen while the
  familiar is within arm's reach — situational, shown on the master's
  skills (`rules/companions.py`'s `familiar_master_skill_notes`) and
  summarized here.
- Verbessertes Entrinnen, Empathische Verbindung, Zauber teilen,
  Berührungszauber übermitteln, Mit Meister sprechen, Mit Tieren seiner Art
  sprechen: descriptive.
"""

from collections.abc import Callable
from uuid import UUID

from ..context import CharacterContext

WACHSAMKEIT_ABILITY_ID = UUID("abc2059a-235f-54c7-8cb8-76464c20cd9b")
ZAUBERRESISTENZ_ABILITY_ID = UUID("f916fc82-91bf-5c2b-82b3-37dd3e1e2d1c")
VERTRAUTEN_AUSSPAEHEN_ABILITY_ID = UUID("9b99f35e-d224-5a87-a451-177791289d66")


def _zauberresistenz(context: CharacterContext) -> str:
    level = context.companion_effective_level
    return f"ZR {level + 5}" if level is not None else "ZR = Stufe des Meisters + 5"


FEATURE_SUMMARY_HANDLERS: dict[UUID, Callable[[CharacterContext], str]] = {
    WACHSAMKEIT_ABILITY_ID: lambda _context: "Meister: +2 Wahrnehmung und Motiv erkennen, solange in Armeslänge",
    ZAUBERRESISTENZ_ABILITY_ID: _zauberresistenz,
    VERTRAUTEN_AUSSPAEHEN_ABILITY_ID: lambda _context: "Meister: 1/Tag Ausspähung auf den Vertrauten",
}
