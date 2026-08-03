"""Import the German Pathfinder PRD's weapon tables into a staging JSON file,
one row per weapon, as prep for the `todos.md` "Waffenkatalog ohne
Kampfwerte" item (no `BaseItem` schema field yet for damage/critical/weapon
type, and several standard weapons are missing as catalog rows at all).

Source page (unlike the feat index, this is a single hand-authored wiki page,
not a DataTables JSON endpoint):

    http://prd.5footstep.de/Ausruestungskompendium/WaffenundRuestungen/Waffen

It bundles everything needed in one fetch:
- Four stat tables ("Tabelle: Einfache Waffen" / "Kriegswaffen" / "Exotische
  Waffen" / "Feuerwaffen"), each `<div class="table_wrapper"><table
  class="usertable">` with `<tr class="userrow">`/`<td class="usercell">`
  rows. Two other tables on the same page ("Tabelle: Munition",
  "Tabelle: Feuerwaffenmunition", "Tabelle: Schaden sehr kleiner und großer
  Waffen") are ammunition/scaling reference tables, not per-weapon rows, and
  are deliberately skipped.
- A "Waffenbeschreibungen" prose section giving a `<strong>Name:</strong>
  text` (or, inconsistently, `<strong>Name</strong>: text` with the colon
  *outside* the bold, or `<strong>Name:  </strong>` with trailing whitespace
  *inside* it — both quirks seen on this page and handled by finding each
  `<strong>...</strong>` span first, then resolving the colon's position
  relative to it, rather than requiring `:</strong>` as one literal) entry
  per weapon, matched back to table rows by case/whitespace-normalized name.

This is a staging file, not DB seed data:
- Only the four stat-table columns are structured; `special` is left as
  cleaned free text (may reference weapon qualities defined only in prose
  elsewhere, e.g. "Doppel", "Abwehr").
- `description` is the PRD's per-weapon prose blurb where a name match was
  found; not every table row has one (e.g. table names carrying a quantity
  suffix like "Schuriken (5)", or a handful of genuine name mismatches
  between the table and the prose section, such as "Bolas" vs. the prose
  entry "Bola", or "Zweihändige Axt" vs. the prose heading
  "Zweihändige-Axt") — left `null` rather than guessed. No fuzzy/partial
  matching is attempted beyond case/whitespace normalization.
- No attempt is made to resolve `BaseItem`/weapon-property foreign keys —
  this is a flat, human-reviewable list for scoping that follow-up work.

Usage:
    python import_waffen_prd.py [-o output.json]
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
import uuid
from html import unescape

SOURCE_URL = "http://prd.5footstep.de/Ausruestungskompendium/WaffenundRuestungen/Waffen"

# Stable namespace so re-running the script produces the same weapon ids
# instead of fresh random UUIDs on every run.
NAMESPACE = uuid.UUID("6f3a8c1e-2b7d-4e9a-9c3f-5a1d7e2b4c6a")

TAG_RE = re.compile(r"<[^>]+>")
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)

# (table heading as it appears right before its closing </h4>/</h5>, category
# slug, number of <td class="usercell"> columns for a real weapon row in that
# table). Firearms add Fehlzündung (misfire) and Kapazität (capacity) columns
# ahead of Gewicht, hence the 11 vs. 9 columns.
TABLES = [
    ("Tabelle: Einfache Waffen</h5>", "simple", 9),
    ("Tabelle: Kriegswaffen</h5>", "martial", 9),
    ("Tabelle: Exotische Waffen</h5>", "exotic", 9),
    ("Tabelle: Feuerwaffen</h4>", "firearm", 11),
]

DESCRIPTIONS_START = "Waffenbeschreibungen</h4>"
DESCRIPTIONS_END = "Meisterarbeiten von"


def clean_text(value: str) -> str:
    """Strip HTML tags/entities from a table cell or prose slice, collapsing
    whitespace (including literal `&nbsp;`, which this page uses instead of
    plain spaces almost everywhere) down to single spaces."""
    value = BR_RE.sub(" ", value)
    value = TAG_RE.sub("", value)
    value = value.replace("&nbsp;", " ")
    value = unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def none_if_dash(value: str) -> str | None:
    return value if value not in ("", "-") else None


def parse_price(raw_cell: str) -> tuple[float | None, str | None]:
    """Parse a "Preis" cell. Returns (price_gp, price_raw). price_raw is only
    set when the value couldn't be confidently read as a plain GM amount
    (different currency, e.g. "5 SM"), so it isn't silently mis-parsed."""
    text = clean_text(raw_cell)
    if text in ("", "-"):
        return None, None
    match = re.match(r"^([0-9][0-9.,]*)\s*GM$", text)
    if match:
        number = match.group(1).replace(".", "").replace(",", ".")
        return float(number), None
    return None, text


def fetch_page() -> str:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "pathfinder_web-import/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        html = response.read().decode("iso-8859-1")
    match = re.search(r'<div id="page" class="page">(.*?)<script type="text/javascript">', html, re.DOTALL)
    if not match:
        raise RuntimeError("could not find <div id=\"page\"> content on the fetched page")
    return match.group(1)


