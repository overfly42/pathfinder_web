"""Import the German Pathfinder PRD's talent index into a staging JSON file
shaped like `BaseFeat` (id/name/description/type), plus reference-only fields
(prerequisite text, sourcebook, page) that don't have a home in that model yet.

The site's /TalentIndex page renders an empty <table> filled client-side via
DataTables from a JSON endpoint — that endpoint is already free of navigation
chrome, so no HTML scraping/stripping is needed, just a straight fetch.

This is a staging file, not a drop-in replacement for
backend/app/fixtures/seed/base_feats.json:
- `description` here is the PRD's short summary column, not full rule text.
- `prerequisite`/`source`/`page` have no columns on BaseFeat — prerequisites
  there are structured rows (BaseFeatRequiredFeat, BaseFeatRequiredSkill, ...)
  that need per-feat parsing against other catalogs, not a free-text field.
  They're kept here for manual review / future structured-prerequisite work.

Usage:
    python import_feats_from_prd.py [-o output.json]
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
import uuid
from html import unescape

SOURCE_URL = "http://prd.5footstep.de/cache/prd_datatable__talente.txt"

# Stable namespace so re-running the script produces the same feat ids
# (derived from the PRD's own numeric page id) instead of fresh random UUIDs
# on every run.
NAMESPACE = uuid.UUID("a4b6f1f0-6c2e-4b3a-9a3b-9e6f2f1a7c3d")

NAME_LINK_RE = re.compile(r"<a[^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")

# German "Art" column value -> type slug. Empty string means no category was
# given on the index (most feats) and maps to "general". Unrecognized values
# fall back to a slugified version of the German term itself rather than a
# guessed translation, so nothing is silently mistranslated.
ART_TO_TYPE = {
    "": "general",
    "Kampf": "combat",
    "Metamagie": "metamagic",
    "Erschaffung von Gegenständen": "item_creation",
    "Gemeinschaft": "teamwork",
}


def slugify(value: str) -> str:
    value = value.strip().lower()
    value = value.replace("ä", "ae").replace("ö", "oe").replace("ü", "ue").replace("ß", "ss")
    value = re.sub(r"[^a-z0-9]+", "_", value)
    return value.strip("_")


def clean_text(value: str) -> str:
    """Strip HTML tags and unescape entities from a data-table cell."""
    value = TAG_RE.sub("", value)
    return unescape(value).strip()


def art_to_type(art: str) -> str:
    parts = [p.strip() for p in art.split(",") if p.strip()]
    if not parts:
        return "general"
    slugs = []
    for part in parts:
        slug = ART_TO_TYPE.get(part, slugify(part))
        if slug not in slugs:
            slugs.append(slug)
    return ",".join(slugs)


def fetch_raw() -> list[dict]:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "pathfinder_web-import/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.load(response)
    return payload["data"]


def convert(raw_rows: list[dict]) -> list[dict]:
    feats = []
    for row in raw_rows:
        prd_id = row.get("ID", "").strip()
        name_match = NAME_LINK_RE.search(row.get("Name", ""))
        name = clean_text(name_match.group(1) if name_match else row.get("Name", ""))
        if not name:
            continue

        feats.append(
            {
                "id": str(uuid.uuid5(NAMESPACE, f"prd-talent-{prd_id}")),
                "name": name,
                "description": clean_text(row.get("Beschreibung", "")),
                "type": art_to_type(row.get("Art", "")),
                "prerequisite": clean_text(row.get("Voraussetzung", "")) or None,
                "source": row.get("Regelwerk", "").strip() or None,
                "page": row.get("Seite", "").strip() or None,
                "prd_id": prd_id,
            }
        )
    feats.sort(key=lambda f: f["name"])
    return feats


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        default="talente_prd_import.json",
        help="Output path for the staging JSON file (default: %(default)s)",
    )
    args = parser.parse_args()

    raw_rows = fetch_raw()
    feats = convert(raw_rows)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(feats, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(feats)} feats to {args.output}")


if __name__ == "__main__":
    main()
