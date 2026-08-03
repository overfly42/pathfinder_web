"""Import the German Pathfinder PRD's adventuring gear and tools tables into
a staging JSON file, one row per item, as prep work alongside
`import_waffen_prd.py` for the `todos.md` equipment-catalog item (see that
script's docstring for the weapon side of the same effort).

Source pages:

    http://prd.5footstep.de/Ausruestungskompendium/Ausruestung/Abenteuerausruestung  (gear,  ~252 rows)
    http://prd.5footstep.de/Ausruestungskompendium/Ausruestung/Werkzeuge             (tools, ~43 rows)

Both are a single `<div class="table_wrapper"><table class="usertable">`
with the same three columns (Gegenstand/Preis/Gewicht), `<tr
class="userrow">`/`<td class="usercell">` rows - the same shape as the
weapon tables in `import_waffen_prd.py`, just without a `damage`-style
column set.

Unlike the weapon page, neither of these pages has a prose description
section anywhere on them (no "...beschreibungen" `<h4>`) - each item's actual
rule text only exists on that item's own permalink page, e.g.
`http://prd.5footstep.de/Expertenregeln/Ausruestung/Abakus`. That's ~295
additional HTTP requests to a third-party wiki. Per this project's own
documented convention for the feat catalog (`README.md` §2: bulk-fetching
full text for all 1506 feats "hasn't been done - only worth it if/when full
rule text is actually needed catalog-wide"), the same call is made here: this
script only parses the summary table (name, price, weight, category) and
keeps each row's own permalink URL as `source_url`, so a description can be
fetched on demand later - exactly the two-step workflow §2 documents for
feats (bulk index now, full text per-item when a handler/description is
actually being written).

This is a staging file, not DB seed data - no attempt is made to resolve
`BaseItem` foreign keys or normalize price/weight beyond what's described
below.

Usage:
    python import_ausruestung_prd.py [-o output.json]
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
import uuid
from html import unescape

SOURCES = [
    ("http://prd.5footstep.de/Ausruestungskompendium/Ausruestung/Abenteuerausruestung", "gear"),
    ("http://prd.5footstep.de/Ausruestungskompendium/Ausruestung/Werkzeuge", "tool"),
]

# Stable namespace so re-running the script produces the same item ids
# instead of fresh random UUIDs on every run.
NAMESPACE = uuid.UUID("9d2b6a4e-7c1f-4a8e-b3d5-2e6f9a1c8b0d")

TAG_RE = re.compile(r"<[^>]+>")
HREF_RE = re.compile(r'href="([^"]+)"')


def clean_text(value: str) -> str:
    value = TAG_RE.sub("", value)
    value = value.replace("&nbsp;", " ")
    value = unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def parse_price(raw_cell: str) -> tuple[float | None, str | None]:
    """Same GM-only parsing as import_waffen_prd.py: returns (price_gp,
    price_raw), where price_raw is only set when the amount isn't a plain
    GM value (e.g. "5 SM"), so a different currency is never silently
    misread as gold."""
    text = clean_text(raw_cell)
    if text in ("", "-"):
        return None, None
    match = re.match(r"^([0-9][0-9.,]*)\s*GM$", text)
    if match:
        number = match.group(1).replace(".", "").replace(",", ".")
        return float(number), None
    return None, text


def fetch_page(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "pathfinder_web-import/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        html = response.read().decode("iso-8859-1")
    match = re.search(r'<div id="page" class="page">(.*?)<script type="text/javascript">', html, re.DOTALL)
    if not match:
        raise RuntimeError(f"could not find <div id=\"page\"> content on {url}")
    return match.group(1)


def extract_table_html(page: str) -> str:
    wrapper_start = page.index('<div class="table_wrapper">')
    table_end = page.index("</table></div>", wrapper_start)
    return page[wrapper_start:table_end]


def parse_item_rows(table_html: str, category: str) -> list[dict]:
    rows = re.findall(r'<tr class="userrow">(.*?)</tr>', table_html, re.DOTALL)
    items = []
    for row in rows:
        if "<th" in row:
            continue  # header row
        cells = re.findall(r'<td class="usercell"[^>]*>(.*?)</td>', row, re.DOTALL)

        if len(cells) == 1:
            continue  # footnote row (colspan across all columns)

        name_cell = cells[0]
        name = clean_text(name_cell)
        if not name:
            continue
        href_match = HREF_RE.search(name_cell)
        source_url = href_match.group(1) if href_match else None

        if len(cells) == 3:
            price_cell, weight_cell = cells[1], cells[2]
        elif len(cells) == 2:
            # One-off shape seen on the gear page ("Schloss"): price and
            # weight columns merged into a single colspan="2" cell holding
            # only a weight value (no price given). Can't be split back
            # into two values, so keep whichever unit the merged cell
            # actually shows and leave the other null.
            merged = clean_text(cells[1])
            if "Pfd." in merged:
                price_cell, weight_cell = "-", cells[1]
            else:
                price_cell, weight_cell = cells[1], "-"
        else:
            print(f"  ! unexpected column count ({len(cells)}) in {category} table row, skipping: {row[:120]!r}")
            continue

        price_gp, price_raw = parse_price(price_cell)
        weight_lb = clean_text(weight_cell)

        items.append(
            {
                "id": str(uuid.uuid5(NAMESPACE, f"prd-item-{category}-{name}")),
                "name": name,
                "category": category,
                "price_gp": price_gp,
                "price_raw": price_raw,
                "weight_lb": weight_lb if weight_lb not in ("", "-") else None,
                "source_url": source_url,
            }
        )
    return items


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        default="ausruestung_prd_import.json",
        help="Output path for the staging JSON file (default: %(default)s)",
    )
    args = parser.parse_args()

    items: list[dict] = []
    for url, category in SOURCES:
        page = fetch_page(url)
        table_html = extract_table_html(page)
        rows = parse_item_rows(table_html, category)
        items.extend(rows)
        print(f"{category}: parsed {len(rows)} rows from {url}")

    items.sort(key=lambda i: (i["category"], i["name"]))

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)

    by_category: dict[str, int] = {}
    for i in items:
        by_category[i["category"]] = by_category.get(i["category"], 0) + 1
    print(f"Wrote {len(items)} items to {args.output}")
    print("By category:", ", ".join(f"{k}={v}" for k, v in by_category.items()))


if __name__ == "__main__":
    main()
