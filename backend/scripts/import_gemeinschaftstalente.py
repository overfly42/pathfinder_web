"""Import the teamwork feats ("Gemeinschaftstalente") into `base_feats.json`
and the `BaseFeatRequired*` prerequisite tables — the Jäger's
"Genaues Ausmanövrieren" (Ausmanövrieren) and "Gemeinschaftstalente" bonus
feats (`import_jaeger.py`) pick from them, and before this script the catalog
had exactly one (Hordensturmangriff, from `build_feats_seed.py`'s race scope).

Source: the already-fetched PRD feat index (`imported/talente_prd_import.json`,
every row whose `type` contains "teamwork"), ids reused from it so a wider
`build_feats_seed.py` rerun can't mint duplicates (same as
`import_monster_feats.py`). Descriptions are the index's short summaries,
the same depth as every other `base_feats.json` row. The bracketed type
suffix some names carry ("Koordinierter Schuss [Gemeinschaft, Kampf]") is
stripped. Every feat gets `type` "teamwork" (`build_feats_seed.py`'s
`primary_type`: "teamwork,combat" -> "teamwork").

Left out, same "only currently relevant" call as `build_feats_seed.py`:
- Befreiender Schlag (Hobgoblin only — no Hobgoblin race here).
- Verwobenes Spezialisiertes Kinetisches Geschoss (Kineticist class feature).

Prerequisites (`REQUIREMENTS`) are hand-mapped from each feat's
`prerequisite` line; atoms with nothing to check against stay
`prerequisite_text` only (scripts/README.md §4: under-enforced is
recoverable, wrongly enforced isn't): "Fähigkeit zum Erlangen eines
Tiergefährten/Reittiers/Eidolons/Vertrauten", "ein weiteres/mindestens zwei
weitere Gemeinschaftstalente", "Klassenmerkmal Fallen finden",
"Wenigstens eine Stufe als Zauberkundiger".

Run with the project venv active (writes fixtures only; seed afterwards):
    cd backend && python scripts/import_gemeinschaftstalente.py
    python -m app.seed.feat_seed
"""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "app" / "fixtures"
SEED_DIR = FIXTURES / "seed"
IMPORTED = FIXTURES / "imported" / "talente_prd_import.json"

ID_NAMESPACE = uuid.UUID("3e7c1a92-5d48-4f06-b9a3-c2e8d4f17a65")

EXCLUDED = {"Befreiender Schlag", "Verwobenes Spezialisiertes Kinetisches Geschoss", "Hordensturmangriff"}

# feat name -> [(kind, value...)]: ("bab", n), ("ability", "IN", 13),
# ("skill", skill name, ranks), ("feat", feat name).
REQUIREMENTS: dict[str, list[tuple]] = {
    "Ausmanövrieren": [("bab", 4)],
    "Diebesbande": [("skill", "Bluffen", 1), ("skill", "Fingerfertigkeit", 1)],
    "Feldmedikus": [("skill", "Heilkunde", 5)],
    "Flankierender Tiergefährte": [("ability", "IN", 13), ("feat", "Defensive Kampfweise")],
    "Flächendeckendes Feuer": [("feat", "Kernschuss"), ("feat", "Präzisionsschuss")],
    "Gemeinschaftliche Finte": [("skill", "Bluffen", 1)],
    "Gemeinschaftliches Gegenstand ausschalten": [("skill", "Mechanismus ausschalten", 1)],
    "Genauer Schlag": [("ability", "GE", 13), ("bab", 1)],
    "Kavallerieformation": [("feat", "Berittener Kampf")],
    "Konzentrierter Beschuss": [("feat", "Kernschuss"), ("bab", 6)],
    "Koordinierter Schuss": [("feat", "Kernschuss")],
    "Koordinierter Sturmangriff": [("bab", 10)],
    "Künstlertruppe": [("skill", "Auftreten", 5)],
    "Mein Schwert gehört dir": [
        ("ability", "IN", 13),
        ("feat", "Defensive Kampfweise"),
        ("skill", "Motiv erkennen", 3),
    ],
    "Nutze den Augenblick": [("feat", "Kampfreflexe"), ("feat", "Verbesserter Kritischer Treffer")],
    "Rudelangriff": [("bab", 1)],
    "Rücken an Rücken": [("skill", "Wahrnehmung", 3)],
    "Schildwall": [("feat", "Umgang mit Schilden")],
    "Schwäche vortäuschen": [("skill", "Bluffen", 5)],
    "Verbesserte Gemeinschaftliche Finte": [
        ("skill", "Bluffen", 1),
        ("feat", "Gemeinschaftliche Finte"),
        ("feat", "Kampfreflexe"),
        ("bab", 6),
    ],
    "Verbessertes Gemeinsam ducken": [("feat", "Gemeinsam Ducken")],
    "Verbessertes Plätze tauschen": [("feat", "Plätze tauschen")],
    "Verbessertes Rücken an Rücken": [("feat", "Rücken an Rücken"), ("skill", "Wahrnehmung", 5)],
    "Waghalsiges Schwäche vortäuschen": [("feat", "Schwäche vortäuschen"), ("skill", "Bluffen", 5)],
}

