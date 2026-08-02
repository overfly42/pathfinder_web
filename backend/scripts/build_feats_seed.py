"""Turns the bulk PRD feat import (`talente_prd_import.json`, 1506 rows across
every sourcebook) into DB-shaped seed data for `base_feats` plus the six
`BaseFeatRequired*` prerequisite tables, scoped to what's actually relevant
today (Grundregelwerk feats, plus any other-sourcebook feat whose
prerequisite mentions one of the four races or twelve classes/archetypes
currently in the database) — see the "necessary to add the talents" chat
turn in this session for the reasoning.

Reconciles against the 16 feats already hand-seeded in `base_feats.json`:
five of those use non-canonical PRD names (translation drift, same problem
found and fixed for `base_skills` earlier this session) — `RECONCILE_BY_NAME`
maps each existing name to its PRD-canonical counterpart so the existing row
(and its existing `character_feats` rows) keeps its id while picking up the
canonical name/type/prerequisite from the import.

Prerequisite parsing splits on ";" into top-level clauses (always AND), then
per clause: if it contains a top-level "oder" (outside parentheses, since
e.g. "Auftreten (Gesang oder Redekunst)" is a skill sub-choice, not a real
OR), every comma/oder-separated item in that clause is treated as one
OR-group (`BaseFeatRequiredFeat.group_id`, shared across whichever of the
six tables the resolved items land in) — but only when at least two items
actually resolve against the current catalogs; a lone resolved item (e.g.
"Elf oder Halb-Elf" when Halb-Elf isn't a modeled race) is emitted as a
plain ungrouped requirement instead, which is equivalent given the other
side of the OR can never apply to any character that can currently exist in
this database anyway. Clauses without "oder" split on "," into independent
AND atoms, as before. Individual atoms that don't resolve against the
current catalogs are always dropped rather than guessed at — better an
under-enforced prerequisite than a wrong one. `prerequisite_text` is always
populated when the source has any prerequisite text, regardless of whether
it parsed.

Usage (from `backend/`, project venv active):
    python scripts/build_feats_seed.py
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

SEED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed"
IMPORTED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "imported"

ROOT_CLASS_NAMES = [
    "Barbar", "Barde", "Druide", "Hexenmeister", "Kleriker", "Kämpfer",
    "Magier", "Mönch", "Mystiker", "Paladin", "Schurke", "Waldläufer",
]
ARCHETYPE_NAMES = [
    "Berserker", "Invulnerable Rager", "Archivar", "Sänger der Meere",
    "Tierfreund", "Weltenwandler", "Fluchbringer", "Blutlinie: Drache",
    "Kriegspriester", "Heiler des Volkes", "Waffenmeister", "Söldnerkommandant",
    "Zwei-Waffen-Kämpfer", "Beschwörer", "Kriegsmagier", "Zen-Archer",
    "Fäuste des Windes", "Wiedergänger", "Lebensbündnis", "Rächer",
    "Hüter des Glaubens", "Meucheldieb", "Klingentänzer", "Bogenschütze",
    "Gefährtenbinder",
]
RACE_NAMES = ["Mensch", "Halbling", "Halb-Ork", "Elf"]

# name in the existing hand-seeded base_feats.json -> canonical PRD name.
# Manually matched by mechanics (see chat) since the import's short blurbs
# don't share wording with the existing hand-written descriptions.
RECONCILE_BY_NAME = {
    "Punktzielschuss": "Kernschuss",
    "Gezielter Schuss": "Präzisionsschuss",
    "Schneller Schuss": "Schnelles Schießen",
    "Tödlicher Schuss": "Tödliche Zielgenauigkeit",
    "Zäh wie Leder": "Abhärtung",
    "Eisenwille": "Eiserner Wille",
    "Blitzreflexe": "Blitzschnelle Reflexe",
    "Zweiwaffenkampf": "Kampf mit zwei Waffen",
    "Kraftangriff": "Heftiger Angriff",
    "Wurfwaffenexperte": "Fernschuss",
    "Beweglich wie eine Katze": "Behände Bewegung",
    # Same name in both, different id:
    "Verbesserte Initiative": "Verbesserte Initiative",
    "Waffenfokus": "Waffenfokus",
    "Ausweichen": "Ausweichen",
    "Kampfreflexe": "Kampfreflexe",
    "Fertigkeitsfokus": "Fertigkeitsfokus",
}

CLASS_ABBREV = {
    "KÄM": "Kämpfer", "MAG": "Magier", "HXM": "Hexenmeister", "WAL": "Waldläufer",
    "DRU": "Druide", "MÖN": "Mönch", "SRK": "Schurke", "BAR": "Barde",
    "BRB": "Barbar", "KLE": "Kleriker", "PAL": "Paladin", "ORA": "Mystiker",
}

FOOTNOTE_RE = re.compile(r"\^\^[A-Za-z]*\^\^")
PAREN_RE = re.compile(r"\([^)]*\)")
ODER_RE = re.compile(r"\boder\b", re.IGNORECASE)
ABILITY_RE = re.compile(r"^(ST|GE|KO|IN|WE|CH)\s*(\d+)\+?$")
BAB_RE = re.compile(r"^(?:GAB|Grund-Angriffs\s*bonus)\s*\+?\s*(\d+)$", re.IGNORECASE)
_ROOT_CLASS_ALT = "|".join(re.escape(n) for n in ROOT_CLASS_NAMES)
CLASS_LEVEL_RE = re.compile(
    "^(" + _ROOT_CLASS_ALT + r")(?:stufe|\s+Stufe)?\s+(\d+)\+?$"
)
CLASS_LEVEL_ORDINAL_RE = re.compile(
    r"^(\d+)\.\s*(" + _ROOT_CLASS_ALT + r")stufe$"
)
CLASS_LEVEL_ABBREV_RE = re.compile(
    "^(" + "|".join(CLASS_ABBREV) + r")\s+(\d+)$"
)
WEAPON_SUFFIX_RE = re.compile(r"\s+mit\s+gewählter?\s+Waffe$", re.IGNORECASE)
SKILL_RANKS_A_RE = re.compile(r"^(.+?)\s+(\d+)\s*(?:Fertigkeitsr(?:änge|ang)|Ränge|Rang)$")
SKILL_RANKS_B_RE = re.compile(r"^(\d+)\s*(?:Fertigkeitsr(?:änge|ang)|Rang)\s+(?:in\s+)?(.+)$")
CLASS_ABILITY_RE = re.compile(r"^Klassen(?:merkmal|fähigkeit)\s+(.+)$")


# Fixed namespace so requirement-row ids are deterministic across reruns
# (content-derived via uuid5, not uuid.uuid4()) — otherwise every rerun mints
# a fresh id for the same logical requirement and upsert-by-id duplicates
# instead of updating. See scripts/README.md §4.
ID_NAMESPACE = uuid.UUID("6f2b6f0a-6c1a-4f1a-9b1e-7a6f7a6f7a6f")


def _stable_id(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def _load(path: Path) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))


def _clean(segment: str) -> str:
    return FOOTNOTE_RE.sub("", segment).strip(" .;")


# Paren-aware separator splits: don't split on a comma/"oder" that falls
# inside a parenthetical (e.g. "Auftreten (Gesang oder Redekunst) 10 Ränge"
# stays one atom) — same technique as scripts/README.md §3's comma-splitting
# note, extended to also treat "oder" as a separator for OR-clauses.
_NOT_IN_PARENS = r"(?![^(]*\))"
COMMA_SPLIT_RE = re.compile(r"\s*,\s*" + _NOT_IN_PARENS)
OR_SPLIT_RE = re.compile(r"\s*(?:,|\boder\b)\s*" + _NOT_IN_PARENS, re.IGNORECASE)


def top_level_clauses(prerequisite: str) -> list[str]:
    return [c.strip() for c in prerequisite.split(";") if c.strip()]


def clause_has_top_level_oder(clause: str) -> bool:
    without_parens = PAREN_RE.sub("", clause)
    return bool(ODER_RE.search(without_parens))


def split_and_atoms(clause: str) -> list[str]:
    return [_clean(p) for p in COMMA_SPLIT_RE.split(clause) if _clean(p)]


def split_or_items(clause: str) -> list[str]:
    return [_clean(p) for p in OR_SPLIT_RE.split(clause) if _clean(p)]


def dedupe_by_id(feats: list[dict]) -> list[dict]:
    """A feat reprinted across sourcebooks appears as two rows with the same
    id (known PRD quirk, see scripts/README.md) — keep the Grundregelwerk
    copy when one exists, else the first."""
    by_id: dict[str, dict] = {}
    for feat in feats:
        existing = by_id.get(feat["id"])
        if existing is None or (feat["source"] == "Grundregelwerk" and existing["source"] != "Grundregelwerk"):
            by_id[feat["id"]] = feat
    return list(by_id.values())


def is_relevant(feat: dict, term_pattern: re.Pattern) -> bool:
    if feat["source"] == "Grundregelwerk":
        return True
    prereq = feat.get("prerequisite")
    return bool(prereq and term_pattern.search(prereq))


def primary_type(raw_type: str) -> str:
    return raw_type.split(",")[0].strip()


def main() -> None:
    imported = _load(IMPORTED_DIR / "talente_prd_import.json")
    imported = dedupe_by_id(imported)

    existing = _load(SEED_DIR / "base_feats.json")
    existing_by_name = {f["name"]: f for f in existing}

    term_pattern = re.compile(
        "|".join(re.escape(t) for t in RACE_NAMES + ROOT_CLASS_NAMES + ARCHETYPE_NAMES)
    )
    relevant = [f for f in imported if is_relevant(f, term_pattern)]
    relevant_by_name = {f["name"]: f for f in relevant}

    # --- base_feats ---------------------------------------------------
    final_feats: list[dict] = []
    canonical_to_final_id: dict[str, str] = {}  # PRD canonical name -> final row id
    used_import_ids: set[str] = set()

    for old_name, canonical_name in RECONCILE_BY_NAME.items():
        old_row = existing_by_name[old_name]
        import_row = relevant_by_name.get(canonical_name)
        if import_row is None:
            # Not in the relevant subset (shouldn't happen for these 16 —
            # all are Grundregelwerk) but keep the existing row rather than
            # dropping it.
            final_feats.append(old_row)
            canonical_to_final_id[old_name] = old_row["id"]
            continue
        used_import_ids.add(import_row["id"])
        merged = {
            "id": old_row["id"],
            "name": canonical_name,
            "description": old_row["description"],
            "type": primary_type(import_row["type"]),
            "prerequisite_text": import_row["prerequisite"],
        }
        final_feats.append(merged)
        canonical_to_final_id[canonical_name] = old_row["id"]

    for feat in relevant:
        if feat["id"] in used_import_ids:
            continue
        row = {
            # Reuse the import's own id (stable across reruns, unlike
            # uuid.uuid4()) so re-running this script upserts instead of
            # duplicating — see scripts/README.md §4.
            "id": feat["id"],
            "name": feat["name"],
            "description": feat["description"] or feat["name"],
            "type": primary_type(feat["type"] or "general"),
            "prerequisite_text": feat["prerequisite"],
        }
        final_feats.append(row)
        canonical_to_final_id[feat["name"]] = row["id"]

    # --- lookups for prerequisite resolution ---------------------------
    skills = _load(SEED_DIR / "base_skills.json")
    skill_id_by_name = {s["name"]: s["id"] for s in skills}

    classes = _load(SEED_DIR / "base_classes.json")
    root_class_id_by_name = {c["name"]: c["id"] for c in classes if c.get("arch_class_of") is None}

    class_abilities = _load(SEED_DIR / "base_class_abilities.json")
    ability_id_by_name = {a["name"]: a["id"] for a in class_abilities}

    races = _load(SEED_DIR / "base_races.json")
    race_id_by_name = {r["name"]: r["id"] for r in races}

    feat_id_by_name = dict(canonical_to_final_id)

    # --- structured prerequisite rows -----------------------------------
    required_feats: list[dict] = []
    required_skills: list[dict] = []
    required_class_levels: list[dict] = []
    required_class_abilities: list[dict] = []
    required_races: list[dict] = []
    required_ability_scores: list[dict] = []
    required_babs: list[dict] = []

    unresolved_atoms: list[tuple[str, str]] = []

    buckets: dict[str, list[dict]] = {
        "ability_score": required_ability_scores,
        "bab": required_babs,
        "class_level": required_class_levels,
        "skill": required_skills,
        "class_ability": required_class_abilities,
        "race": required_races,
        "feat": required_feats,
    }

    def resolve_atom(atom: str, self_feat_id: str) -> tuple[str, dict] | None:
        """One prerequisite atom -> (bucket name, row fields sans id/feat_id/
        group_id), or None if it doesn't resolve against a current catalog."""
        m = ABILITY_RE.match(atom)
        if m:
            return "ability_score", {"ability": m.group(1), "minimum_score": int(m.group(2))}

        m = BAB_RE.match(atom)
        if m:
            return "bab", {"minimum_bab": int(m.group(1))}

        ordinal_m = CLASS_LEVEL_ORDINAL_RE.match(atom)
        m = CLASS_LEVEL_RE.match(atom) or CLASS_LEVEL_ABBREV_RE.match(atom)
        if ordinal_m or m:
            class_name, level = (
                (ordinal_m.group(2), ordinal_m.group(1)) if ordinal_m
                else (CLASS_ABBREV.get(m.group(1), m.group(1)), m.group(2))
            )
            base_class_id = root_class_id_by_name.get(class_name)
            if base_class_id:
                return "class_level", {"base_class_id": base_class_id, "minimum_level": int(level)}

        m = SKILL_RANKS_A_RE.match(atom) or SKILL_RANKS_B_RE.match(atom)
        if m:
            groups = m.groups()
            skill_name, ranks = (groups[0], groups[1]) if not groups[0].isdigit() else (groups[1], groups[0])
            skill_id = skill_id_by_name.get(skill_name.strip())
            if skill_id:
                return "skill", {"skill_id": skill_id, "minimum_ranks": int(ranks)}
            return None

        m = CLASS_ABILITY_RE.match(atom)
        if m:
            ability_id = ability_id_by_name.get(m.group(1).strip())
            if ability_id:
                return "class_ability", {"ability_id": ability_id}
            return None

        if atom in race_id_by_name:
            return "race", {"race_id": race_id_by_name[atom]}

        feat_name_candidate = WEAPON_SUFFIX_RE.sub("", atom)
        target_feat_id = feat_id_by_name.get(feat_name_candidate)
        if target_feat_id and target_feat_id != self_feat_id:
            return "feat", {"required_feat_id": target_feat_id}

        return None

    def emit(bucket: str, fields: dict, feat_id: str, group_id: str | None) -> None:
        # Deterministic id (feat + kind + content, deliberately excluding
        # group_id — see ID_NAMESPACE note) so an identical requirement
        # upserts cleanly across reruns instead of duplicating.
        row_id = _stable_id(feat_id, bucket, json.dumps(fields, sort_keys=True))
        buckets[bucket].append({"id": row_id, "feat_id": feat_id, "group_id": group_id, **fields})

    def resolve_oder_clause(
        clause: str, feat_id: str
    ) -> tuple[list[tuple[str, dict]], list[tuple[str, dict]], list[str]]:
        """A clause with a top-level "oder" almost always looks like a
        natural-language enumeration ("A, B oder C") where only the *last*
        comma-run is actually the OR-list — a leading item is often an
        unrelated mandatory AND atom (e.g. "KO 13, Halb-Ork, Ork oder
        Zwerg." is "CON 13 AND (half-orc OR orc OR dwarf)", not a 2-way OR
        between CON and race). So: oder-split only the last comma-item to
        get the core OR-run, then walk backward through the preceding
        comma-items, absorbing each into the run only while it resolves to
        the *same* requirement kind as the run already has — a same-kind
        chain is safe to treat as more OR alternatives, a kind change means
        we've walked past the enumeration into an unrelated AND atom.

        Returns (or_group_members, plain_and_atoms, unresolved_texts) —
        or_group_members only used when >=2 resolve (see module docstring
        for the singleton-run fallback)."""
        raw_items = split_and_atoms(clause)
        if not raw_items:
            return [], [], []

        *leading, last = raw_items
        core_resolved = [(item, resolve_atom(item, feat_id)) for item in split_or_items(last)]
        target_bucket = next((atom[0] for _, atom in core_resolved if atom is not None), None)

        absorbed: list[tuple[str, tuple[str, dict] | None]] = []
        cut = len(leading)
        if target_bucket is not None:
            for item in reversed(leading):
                atom = resolve_atom(item, feat_id)
                if atom is not None and atom[0] == target_bucket:
                    absorbed.insert(0, (item, atom))
                    cut -= 1
                else:
                    break

        run = absorbed + core_resolved
        matched = [atom for _, atom in run if atom is not None]
        unresolved_texts = [item for item, atom in run if atom is None]

        or_group_members = matched if len(matched) >= 2 else []
        plain_and_atoms = matched if len(matched) == 1 else []

        for item in leading[:cut]:
            atom = resolve_atom(item, feat_id)
            if atom is not None:
                plain_and_atoms.append(atom)
            else:
                unresolved_texts.append(item)

        return or_group_members, plain_and_atoms, unresolved_texts

    for name, feat_id in list(feat_id_by_name.items()):
        source_row = relevant_by_name.get(name)
        if source_row is None:
            # One of the 16 reconciled feats whose canonical form wasn't in
            # the relevant subset for some reason; already has no prereq text.
            continue
        prereq = source_row["prerequisite"]
        if not prereq:
            continue

        for clause in top_level_clauses(prereq):
            if clause_has_top_level_oder(clause):
                or_group_members, plain_atoms, unresolved_texts = resolve_oder_clause(clause, feat_id)
                for item in unresolved_texts:
                    unresolved_atoms.append((name, item))
                if or_group_members:
                    group_id = str(uuid.uuid4())
                    for bucket, fields in or_group_members:
                        emit(bucket, fields, feat_id, group_id)
                for bucket, fields in plain_atoms:
                    emit(bucket, fields, feat_id, None)
            else:
                for atom_text in split_and_atoms(clause):
                    atom = resolve_atom(atom_text, feat_id)
                    if atom is None:
                        unresolved_atoms.append((name, atom_text))
                        continue
                    bucket, fields = atom
                    emit(bucket, fields, feat_id, None)

    # --- write output ----------------------------------------------------
    def dump(filename: str, rows: list[dict]) -> None:
        (SEED_DIR / filename).write_text(
            json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    dump("base_feats.json", final_feats)
    dump("base_feat_required_feats.json", required_feats)
    dump("base_feat_required_skills.json", required_skills)
    dump("base_feat_required_class_levels.json", required_class_levels)
    dump("base_feat_required_class_abilities.json", required_class_abilities)
    dump("base_feat_required_races.json", required_races)
    dump("base_feat_required_ability_scores.json", required_ability_scores)
    dump("base_feat_required_babs.json", required_babs)

    print(f"feats: {len(final_feats)} (relevant subset: {len(relevant)}, reconciled: {len(RECONCILE_BY_NAME)})")
    print(f"required_feats: {len(required_feats)}")
    print(f"required_skills: {len(required_skills)}")
    print(f"required_class_levels: {len(required_class_levels)}")
    print(f"required_class_abilities: {len(required_class_abilities)}")
    print(f"required_races: {len(required_races)}")
    print(f"required_ability_scores: {len(required_ability_scores)}")
    print(f"required_babs: {len(required_babs)}")
    print(f"unresolved atoms: {len(unresolved_atoms)}")
    for feat_name, atom in unresolved_atoms[:40]:
        print(f"  {feat_name!r}: {atom!r}")


if __name__ == "__main__":
    main()
