"""Fetch every spell's own PRD page (all sourcebooks, not just Grundregelwerk)
and parse its stat block (Zeitaufwand/Komponenten/Reichweite/Ziel-Effekt-
Bereich/Wirkungsdauer/Rettungswurf/Zauberresistenz) plus full prose
description — none of which is in the bulk `/cache/prd_datatable__zauber.txt`
index (see `import_zauber_prd.py`'s docstring and scripts/README.md §2's
pattern for feats, extended here to a more regular, labeled stat block
instead of free prerequisite prose).

Input: `../app/fixtures/imported/zauber_prd_import.json` (§1's bulk import,
all sourcebooks), deduped by id (a spell reprinted across sourcebooks keeps
only its first occurrence, same quirk as talente).

Resumable: if `--output` already exists, ids already present in it are
skipped (not re-fetched) and the new results are merged in — safe to
interrupt and rerun across ~1900 spells' worth of requests.

Each spell page repeats the same `<div id="page" class="page">...` container
as a feat page. Right after the title, the stat block is one labeled line
per field, each its own paragraph (blank-line separated once <br/> is
normalized to \\n), e.g.:

    Schule: Illusion (Einbildung,Fehlgefühl);  Grad: BAR 5, HXM/MAG 6
    Zeitaufwand: 1 Standard-Aktion
    Komponenten: G
    Reichweite: Nah (7,50 m + 1,50 m/2 Stufen)
    Ziel/Effekt: Du/ein illusionärer Doppelgänger
    Wirkungsdauer: 1 Runde/Stufe (A) und Konzentration + 3 Runde (siehe Text)
    Rettungswurf: Nein oder Willen, anzweifeln ...;  Zauberresistenz: Nein

    {free-text description, possibly multiple paragraphs}
    Referenz: GRW - Seite 241

**Known quirks, checked against a 6-spell sample across different schools**
(see chat for the sample): not every field is present on every spell — a
"funktioniert wie X, aber ..." spell (e.g. "Massen-Weisheit der Eule") can
skip Zeitaufwand/Komponenten/Rettungswurf/Zauberresistenz entirely, jumping
straight from Reichweite/Ziel to the prose. The target/effect/area field's
label varies (`Ziel:`, `Effekt:`, `Ziel/Effekt:`, `Bereich:` all occur) —
kept under one `target_or_area` output field regardless of which label was
used. `Rettungswurf:` and `Zauberresistenz:` are usually one line separated
by `;` but parsed as two independent optional fields since a spell missing
one doesn't necessarily miss the other. A trailing `Referenz: {book} - Seite
{n}` line is stripped from the description (redundant with the bulk index's
own `Regelwerk`/`Seite`, already carried over from `import_zauber_prd.py`).

`Komponenten` is kept as the raw PRD string (e.g. "V, G, M/GF (eine
Wasserfläche), F (...)") rather than parsed into `BaseSpellComponent`'s
per-tradition verbal/somatic/material/focus booleans — that table is keyed
by (spell_id, tradition) specifically because arcane/divine versions of the
same spell can differ (M vs GF above), which needs per-spell judgement on
top of the raw text, left for a follow-up build step.

Usage (from backend/scripts, project venv active):
    python fetch_zauber_prd_details.py [-o output.json] [--limit N] [--delay SECONDS]
"""

from __future__ import annotations

import argparse
import json
import re
import time
import urllib.request
from html import unescape
from pathlib import Path

IMPORTED_DIR = Path(__file__).resolve().parent.parent / "app" / "fixtures" / "imported"

PAGE_RE = re.compile(r'<div id="page" class="page">(.*?)<script type="text/javascript">', re.DOTALL)
BR_RE = re.compile(r"<br\s*/?>")
TAG_RE = re.compile(r"<[^>]+>")

LABELS = [
    "Schule",
    "Zeitaufwand",
    "Komponenten",
    "Reichweite",
    "Ziel oder Wirkungsbereich",
    "Ziel/Effekt",
    "Ziel/Bereich",
    "Ziele",
    "Ziel",
    "Effekt",
    "Wirkungsbereich",
    "Bereich",
    "Wirkungsdauer",
    "Rettungswurf",
    "Zauberresistenz",
    "Referenz",
]
# Longest-first so "Ziel/Effekt" matches before the bare "Ziel"/"Effekt" alternatives.
LABELS.sort(key=len, reverse=True)
LABEL_LINE_RE = re.compile(r"^(" + "|".join(re.escape(label) for label in LABELS) + r"):\s*(.*)$")


