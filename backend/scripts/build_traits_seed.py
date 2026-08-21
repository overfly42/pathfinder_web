"""Builds `../app/fixtures/seed/base_traits.json` — the full `BaseTrait`
catalog (PF1e background traits) from the PRD's Wesenszüge page:

    http://prd.5footstep.de/AusbauregelnIVKampagnen/Charakterhintergrund/Wesenszuege

Replaces the 10 hand-written placeholder traits that shipped with
`trait_seed.py` (one generic "+1 to a skill" example per area, none of them
actual PF1e traits) with the ~220 real ones from the source page.

Same fetch+parse-directly-into-seed shape as `build_conditions_seed.py` (no
cross-catalog resolution needed, so no `app/fixtures/imported/` staging
file). Same `<div id="page" class="page">...<script>var dbclick` content
container as every other PRD page (see `scripts/README.md` §2/§6).

**Parsing quirk**: each category/race subsection opens with an intro
paragraph (e.g. "Nur Elfen können diese Wesenszüge wählen:") whose `<p>`
never closes before the first trait's own nested `<p>` starts — WackoWiki
emits invalid nested `<p>` tags here. A naive `<p ...>(.*?)</p>` match
anchored with `re.match(r'...<strong>...')` from the body's start therefore
silently drops the *first* trait of every subsection (its `<strong>` isn't
at the start of the match — the intro sentence is). Fixed by `re.search`ing
for the first `<strong>...</strong>` anywhere in the paragraph body instead
of requiring it at the start; text before it (the intro sentence, if any) is
simply not part of any trait's own name/description.

`area` mirrors `BaseTrait`'s docstring convention (a plain categorization
tag, load-bearing for the one-trait-per-area cap in
`routers/characters.py`). The site's four "Grundwesenszüge" groups map
directly (Glaube→faith, Kampf→combat, Magie→magic, Sozial→social);
"Wesenszüge (Regional)" reuses the pre-existing "region" tag. Two new tags
are introduced here: "religion" for "Wesenszüge (Religion)" (deity/alignment
-specific traits — a distinct trait type from the four base ones per PF1e's
Additional Traits/Ultimate Campaign rules, not a Glaube subtype) and "race"
for "Wesenszüge (Volk)" (the per-race subsections, plus the sibling
"Blutlinie" bloodline-heritage subsection — not race-restricted itself, but
grouped with the race traits on the source page and conceptually about
ancestry).

`BaseTrait` has no field for "only choosable by race X" — the 7 per-race
subsections (not Blutlinie, which explicitly allows "Angehörige jedes
Volkes") each state that restriction only once, in their own intro sentence,
not per trait. Preserved by prefixing each such trait's description with
"(Nur für {Rasse} wählbar.)" rather than silently dropping it.

**Known source quirk, left as-is**: at least two entries have a stray
literal space baked into the raw HTML mid-word ("Überwäl tigen", "Bef le
ckung") — a site typo, not a parsing artifact; verified in the raw fetched
bytes. Not auto-corrected (same "transcribe faithfully, don't guess-fix
prose" policy as the rest of `scripts/README.md`).

Ids are deterministic (`uuid5` off the trait's own name, `ID_NAMESPACE`
below), so reruns upsert cleanly via `app.seed.trait_seed` instead of
minting duplicates. The 10 previous placeholder ids are intentionally not
reconciled — nothing outside `base_traits.json` itself referenced them (no
`character_traits` row, no test, no other fixture), so this seed's rerun
fully replaces the file's contents rather than merging into the old rows.

Usage:
    cd backend && python scripts/build_traits_seed.py
"""

from __future__ import annotations

import json
import re
import urllib.request
import uuid
from html import unescape
from pathlib import Path

SOURCE_URL = "http://prd.5footstep.de/AusbauregelnIVKampagnen/Charakterhintergrund/Wesenszuege"
OUTPUT_PATH = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "seed" / "base_traits.json"

ID_NAMESPACE = uuid.UUID("7d3c9a6e-4b1f-4e2a-9c5d-6a1f3e9c7d3c")

