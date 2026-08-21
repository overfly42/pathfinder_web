"""Import the German Pathfinder PRD's spell index into a staging JSON file
shaped roughly like `BaseSpell` (id/name/school/description), plus per-class
grade data and reference-only fields (subschool, category, sourcebook, page)
that don't have a home in that model yet.

Same technique as `import_feats_from_prd.py` — the site's /ZauberIndex page
renders an empty <table> filled client-side via DataTables from a JSON
endpoint, so no HTML scraping/stripping is needed beyond the <a> wrapper
around Name. See scripts/README.md.

This is a staging file, not a drop-in replacement for
backend/app/fixtures/seed/base_spells.json / base_class_spells.json:
- `description` here is the PRD's short summary column, not full rule text —
  and unlike talente, the bulk index has *no* casting-time/components/range/
  duration/save/SR columns at all (checked against
  js/datatables/prd_datatable.js's 'zauber' case). Those live only in each
  spell's own page, in a consistent stat-block right after the title
  (`Schule: ...; Grad: ...` / `Zeitaufwand:` / `Komponenten:` / `Reichweite:`
  / `Ziel/Effekt:` or `Bereich:` / `Wirkungsdauer:` / `Rettungswurf: ...;
  Zauberresistenz: ...`, then free prose) — more regular than a feat's
  prerequisite prose, so a per-spell fetch (README §2 pattern, via
  `source_url` below) is worth doing before this data is used for anything
  beyond a short blurb. Not fetched here — 1909 requests is only worth
  doing once when actually wiring that up.
- `grades_by_class` keys are PRD class names verbatim (including classes not
  yet modeled in base_classes, e.g. Alchemist/Inquisitor/Kampfmagus) — needs
  matching against base_classes.json in a follow-up build step.
- Duplicate `id`s occur for spells reprinted across sourcebooks (same known
  PRD quirk as talente) — not deduped here, left for the build step.

Usage:
    python import_zauber_prd.py [-o output.json]
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
import uuid
from html import unescape

SOURCE_URL = "http://prd.5footstep.de/cache/prd_datatable__zauber.txt"
PERMALINK_TEMPLATE = "http://prd.5footstep.de/Permalink?page_id={id}"

# Stable namespace so re-running the script produces the same spell ids
# (derived from the PRD's own numeric page id) instead of fresh random UUIDs
# on every run. Distinct from import_feats_from_prd.py's NAMESPACE so a
# spell and a feat that happened to share a PRD page id never collide.
NAMESPACE = uuid.UUID("d3a9f5f1-2b8e-4a6f-9c1d-7e4b6a2f5d8c")

NAME_LINK_RE = re.compile(r"<a[^>]*>(.*?)</a>", re.IGNORECASE | re.DOTALL)
TAG_RE = re.compile(r"<[^>]+>")

# Non-grade/meta columns in the raw row; everything else is a per-class grade
# column (see js/datatables/prd_datatable.js's 'zauber' case).
META_COLUMNS = {"ID", "Name", "Grad", "Schule", "Unterschule", "Kategorie", "Beschreibung", "Regelwerk", "Seite"}


def clean_text(value: str) -> str:
    """Strip HTML tags and unescape entities from a data-table cell."""
    value = TAG_RE.sub("", value)
    return unescape(value).strip()


def fetch_raw() -> list[dict]:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "pathfinder_web-import/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("iso-8859-1"))
    return payload["data"]


def convert(raw_rows: list[dict]) -> list[dict]:
    spells = []
    for row in raw_rows:
        prd_id = row.get("ID", "").strip()
        name_match = NAME_LINK_RE.search(row.get("Name", ""))
        name = clean_text(name_match.group(1) if name_match else row.get("Name", ""))
        if not name:
            continue

        grades_by_class = {}
        for key, value in row.items():
            if key in META_COLUMNS:
                continue
            value = value.strip() if isinstance(value, str) else value
            if value:
                grades_by_class[key] = int(value)

        spells.append(
            {
                "id": str(uuid.uuid5(NAMESPACE, f"prd-zauber-{prd_id}")),
                "name": name,
                "school": clean_text(row.get("Schule", "")) or None,
                "subschool": clean_text(row.get("Unterschule", "")) or None,
                "category": clean_text(row.get("Kategorie", "")) or None,
                "description": clean_text(row.get("Beschreibung", "")),
                "grades_by_class": grades_by_class,
                "source": row.get("Regelwerk", "").strip() or None,
                "page": row.get("Seite", "").strip() or None,
                "prd_id": prd_id,
                "source_url": PERMALINK_TEMPLATE.format(id=prd_id),
            }
        )
    spells.sort(key=lambda s: s["name"])
    return spells


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        default="zauber_prd_import.json",
        help="Output path for the staging JSON file (default: %(default)s)",
    )
    args = parser.parse_args()

    raw_rows = fetch_raw()
    spells = convert(raw_rows)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(spells, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(spells)} spells to {args.output}")


if __name__ == "__main__":
    main()