def fetch_page(prd_id: str) -> str:
    request = urllib.request.Request(
        f"http://prd.5footstep.de/Permalink?page_id={prd_id}",
        headers={"User-Agent": "pathfinder_web-import/1.0"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read().decode("iso-8859-1")


def extract_lines(html: str) -> list[str]:
    match = PAGE_RE.search(html)
    if not match:
        return []
    text = BR_RE.sub("\n", match.group(1))
    text = unescape(TAG_RE.sub("", text).replace("&nbsp;", " "))
    lines = [line.strip() for line in text.split("\n")]
    return [line for line in lines if line]


def parse_stat_block(lines: list[str]) -> dict:
    """Walk lines from the top; each recognized `Label: value` line is
    consumed into `fields`. Stops at the first line that isn't a recognized
    label (start of free-text description) — target/effect fields
    (Ziel/Effekt/Bereich, whichever label the spell used) all collapse into
    one `target_or_area` key."""
    fields: dict[str, str] = {}
    index = 0
    while index < len(lines):
        match = LABEL_LINE_RE.match(lines[index])
        if not match:
            break
        label, value = match.group(1), match.group(2).strip()
        if label in (
            "Ziel oder Wirkungsbereich",
            "Ziel/Effekt",
            "Ziel/Bereich",
            "Ziele",
            "Ziel",
            "Effekt",
            "Wirkungsbereich",
            "Bereich",
        ):
            fields["target_or_area"] = value
        elif label == "Schule":
            school, _, grade = value.partition(";")
            fields["school_text"] = school.strip()
            fields["grade_text"] = grade.replace("Grad:", "").strip()
        elif label == "Rettungswurf" and ";" in value and "Zauberresistenz" in value:
            save_part, _, sr_part = value.partition(";")
            fields["saving_throw"] = save_part.strip()
            fields["spell_resistance"] = sr_part.replace("Zauberresistenz:", "").strip()
        else:
            key = {
                "Zeitaufwand": "casting_time",
                "Komponenten": "components",
                "Reichweite": "range",
                "Wirkungsdauer": "duration",
                "Rettungswurf": "saving_throw",
                "Zauberresistenz": "spell_resistance",
                "Referenz": "reference",
            }[label]
            fields[key] = value
        index += 1

    description_lines = lines[index:]
    # Drop a trailing "Referenz: {book} - Seite {n}" line if the loop above
    # didn't already consume it as part of the stat block (it can appear
    # either right after the header or at the very end of the prose).
    if description_lines and LABEL_LINE_RE.match(description_lines[-1]):
        description_lines = description_lines[:-1]
    fields["full_description"] = "\n\n".join(description_lines).strip()
    return fields


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-o", "--output", default="zauber_prd_details.json")
    parser.add_argument("--limit", type=int, default=None, help="Only fetch the first N spells (for testing)")
    parser.add_argument("--delay", type=float, default=0.2, help="Seconds to sleep between requests")
    args = parser.parse_args()

    imported = json.loads((IMPORTED_DIR / "zauber_prd_import.json").read_text(encoding="utf-8"))

    output_path = Path(args.output)
    existing_results: list[dict] = []
    if output_path.exists():
        existing_results = json.loads(output_path.read_text(encoding="utf-8"))
    already_fetched_ids = {row["id"] for row in existing_results}

    seen_ids: set[str] = set(already_fetched_ids)
    deduped = []
    for row in imported:
        if row["id"] in seen_ids:
            continue
        seen_ids.add(row["id"])
        deduped.append(row)

    if args.limit:
        deduped = deduped[: args.limit]

    results = list(existing_results)
    failures = []
    for i, row in enumerate(deduped, start=1):
        try:
            html = fetch_page(row["prd_id"])
            lines = extract_lines(html)
            # Anchor on the first "Schule:" line rather than the title text:
            # some pages bundle a spell with its "greater" variant under one
            # URL and prepend a WackoWiki "Inhalt" TOC block listing both
            # names before the title repeats (e.g. "Ausspähung" + "Mächtige
            # Ausspähung"), and some page titles don't even match the bulk
            # index's name verbatim (e.g. index "Blind oder Taubheit
            # kurieren" vs. page title "Blind- oder Taubheit kurieren" —
            # same reprint/naming-drift class of quirk as talente). The stat
            # block always starts with "Schule:", so that's a more reliable
            # anchor than either the index name or lines[0]. A page with no
            # "Schule:" line at all (e.g. "Gestalt verändern", a pure
            # links-to-variants page with no stat block of its own) falls
            # through with lines unchanged — same "leave it, don't guess"
            # policy as build_feats_seed.py's unresolved atoms.
            schule_index = next((i for i, line in enumerate(lines) if line.startswith("Schule:")), None)
            if schule_index is not None:
                lines = lines[schule_index:]
            fields = parse_stat_block(lines)
        except Exception as exc:  # noqa: BLE001 - keep going, report at the end
            failures.append((row["name"], row["prd_id"], str(exc)))
            continue

        results.append({"id": row["id"], "name": row["name"], "prd_id": row["prd_id"], **fields})
        if i % 50 == 0 or i == len(deduped):
            print(f"  {i}/{len(deduped)}")
            # Checkpoint periodically so an interrupted run keeps its progress
            # (the resumability described in the module docstring).
            output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        time.sleep(args.delay)

    output_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Wrote {len(results)} spell detail rows to {args.output}")
    if failures:
        print(f"{len(failures)} failures:")
        for name, prd_id, error in failures[:20]:
            print(f"  {name!r} ({prd_id}): {error}")


if __name__ == "__main__":
    main()
