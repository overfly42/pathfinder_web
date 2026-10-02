"""Import the rings from the Ausrüstungskompendium's ring page into a staging
JSON file for `build_wondrous_items_seed.py` - the compendium lists ~69 rings
vs. the ~38 on the Grundregelwerk's `MagischeRinge` page that
`import_wondrous_items_prd.py` already covers.

Source page:

    http://prd.5footstep.de/Ausruestungskompendium/RingeZaubersteckenZauberzepter/Ringe

Reuses `import_wondrous_items_prd.py`'s fetch/clean helpers. Differences
from the Grundregelwerk page this script handles:

- 22 of the entries have no `Ausrüstungsplatz` field in their stat block
  (`Aura`/`ZS`/`Preis`/`Gewicht` only). They are on a rings page, so the
  slot defaults to "Ring".
- Three entries have irregular stat blocks (Kletterring: unbolded
  "Gewicht"; Ring des Zauberwissens: "Weight" instead of "Gewicht";
  Sternschnuppenring: "Gewicht" with no value) - the regex tolerates all
  three, an empty weight becomes "-".
- Names carry `&nbsp;` and a few are miscased ("rattenzahnring") - names
  are whitespace-normalized and capitalized.
- Entries whose name already exists in `base_items.json` (the rings the
  Grundregelwerk import already seeded) are skipped, so re-running the
  builder only adds rings that were really missing and never overwrites
  existing rows.

Usage:
    python import_ausruestung_ringe_prd.py [-o output.json]
    python build_wondrous_items_seed.py -i ../app/fixtures/imported/ausruestung_ringe_prd_import.json
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from import_wondrous_items_prd import END_MARKER_RE, TITLE_RE, clean_text, fetch_html

URL = "http://prd.5footstep.de/Ausruestungskompendium/RingeZaubersteckenZauberzepter/Ringe"
SEED_PATH = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed" / "base_items.json"

STAT_BLOCK_RE = re.compile(
    r"(?:<strong>Ausrüstungsplatz</strong>\s*(?P<slot>.*?);\s*)?"
    r"<strong>Preis</strong>\s*(?P<price>.*?)\s*[;,]?\s*"
    r"(?:<strong>)?(?:Gewicht|Weight)(?:</strong>)?\s*(?P<weight>.*?)</p>",
    re.DOTALL,
)
BESCHREIBUNG_RE = re.compile(r"<strong>BESCHREIBUNG</strong></p>.*?<hr\s*/?>", re.DOTALL)
ERSCHAFFUNG_RE = re.compile(r"<strong>ERSCHAFFUNG(?:SVORAUSSETZUNGEN)?</strong>")


def normalize_name(raw: str) -> str:
    name = clean_text(raw)
    return name[0].upper() + name[1:] if name else name


def parse_page(html: str) -> list[dict]:
    end_match = END_MARKER_RE.search(html)
    content = html[: end_match.start()] if end_match else html
    titles = list(TITLE_RE.finditer(content))
    rows = []
    for i, title_match in enumerate(titles):
        name = normalize_name(title_match.group("name"))
        block_end = titles[i + 1].start() if i + 1 < len(titles) else len(content)
        block = content[title_match.end() : block_end]

        stat_match = STAT_BLOCK_RE.search(block)
        if stat_match is None:
            print(f"WARNING: no stat block for {name!r}, skipped")
            continue
        slot_raw = clean_text(stat_match.group("slot") or "") or "Ring"
        beschreibung_match = BESCHREIBUNG_RE.search(block, stat_match.end())
        description = None
        if beschreibung_match:
            erschaffung_match = ERSCHAFFUNG_RE.search(block, beschreibung_match.end())
            desc_end = erschaffung_match.start() if erschaffung_match else len(block)
            description = clean_text(block[beschreibung_match.end() : desc_end])
        rows.append(
            {
                "name": name,
                "category": "ring",
                "slot_raw": slot_raw,
                "price_raw": clean_text(stat_match.group("price")),
                "weight_raw": clean_text(stat_match.group("weight")) or "-",
                "description": description,
                "source_url": f"{URL}#{name}",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default="../app/fixtures/imported/ausruestung_ringe_prd_import.json")
    args = parser.parse_args()

    rows = parse_page(fetch_html(URL))
    existing = {r["name"].lower() for r in json.loads(SEED_PATH.read_text(encoding="utf-8"))}
    new_rows = [r for r in rows if r["name"].lower() not in existing]
    print(f"{len(rows)} rings parsed, {len(rows) - len(new_rows)} already in base_items.json, {len(new_rows)} new")

    Path(args.output).write_text(json.dumps(new_rows, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {len(new_rows)} rings to {args.output}")
    for r in new_rows:
        flags = [f for f, bad in (("no-description", r["description"] is None), ("no-price", "GM" not in r["price_raw"])) if bad]
        print(f"  {r['name']} | {r['slot_raw']} | {r['price_raw']}" + (f"  !! {flags}" if flags else ""))


if __name__ == "__main__":
    main()
