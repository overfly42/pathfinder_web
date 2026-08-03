"""Import the German Pathfinder PRD's named weapon special-ability list into a
staging JSON file, one row per ability, as prep for roadmap.md's "Magische
Verzauberung/Material als Berechnung statt Freitext" item (`CharacterGear
.properties` today is freetext, can't carry `bonus_equivalent`/category/
mutual-exclusion structure).

Source page (same "hand-authored wiki page" shape as
`import_waffen_prd.py`'s weapon tables, see that script's/`scripts/README.md`'s
§5 for the general table-parsing approach):

    http://prd.5footstep.de/Ausruestungskompendium/MagischeWaffenundRuestungen/BesondereEigenschaftenvonWaffen

Two shapes on this one page feed this script:

1. Three percentile-roll tables ("Tabelle: Besondere Eigenschaften von
   Nahkampfwaffen/Fernkampfwaffen/Munition"), each split into `<th
   class="userhead">BESONDERE WAFFENEIGENSCHAFT +N [ODER +M]</th>` sub-
   sections (a treasure-roll table, not descriptive prose) — this is the
   *only* structured source for which of the three weapon categories a named
   ability applies to, and its `bonus_equivalent` (1-5, needed for the PF1e
   "+10 total bonus" cap and price formula). The section header's own tier
   (e.g. "+3 ODER +4") is not authoritative by itself since it can span two
   tiers; each row's own "MODIFIKATOR FÜR DEN GRUNDPREIS" cell disambiguates
   ("+3 Bonus" vs "+4 Bonus") except for a handful of flat-gold-price rows
   (e.g. "Undurchdringbar", "+3.000 GM") that don't restate the tier at all —
   for those the (unambiguous, single-tier) section header is used instead;
   a row under a *dual*-tier header with a flat price is left with
   `bonus_equivalent: null` rather than guessed (two observed: "Duell",
   "Selbstverwandelnd", both under "+4 ODER +5").

   A row's name cell may carry a `<sup><a href="#oftndN">N</a></sup>`
   footnote marker; footnote *1* is always the same table-wide boilerplate
   ("add this to the base bonus-price table") and carries no per-ability
   information, so it's dropped. Footnotes 2+ are real per-ability
   restrictions/exclusions (e.g. "Nur Wuchtwaffen.") and become
   `restriction_note`. Each table resets its own footnote numbering
   (`ftnd1`, `ftnd2`, ... start over per table), so footnote text is resolved
   per table, not globally.

2. A single unbroken prose section after the third table, one `<p>` per
   ability in alphabetical order (*not* the tables' roll order), each
   anchored `<a name="{AnchorName}" href="#{AnchorName}" class="anchor">`
   immediately before a `<strong>{Label}:</strong> {full rule text}`
   paragraph (or, inconsistently, `<strong>{Label}</strong>:` with the colon
   *outside* the bold — same quirk `import_waffen_prd.py` documents for the
   weapons page, handled the same way: resolve the colon's position relative
   to the `<strong>` tag rather than assuming one form). `{Label}` is the
   natural-spacing name ("Geisterhafte Berührung") and isn't cross-checked
   against `{AnchorName}` — the two often differ (see below), so the anchor
   boundary alone (this entry ends where the next anchor starts) is what
   isolates each entry's text, not a name match.

   `{AnchorName}` itself doesn't always match a table row's name string
   directly: most are exact or plain space->hyphen (`Strahlendes Licht` ->
   `Strahlendes-Licht`), but every "Mächtig(e/es) X" / "Schwach X" qualified
   name is anchored word-order-reversed instead (`Mächtige Verlässlichkeit`
   -> `Verlässlichkeit-Mächtige`), apparently filed under the base ability's
   own anchor group. `resolve_description()` tries direct name, hyphenated,
   and (for two-word names) word-order-reversed, case-insensitively. Three
   table names ("Schock", "Zerschlagend", "Zorngeboren") have no matching
   anchor under any of these forms — genuinely missing a prose entry on this
   page, not a matching bug — left with `description: null` rather than
   fuzzy-matched, same "don't guess" policy as `import_waffen_prd.py`.

A name can appear in more than one of the three tables (most melee/ranged
abilities do; ammunition-only and category-exclusive ones don't) — rows are
merged by name into one record with the union of categories. If two tables
disagree on `bonus_equivalent`/price for the same name (not observed as of
this writing), both raw values are kept in `price_modifier` joined by "; "
and `bonus_equivalent` is left as the first value seen, flagged via
`bonus_equivalent_conflict: true` for manual review rather than silently
picking one.

This is a staging file, not DB seed data — see `build_weapon_abilities_seed.py`
for the transform into `../app/fixtures/seed/base_weapon_special_abilities.json`.

Usage:
    python import_waffeneigenschaften_prd.py [-o output.json]
"""