NAME_SUFFIX_RE = re.compile(r"\s*\[[^\]]*\]$")
FOOTNOTE_RE = re.compile(r"\^\^[A-Za-z]*\^\^")


def uid(*parts: str) -> str:
    return str(uuid.uuid5(ID_NAMESPACE, "|".join(parts)))


def load(filename: str) -> list[dict]:
    return json.loads((SEED_DIR / filename).read_text(encoding="utf-8"))


def save(filename: str, rows: list[dict]) -> None:
    deduped: dict[str, dict] = {}
    for row in rows:
        deduped[row["id"]] = row
    (SEED_DIR / filename).write_text(
        json.dumps(list(deduped.values()), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def clean_prerequisite(text: str | None) -> str | None:
    if not text:
        return None
    return re.sub(r"\s+", " ", FOOTNOTE_RE.sub("", text)).strip()


def main() -> None:
    imported: dict[str, dict] = {}
    for row in json.loads(IMPORTED.read_text(encoding="utf-8")):
        if "teamwork" in row["type"]:
            imported.setdefault(row["id"], row)

    feats = load("base_feats.json")
    new_feats = []
    for row in imported.values():
        name = NAME_SUFFIX_RE.sub("", row["name"]).strip()
        if name in EXCLUDED:
            continue
        new_feats.append(
            {
                "id": row["id"],
                "name": name,
                "description": row["description"],
                "type": "teamwork",
                "prerequisite_text": clean_prerequisite(row["prerequisite"]),
            }
        )
    new_ids = {f["id"] for f in new_feats}
    feats = [f for f in feats if f["id"] not in new_ids] + sorted(new_feats, key=lambda f: f["name"])
    save("base_feats.json", feats)

    feat_id_by_name = {f["name"]: f["id"] for f in feats}
    skill_id_by_name = {s["name"]: s["id"] for s in load("base_skills.json")}
    assert set(REQUIREMENTS) <= {f["name"] for f in new_feats}, set(REQUIREMENTS) - {f["name"] for f in new_feats}

    tables = {
        "bab": load("base_feat_required_babs.json"),
        "ability": load("base_feat_required_ability_scores.json"),
        "skill": load("base_feat_required_skills.json"),
        "feat": load("base_feat_required_feats.json"),
    }
    for kind in tables:
        tables[kind] = [r for r in tables[kind] if r["feat_id"] not in new_ids]
    for feat_name, requirements in REQUIREMENTS.items():
        feat_id = feat_id_by_name[feat_name]
        for requirement in requirements:
            kind, *values = requirement
            row = {"id": uid(feat_id, kind, *map(str, values)), "feat_id": feat_id, "group_id": None}
            if kind == "bab":
                row["minimum_bab"] = values[0]
            elif kind == "ability":
                row["ability"], row["minimum_score"] = values
            elif kind == "skill":
                row["skill_id"], row["minimum_ranks"] = skill_id_by_name[values[0]], values[1]
            else:
                row["required_feat_id"] = feat_id_by_name[values[0]]
            tables[kind].append(row)
    save("base_feat_required_babs.json", tables["bab"])
    save("base_feat_required_ability_scores.json", tables["ability"])
    save("base_feat_required_skills.json", tables["skill"])
    save("base_feat_required_feats.json", tables["feat"])

    print("Teamwork feats:", len(new_feats))
    print("Ausmanövrieren:", feat_id_by_name["Ausmanövrieren"])


if __name__ == "__main__":
    main()