def extract_table_html(page: str, heading_marker: str) -> str:
    heading_pos = page.index(heading_marker)
    wrapper_start = page.index('<div class="table_wrapper">', heading_pos)
    table_end = page.index("</table></div>", wrapper_start)
    return page[wrapper_start:table_end]


def parse_weapon_rows(table_html: str, category: str, ncols: int) -> list[dict]:
    rows = re.findall(r'<tr class="userrow">(.*?)</tr>', table_html, re.DOTALL)
    weapons = []
    subgroup: str | None = None
    for row in rows:
        if "<th" in row:
            continue  # header row
        cells = re.findall(r'<td class="usercell"[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(cells) == 1:
            # Either a subgroup marker (<em>Leichte Waffen</em>) or a
            # footnote row (<sup>...) - the latter is skipped outright.
            stripped = cells[0].strip()
            em_match = re.match(r"^<em>(.*?)</em>\s*$", stripped, re.DOTALL)
            if em_match:
                subgroup = clean_text(em_match.group(1))
            continue
        if len(cells) != ncols:
            print(f"  ! unexpected column count ({len(cells)}) in {category} table row, skipping: {row[:120]!r}")
            continue

        if ncols == 9:
            name, price, dmg_s, dmg_m, crit, range_, weight, dmg_type, special = cells
            misfire = capacity = None
        else:  # firearms, 11 columns
            name, price, dmg_s, dmg_m, crit, range_, misfire, capacity, weight, dmg_type, special = cells

        name = clean_text(name)
        if not name:
            continue
        price_gp, price_raw = parse_price(price)

        weapon = {
            "id": str(uuid.uuid5(NAMESPACE, f"prd-weapon-{name}")),
            "name": name,
            "category": category,
            "subgroup": subgroup,
            "price_gp": price_gp,
            "price_raw": price_raw,
            "damage_small": clean_text(dmg_s),
            "damage_medium": clean_text(dmg_m),
            "critical": clean_text(crit),
            "range_ft": clean_text(range_),
            "weight_lb": clean_text(weight),
            "damage_type": clean_text(dmg_type),
            "special": none_if_dash(clean_text(special)),
            "description": None,  # filled in later from Waffenbeschreibungen
        }
        if category == "firearm":
            weapon["misfire"] = none_if_dash(clean_text(misfire)) if misfire is not None else None
            weapon["capacity"] = none_if_dash(clean_text(capacity)) if capacity is not None else None
        weapons.append(weapon)
    return weapons


def parse_descriptions(page: str) -> dict[str, str]:
    """Parse the "Waffenbeschreibungen" prose section into {normalized_name:
    description}. Each entry is introduced by a `<strong>...</strong>` span
    naming the weapon, but the colon separating name from body is
    inconsistently placed - sometimes inside the bold ("Name:"), sometimes
    right after it ("Name</strong>:"), occasionally with stray whitespace
    inside the bold before the colon ("Name:  </strong>"). Matching each
    `<strong>` span first and resolving the colon relative to *that* match
    (rather than requiring the literal sequence `:</strong>`) avoids a
    regex that silently swallows one weapon's description into the next's
    when a page entry doesn't follow the common shape.
    """
    start = page.index(DESCRIPTIONS_START)
    end = page.index(DESCRIPTIONS_END, start)
    section = page[start:end]

    strong_re = re.compile(r"<strong>(.*?)</strong>", re.DOTALL)
    spans = list(strong_re.finditer(section))

    descriptions: dict[str, str] = {}
    for i, span in enumerate(spans):
        name_raw = span.group(1).strip()
        pos = span.end()
        if name_raw.endswith(":"):
            name_raw = name_raw[:-1]
        else:
            rest = section[pos:]
            stripped = rest.lstrip()
            if stripped.startswith(":"):
                pos += (len(rest) - len(stripped)) + 1
        name = clean_text(name_raw)
        text_end = spans[i + 1].start() if i + 1 < len(spans) else len(section)
        text = clean_text(section[pos:text_end])
        if name:
            descriptions[name.lower()] = text
    return descriptions


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-o",
        "--output",
        default="waffen_prd_import.json",
        help="Output path for the staging JSON file (default: %(default)s)",
    )
    args = parser.parse_args()

    page = fetch_page()

    weapons: list[dict] = []
    for heading_marker, category, ncols in TABLES:
        table_html = extract_table_html(page, heading_marker)
        weapons.extend(parse_weapon_rows(table_html, category, ncols))

    descriptions = parse_descriptions(page)
    matched = 0
    for weapon in weapons:
        text = descriptions.get(weapon["name"].lower())
        if text:
            weapon["description"] = text
            matched += 1

    weapons.sort(key=lambda w: w["name"])

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(weapons, f, ensure_ascii=False, indent=2)

    by_category: dict[str, int] = {}
    for w in weapons:
        by_category[w["category"]] = by_category.get(w["category"], 0) + 1
    print(f"Wrote {len(weapons)} weapons to {args.output}")
    print("By category:", ", ".join(f"{k}={v}" for k, v in by_category.items()))
    print(f"Descriptions matched: {matched}/{len(weapons)} ({len(weapons) - matched} without a match)")
    print(f"Description entries parsed from prose section: {len(descriptions)}")


if __name__ == "__main__":
    main()
