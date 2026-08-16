"""Hand-frozen `BaseSkill` catalog ids referenced directly by rule code
(situational skill-note handlers, `sheet.py`'s per-skill display hooks) —
same "stable id referenced by name across files" convention as
`rules/speed.py`'s `RACE_NORMAL_SPEED_ABILITY_ID`. Centralized here rather
than redeclared per file once more than one unrelated module needs the same
skill's id (`rules/speed.py`'s universal jump bonus and
`rules/classes/barbarian.py`'s Wilder Seemann both target Akrobatik, for
unrelated reasons) — a single source avoids the two ever drifting out of
sync with `base_skills.json`."""

from uuid import UUID

AKROBATIK_SKILL_ID = UUID("61a2cb21-fcda-4a2d-8fb5-8ed12133c648")
BERUF_SKILL_ID = UUID("7cf08043-8422-400c-88de-960f094fe9e6")
KLETTERN_SKILL_ID = UUID("bf8d0e63-8a96-4a0e-baf9-06a1cac4e4c7")
SCHWIMMEN_SKILL_ID = UUID("e5fa3283-96aa-49ee-8836-ba3062bae32d")
UEBERLEBENSKUNST_SKILL_ID = UUID("1b9fe08d-09e0-46c8-8772-dd573cab6fff")