from __future__ import annotations

import argparse
import json
import re
import urllib.request
from dataclasses import dataclass, field
from html import unescape

SOURCE_URL = (
    "http://prd.5footstep.de/Ausruestungskompendium/MagischeWaffenundRuestungen/BesondereEigenschaftenvonWaffen"
)

TAG_RE = re.compile(r"<[^>]+>")
BR_RE = re.compile(r"<br\s*/?>", re.IGNORECASE)

TABLES = [
    ("Tabelle: Besondere Eigenschaften von&nbsp;Nahkampfwaffen</h3>", "melee"),
    ("Tabelle: Besondere Eigenschaften von&nbsp;Fernkampfwaffen</h3>", "ranged"),
    ("Tabelle: Besondere Eigenschaften von&nbsp;Munition</h3>", "ammunition"),
]

DESCRIPTIONS_START_MARKER = "muss mindestens einen Verbesserungsbonus von&nbsp;+1 besitzen.</p>"

SECTION_HEADER_RE = re.compile(r"BESONDERE WAFFENEIGENSCHAFT \+(\d)(?:\s*ODER\s*\+(\d))?", re.IGNORECASE)
ROW_RE = re.compile(
    r'<tr class="userrow"><td class="usercell">[^<]*</td>'
    r'<td class="usercell">(?P<name>[^<]*?)\s*(?:<sup><a href="#oftnd(?P<footnote>\d+)"[^>]*>\d+</a></sup>\s*)?</td>'
    r'<td class="usercell">(?P<price>[^<]*)</td></tr>'
)
FOOTNOTE_DEF_RE = re.compile(
    r'<sup><a href="#ftnd(?P<num>\d+)" name="oftnd\d+">\d+</a></sup>\s*(?P<text>.*?)</td></tr>'
)
ANCHOR_RE = re.compile(r'<a name="(?P<name>[^"]+)" href="#(?P=name)" class="anchor" title=""></a>')
STRONG_RE = re.compile(r"<strong>(?P<text>.*?)</strong>", re.DOTALL)

# Observed site quirks in the table rows' name cells, fixed up before
# anchor/description matching (not fuzzy-matched, per scripts/README.md §5's
# "left null rather than guessed" policy — these are the two *specific*,
# manually-verified cases found, not a general fuzzy pass):
# - "Hinrichtung3": a footnote digit glued directly onto the name with no
#   `<sup>` wrapper at all (every other footnoted row uses a real `<sup>`),
#   so the generic sup-stripping in the table-row regex doesn't catch it.
# - "Auflammen": a plain typo for "Aufflammen" (missing the second f) — the
#   Nahkampf table spells it correctly, Fernkampf/Munition don't.
NAME_FIXES = {"Hinrichtung3": "Hinrichtung", "Auflammen": "Aufflammen"}


def clean_text(value: str) -> str:
    value = BR_RE.sub(" ", value)
    value = TAG_RE.sub("", value)
    value = value.replace("&nbsp;", " ")
    value = unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def fetch_html() -> str:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("iso-8859-1")


def parse_bonus(price_raw: str) -> int | None:
    match = re.match(r"^\+(\d) Bonus$", price_raw)
    return int(match.group(1)) if match else None


@dataclass
class AbilityRow:
    name: str
    categories: set[str] = field(default_factory=set)
    bonus_equivalent: int | None = None
    bonus_equivalent_conflict: bool = False
    price_modifiers: list[str] = field(default_factory=list)
    restriction_notes: list[str] = field(default_factory=list)


def parse_table(html: str, header_marker: str, category: str, rows: dict[str, AbilityRow]) -> None:
    start = html.index(header_marker) + len(header_marker)
    end = html.index("</table>", start)
    chunk = html[start:end]

    # Footnote definitions live in their own trailing colspan row(s), same
    # chunk, after every data row — collect them first so row parsing below
    # can resolve a footnote number to text regardless of order.
    footnotes = {int(m.group("num")): clean_text(m.group("text")) for m in FOOTNOTE_DEF_RE.finditer(chunk)}

    current_tiers: list[int] = []
    for line in chunk.split("<tr"):
        line = "<tr" + line
        header_match = SECTION_HEADER_RE.search(line)
        if header_match:
            current_tiers = [int(g) for g in header_match.groups() if g]
            continue

        row_match = ROW_RE.search(line)
        if not row_match:
            continue
        name = clean_text(row_match.group("name"))
        if not name:
            continue
        name = NAME_FIXES.get(name, name)
        price_raw = clean_text(row_match.group("price"))

        row = rows.setdefault(name, AbilityRow(name=name))
        row.categories.add(category)
        if price_raw not in row.price_modifiers:
            row.price_modifiers.append(price_raw)

        bonus = parse_bonus(price_raw)
        if bonus is None and len(current_tiers) == 1:
            bonus = current_tiers[0]
        if bonus is not None:
            if row.bonus_equivalent is None:
                row.bonus_equivalent = bonus
            elif row.bonus_equivalent != bonus:
                row.bonus_equivalent_conflict = True

        footnote_num = row_match.group("footnote")
        if footnote_num and int(footnote_num) >= 2:
            text = footnotes.get(int(footnote_num))
            if text and text not in row.restriction_notes:
                row.restriction_notes.append(text)