TAG_RE = re.compile(r"<[^>]+>")
BR_RE = re.compile(r"<br\s*/?>")
PAGE_RE = re.compile(r'<div id="page" class="page">(.*?)<script type="text/javascript">', re.DOTALL)
HEADER_SPLIT_RE = re.compile(r"(<h[3-5][^>]*>.*?</h[3-5]>)", re.DOTALL)
HEADER_RE = re.compile(r"<h([3-5])[^>]*>(.*?)</h\1>", re.DOTALL)
PARAGRAPH_RE = re.compile(r'<p class="auto" id="[^"]*">(.*?)</p>', re.DOTALL)
STRONG_RE = re.compile(r"<strong>(.*?)</strong>\s*:?\s*(.*)", re.DOTALL)

# Category path (as it appears in the page's own headers) -> BaseTrait.area.
# Path is matched by its last (most specific) header text.
AREA_BY_CATEGORY = {
    "Grundwesenszüge (Glaube)": "faith",
    "Grundwesenszüge (Kampf)": "combat",
    "Grundwesenszüge (Magie)": "magic",
    "Grundwesenszüge (Sozial)": "social",
    "Wesenszüge (Regional)": "region",
    "Wesenszüge (Religion)": "religion",
}
# Everything under "Wesenszüge (Volk)" (per-race subsections + "Blutlinie").
RACE_SUBSECTION_AREA = "race"
# Per-race subsections that carry a "Nur {Rasse} können diese Wesenszüge
# wählen" restriction (Blutlinie deliberately excluded — it states the
# opposite: any race may take a bloodline trait).
RACE_RESTRICTED_SECTIONS = {"Elfen", "Gnome", "Halb-Elfen", "Halblinge", "Halb-Orks", "Menschen", "Zwerge"}


def strip_tags(value: str) -> str:
    value = BR_RE.sub("\n", value)
    value = TAG_RE.sub("", value)
    value = unescape(value.replace("&nbsp;", " "))
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n\s*\n+", "\n", value)
    return value.strip()


def fetch_page(url: str) -> str:
    # The site's own headers (and scripts/README.md's general guidance) say
    # iso-8859-1, but this page's prose actually contains cp1252-only bytes
    # (German „curly quotes", 0x84/0x93) that strict iso-8859-1 turns into
    # C1 control characters instead of decoding them — verified against the
    # raw response bytes for "„niederer"" in "Eifernder Krieger". cp1252 is a
    # superset of iso-8859-1 for every byte this site otherwise uses, so this
    # is strictly a fix, not a behavior change, for content that stays within
    # true iso-8859-1.
    request = urllib.request.Request(url, headers={"User-Agent": "pathfinder_web-import/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("cp1252")


def parse_traits(html: str) -> list[dict]:
    page = PAGE_RE.search(html).group(1)
    parts = HEADER_SPLIT_RE.split(page)

    path: list[tuple[int, str]] = []
    entries: list[dict] = []
    for part in parts:
        header_match = HEADER_RE.match(part) if part else None
        if header_match:
            level = int(header_match.group(1))
            text = strip_tags(header_match.group(2))
            path = [step for step in path if step[0] < level] + [(level, text)]
            continue

        category = path[-1][1] if path else ""
        area = AREA_BY_CATEGORY.get(category)
        race_restriction = None
        if area is None and any(step[1] == "Wesenszüge (Volk)" for step in path):
            area = RACE_SUBSECTION_AREA
            if category in RACE_RESTRICTED_SECTIONS:
                race_restriction = category
        if area is None:
            continue

        for paragraph_match in PARAGRAPH_RE.finditer(part):
            strong_match = STRONG_RE.search(paragraph_match.group(1))
            if not strong_match:
                continue
            name = strip_tags(strong_match.group(1)).rstrip(":").strip()
            description = strip_tags(strong_match.group(2)).strip()
            if not name or not description:
                continue
            if race_restriction:
                description = f"(Nur für {race_restriction} wählbar.) {description}"
            entries.append({"name": name, "description": description, "area": area})

    return entries


def main() -> None:
    html = fetch_page(SOURCE_URL)
    entries = parse_traits(html)

    seen_names = set()
    for entry in entries:
        if entry["name"] in seen_names:
            raise ValueError(f"duplicate trait name parsed: {entry['name']!r}")
        seen_names.add(entry["name"])

    rows = [
        {"id": str(uuid.uuid5(ID_NAMESPACE, entry["name"])), **entry}
        for entry in entries
    ]
    OUTPUT_PATH.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows)} traits to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
