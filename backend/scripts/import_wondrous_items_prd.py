"""Import the German Pathfinder PRD's wondrous-item and ring catalogs into a
staging JSON file, as prep for roadmap.md's "Wondrous-Item-Katalog mit echter
Attributsboni-Wirkung" (decided 2026-08-04).

Source pages:

    http://prd.5footstep.de/Grundregelwerk/MagischeGegenstaende/WundersameGegenstaende (~177 items)
    http://prd.5footstep.de/Grundregelwerk/MagischeGegenstaende/MagischeRinge          (~38 items)

Unlike `import_waffeneigenschaften_prd.py`'s source page, both of these are
UTF-8 encoded, not ISO-8859-1 (this site is inconsistent per-page about
encoding, see roadmap.md's "Class source-page fetch/preprocess tooling"
item) - `fetch_html()` tries UTF-8 first and falls back to ISO-8859-1.

Each item is one `<h5><span class="cl-stat-block-title">{Name}</span></h5>`
block, followed by a stat-block paragraph (`Aura`/`ZS`/`Ausrüstungsplatz`/
`Preis`/`Gewicht`), then `BESCHREIBUNG` prose, then `ERSCHAFFUNG`
(Voraussetzungen/Kosten - not imported, this app doesn't model item
crafting). `ZS`/`Aura` are also not imported - out of scope for a quick
player-facing lookup, see roadmap.md's decision.

Known, deliberate gap: "Ionensteine" on the wondrous-items page is a
~20-row price table of individually named ioun-stone variants, not its own
set of `<h5>` blocks - it imports as a single generic row (whole table
folded into `description`) rather than 20 separate catalog rows, same
"don't guess, don't build a one-off table parser for a single page section"
call as `import_waffeneigenschaften_prd.py`'s handling of edge cases.

This is a staging file, not DB seed data - see `build_wondrous_items_seed.py`
for the transform into `base_items.json` rows (slot-name mapping, price
parsing, and the attribute-bonus-item tier split).

Usage:
    python import_wondrous_items_prd.py [-o output.json]
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from html import unescape

SOURCES = [
    ("http://prd.5footstep.de/Grundregelwerk/MagischeGegenstaende/WundersameGegenstaende", "wondrous"),
    ("http://prd.5footstep.de/Grundregelwerk/MagischeGegenstaende/MagischeRinge", "ring"),
]

TAG_RE = re.compile(r"<[^>]+>")
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)
END_MARKER_RE = re.compile(r'<script type="text/javascript">|<footer id="footer"')

TITLE_RE = re.compile(r'<h5><span class="cl-stat-block-title">(?P<name>.*?)</span></h5>')
STAT_BLOCK_RE = re.compile(
    r"<strong>Ausrüstungsplatz</strong>\s*(?P<slot>.*?);\s*"
    r"<strong>Preis</strong>\s*(?P<price>.*?);\s*"
    r"<strong>Gewicht</strong>\s*(?P<weight>.*?)</p>",
    re.DOTALL,
)
BESCHREIBUNG_RE = re.compile(r"<strong>BESCHREIBUNG</strong></p>.*?<hr\s*/?>", re.DOTALL)
ERSCHAFFUNG_RE = re.compile(r"<strong>ERSCHAFFUNG</strong></p>")


def clean_text(value: str) -> str:
    value = BR_RE.sub(" ", value)
    value = TAG_RE.sub("", value)
    value = value.replace("&nbsp;", " ")
    value = unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def fetch_html(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read()
    try:
        return raw.decode("utf-8")
    except UnicodeDecodeError:
        return raw.decode("iso-8859-1")


def parse_page(html: str, url: str, category: str) -> list[dict]:
    end_match = END_MARKER_RE.search(html)
    content = html[: end_match.start()] if end_match else html

    titles = list(TITLE_RE.finditer(content))
    rows = []
    for i, title_match in enumerate(titles):
        name = clean_text(title_match.group("name"))
        block_start = title_match.end()
        block_end = titles[i + 1].start() if i + 1 < len(titles) else len(content)
        block = content[block_start:block_end]

        stat_match = STAT_BLOCK_RE.search(block)
        if stat_match is None:
            # No stat block at all -> not an item entry (stray anchor/heading).
            continue
        slot_raw = clean_text(stat_match.group("slot"))
        price_raw = clean_text(stat_match.group("price"))
        weight_raw = clean_text(stat_match.group("weight"))

        beschreibung_match = BESCHREIBUNG_RE.search(block, stat_match.end())
        description = None
        if beschreibung_match:
            erschaffung_match = ERSCHAFFUNG_RE.search(block, beschreibung_match.end())
            desc_end = erschaffung_match.start() if erschaffung_match else len(block)
            description = clean_text(block[beschreibung_match.end() : desc_end])

        rows.append(
            {
                "name": name,
                "category": category,
                "slot_raw": slot_raw,
                "price_raw": price_raw,
                "weight_raw": weight_raw,
                "description": description,
                "source_url": f"{url}#{name}",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default="../app/fixtures/imported/wondrous_items_prd_import.json")
    args = parser.parse_args()

    result: list[dict] = []
    for url, category in SOURCES:
        html = fetch_html(url)
        rows = parse_page(html, url, category)
        print(f"{category}: {len(rows)} items from {url}")
        result.extend(rows)

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    missing_description = [r["name"] for r in result if r["description"] is None]
    print(f"Wrote {len(result)} items to {args.output}")
    if missing_description:
        print(f"{len(missing_description)} without a matched description: {missing_description}")


if __name__ == "__main__":
    main()