def parse_descriptions(html: str) -> dict[str, str]:
    start = html.index(DESCRIPTIONS_START_MARKER) + len(DESCRIPTIONS_START_MARKER)
    chunk = html[start:]

    anchors = list(ANCHOR_RE.finditer(chunk))
    descriptions: dict[str, str] = {}
    for i, anchor in enumerate(anchors):
        name = anchor.group("name")
        entry_end = anchors[i + 1].start() if i + 1 < len(anchors) else len(chunk)

        # Name label sits in the first <strong> after the anchor, either as
        # "<strong>Name:</strong>" or "<strong>Name</strong>:" — resolve the
        # colon's position relative to the tag instead of assuming one form
        # (see scripts/README.md §5's identical quirk on the weapons page).
        # Not cross-checked against the anchor's own name: the anchor is
        # hyphenated (`Geisterhafte-Berührung`) while the <strong> label
        # keeps the natural spacing (`Geisterhafte Berührung`), so a strict
        # equality check would reject nearly every multi-word entry — the
        # one-block-per-anchor boundary above is enough to isolate the right
        # <strong>.
        strong = STRONG_RE.search(chunk, anchor.end(), entry_end)
        if strong is None:
            continue
        text_start = strong.end()
        if chunk[text_start : text_start + 1] == ":":
            text_start += 1
        descriptions[name] = clean_text(chunk[text_start:entry_end])
    return descriptions


def resolve_description(name: str, descriptions_by_slug: dict[str, str]) -> str | None:
    """Matches a table row's name against the prose section's anchors, which
    aren't always the same string: most are exact or plain space->hyphen
    (`Strahlendes Licht` -> `Strahlendes-Licht`), but every "Mächtig(e/es) X"
    / "Schwach X" qualified name is anchored word-order-reversed instead
    (`Mächtige Verlässlichkeit` -> `Verlässlichkeit-Mächtige`, `Schwach
    markierend` -> `Markierend-Schwach`) — apparently grouped under the base
    ability's own anchor on the site. Tried case-insensitively since a few
    anchors also differ from the table only in capitalization
    (`Ki-steigernd` -> `Ki-Steigernd`)."""
    candidates = [name, name.replace(" ", "-")]
    words = name.split(" ")
    if len(words) == 2:
        candidates.append(f"{words[1]}-{words[0]}")
    for candidate in candidates:
        text = descriptions_by_slug.get(candidate.lower())
        if text is not None:
            return text
    return None


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("-o", "--output", default="../app/fixtures/imported/waffeneigenschaften_prd_import.json")
    args = parser.parse_args()

    html = fetch_html()

    rows: dict[str, AbilityRow] = {}
    for header_marker, category in TABLES:
        parse_table(html, header_marker, category, rows)

    descriptions = parse_descriptions(html)
    descriptions_by_slug = {k.lower(): v for k, v in descriptions.items()}

    result = []
    for name, row in sorted(rows.items()):
        result.append(
            {
                "name": name,
                "categories": sorted(row.categories),
                "bonus_equivalent": row.bonus_equivalent,
                "bonus_equivalent_conflict": row.bonus_equivalent_conflict,
                "price_modifier": "; ".join(row.price_modifiers),
                "restriction_note": " ".join(row.restriction_notes) or None,
                "description": resolve_description(name, descriptions_by_slug),
                "source_url": f"{SOURCE_URL}#{name}",
            }
        )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    missing_description = [r["name"] for r in result if r["description"] is None]
    print(f"Wrote {len(result)} abilities to {args.output}")
    if missing_description:
        print(f"{len(missing_description)} without a matched description: {missing_description}")
    conflicts = [r["name"] for r in result if r["bonus_equivalent_conflict"]]
    if conflicts:
        print(f"{len(conflicts)} with a bonus_equivalent conflict across tables: {conflicts}")


if __name__ == "__main__":
    main()
