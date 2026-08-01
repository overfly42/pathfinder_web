"""Extract the Hexenmeister (Sorcerer) bloodline bonus-feat lists ("Talent
des Blutes" eligibility, one closed ~8-feat list per bloodline) from the PRD's
core-rulebook class page.

Unlike the /TalentIndex datatable (see import_feats_from_prd.py), this data
isn't exposed as a machine-readable endpoint — it only exists as prose on
http://prd.5footstep.de/Grundregelwerk/Klassen/Hexenmeister, one <h4> section
per bloodline with a "Bonustalente:" paragraph listing linked feat names. This
script fetches that page and parses those sections directly.

Each entry is matched against a previously-imported feat catalog (see
import_feats_from_prd.py) by name, so the output can be joined straight onto
`base_feats` ids once that catalog is loaded — this is the raw material for
the `BaseClassAbilityFeatOption` design in roadmap.md (closed per-bloodline
feat_id lists for the "Talent des Blutes" ability slot).

Usage:
    python import_hexenmeister_bloodlines.py --feats-catalog ../app/fixtures/imported/talente_prd_import.json [-o output.json]
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from html import unescape

SOURCE_URL = "http://prd.5footstep.de/Grundregelwerk/Klassen/Hexenmeister"

H4_RE = re.compile(r"<h4>([^<]*)</h4>")
BONUS_FEATS_RE = re.compile(r"Bonustalente:</strong>(.*?)<br\s*/?>", re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")

# The page's link text is occasionally a shortened display label rather than
# the feat's canonical name (e.g. "Entwaffnen" links to
# .../Talente/VerbessertesEntwaffnen, whose real name is "Verbessertes
# Entwaffnen"). Resolved by hand by checking the link target.
DISPLAY_NAME_ALIASES = {
    "entwaffnen": "Verbessertes Entwaffnen",
}


def strip_tags(value: str) -> str:
    value = TAG_RE.sub("", value)
    return unescape(value.replace("&nbsp;", " ")).strip()


def fetch_page(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "pathfinder_web-import/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("iso-8859-1")


def split_bonus_feats(segment_text: str) -> list[str]:
    """Split a 'Bonustalente:' paragraph's plain text on top-level commas,
    keeping parenthetical skill choices like 'Fertigkeitsfokus (Wissen
    (Arkanes))' intact as one entry."""
    text = segment_text.rstrip(".").strip()
    parts = re.split(r",\s*(?![^(]*\))", text)
    return [p.strip() for p in parts if p.strip()]


def parse_bloodlines(html: str) -> dict[str, list[str]]:
    headings = list(H4_RE.finditer(html))
    bloodlines: dict[str, list[str]] = {}
    for i, heading in enumerate(headings):
        name = strip_tags(heading.group(1))
        start = heading.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(html)
        chunk = html[start:end]

        match = BONUS_FEATS_RE.search(chunk)
        if not match:
            continue
        bloodlines[name] = split_bonus_feats(strip_tags(match.group(1)))
    return bloodlines


def resolve_against_catalog(bloodlines: dict[str, list[str]], catalog_path: str) -> list[dict]:
    with open(catalog_path, encoding="utf-8") as f:
        catalog = json.load(f)
    by_name = {entry["name"].lower(): entry for entry in catalog}

    resolved = []
    for bloodline, feats in bloodlines.items():
        entries = []
        for display_name in feats:
            base_name, _, skill_choice = display_name.partition(" (")
            if skill_choice.endswith(")"):
                skill_choice = skill_choice[:-1]
            skill_choice = skill_choice or None
            lookup_name = DISPLAY_NAME_ALIASES.get(base_name.lower(), base_name)

            catalog_entry = by_name.get(lookup_name.lower())
            entries.append(
                {
                    "display_name": display_name,
                    "feat_name": lookup_name,
                    "skill_choice": skill_choice,
                    "feat_id": catalog_entry["id"] if catalog_entry else None,
                    "prd_id": catalog_entry["prd_id"] if catalog_entry else None,
                }
            )
        resolved.append({"bloodline": bloodline, "bonus_feats": entries})
    return resolved


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--feats-catalog",
        default="../app/fixtures/imported/talente_prd_import.json",
        help="Path to the feat catalog produced by import_feats_from_prd.py, used to resolve feat ids (default: %(default)s)",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="hexenmeister_bloodline_bonus_feats.json",
        help="Output path for the staging JSON file (default: %(default)s)",
    )
    args = parser.parse_args()

    html = fetch_page(SOURCE_URL)
    bloodlines = parse_bloodlines(html)
    resolved = resolve_against_catalog(bloodlines, args.feats_catalog)

    unresolved = [
        (row["bloodline"], entry["display_name"])
        for row in resolved
        for entry in row["bonus_feats"]
        if entry["feat_id"] is None
    ]

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(resolved, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(resolved)} bloodlines to {args.output}")
    if unresolved:
        print(f"WARNING: {len(unresolved)} feat(s) could not be resolved against the catalog:")
        for bloodline, name in unresolved:
            print(f"  {bloodline}: {name}")


if __name__ == "__main__":
    main()
