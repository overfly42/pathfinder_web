# PRD (prd.5footstep.de) data extraction

Notes on how to pull rule data — feats first, but the same techniques apply
to spells/traits/etc. — off the German Pathfinder Reference Document at
`prd.5footstep.de`, for implementing `rules/*.py` `HANDLERS` one feat at a
time (per `CLAUDE.md`'s composition-vs-computation split: the catalog rows
are data, `HANDLERS[ability_id]` is where the mechanical effect gets coded).

The site is a WackoWiki. Two shapes of page matter here: **index pages**
(machine-readable JSON behind a DataTables widget) and **content pages**
(hand-written prose, no structured data at all — has to be parsed by
convention, not by schema).

Fetch everything over **plain `http://`**, not https — the cert doesn't
cover this hostname. Response encoding is `iso-8859-1`, not UTF-8, so decode
accordingly (`response.read().decode("iso-8859-1")` when using
`urllib.request`, or unavoidable mangled umlauts on a JSON string but decode
still needed).

## 1. Bulk feat index → short summaries for all 1506 feats

`/TalentIndex` itself renders an *empty* `<table>` and fills it client-side
via DataTables. Don't scrape that page — go straight to its data source:

```
http://prd.5footstep.de/cache/prd_datatable__talente.txt
```

This is plain JSON: `{"data": [{"ID", "Name", "Art", "Beschreibung",
"Voraussetzung", "Regelwerk", "Seite"}, ...]}`. `Name` contains an `<a
href="http://prd.5footstep.de/Permalink?page_id={ID}">{name}</a>` — strip the
tag for the plain name, keep the `page_id` to resolve the full page (§2).
`Beschreibung` is a short summary, not full rule text. No pagination, no nav
chrome to strip — it's already clean.

Same trick works for the other `*Index` pages (`/ZauberIndex`,
`/MonsterIndex`, ...) — check the index page's `<table data-file='...'>`
attribute for the matching `/cache/prd_datatable__*.txt` endpoint; the column
shape per type is in `js/datatables/prd_datatable.js`'s `switch(type)` block.

**Known data quirk:** a feat reprinted across two sourcebooks (e.g. GRW and
EXP) appears as *two rows with the same `ID`*, differing only in `Seite`. Not
an import bug — dedupe by `ID` if you need one row per feat.

Script: `import_feats_from_prd.py` → `../app/fixtures/imported/talente_prd_import.json`.

## 2. Full text for one feat → when implementing its handler

The index's `Beschreibung` is too short to implement from. The full text
(flavor, `Voraussetzungen:`, `Vorteil:`, sometimes `Normal:`/`Sonderregel:`,
and a cross-book `Referenz:` line) lives on the feat's own page. Resolve it
in two steps:

1. `http://prd.5footstep.de/Permalink?page_id={ID}` — 302-redirects to the
   canonical URL, e.g. `.../Expertenregeln/Talente/Adleraugen`. Follow the
   redirect (most HTTP clients do this automatically; `curl` needs `-L`).
2. On that page, the content is the `<div id="page" class="page">...</div>`
   block, right before the trailing `<script>var dbclick = "page";...`. Strip
   tags, unescape entities (`&nbsp;` → space), collapse whitespace. Example
   parse (same regex approach as both scripts here):

   ```python
   m = re.search(r'<div id="page" class="page">(.*?)<script type="text/javascript">', html, re.DOTALL)
   text = re.sub(r'<br\s*/?>', '\n', m.group(1))
   text = unescape(re.sub(r'<[^>]+>', '', text).replace('&nbsp;', ' '))
   ```

Doing this for all 1506 feats (1506 requests) hasn't been done — only worth
it if/when full rule text is actually needed catalog-wide. For the
one-handler-at-a-time workflow this is for, fetch on demand per feat.

## 3. Prose-only data not on any index (e.g. per-bloodline feat lists)

Some data (Sorcerer/Hexenmeister bloodline bonus-feat lists, class table
data, etc.) was never put in a datatable at all — it only exists as prose on
the relevant class/rules page, e.g.:

```
http://prd.5footstep.de/Grundregelwerk/Klassen/Hexenmeister
```

Same `<div id="page" class="page">` container as §2, but the internal
structure is hand-written HTML with no consistent schema — inspect each case
and parse by convention. What worked for the bloodlines: split the page on
`<h4>{section name}</h4>` markers to get one HTML chunk per bloodline, then
within each chunk regex for the specific `<strong>{Label}:</strong>...<br/>`
paragraph and strip tags from that slice. `Fertigkeitsfokus (Wissen
(Arkanes))`-style entries have a nested `<a>` around the skill name — split
on top-level commas only (`,\s*(?![^(]*\))`) so parenthetical skill choices
survive as one entry, not two.

**Known data quirk:** link text is occasionally a shortened display label
that differs from the feat's canonical catalog name (e.g. link text
"Entwaffnen" → target `.../Talente/VerbessertesEntwaffnen`, canonical name
"Verbessertes Entwaffnen"). When resolving a name from prose against the
catalog from §1 and it doesn't match, check the `href`'s last path segment
before concluding the feat is missing.

Script: `import_hexenmeister_bloodlines.py` → resolves each bloodline's
bonus feats against `talente_prd_import.json`'s `id`s, output at
`../app/fixtures/imported/hexenmeister_bloodline_bonus_feats.json`.

## 4. Turning the bulk feat index into DB seed data (`base_feats` + prerequisites)

`build_feats_seed.py` is a different kind of script from §1–3: it doesn't
fetch anything, it transforms the already-fetched `talente_prd_import.json`
(§1's output, 1506 feats across every sourcebook) straight into the
DB-shaped files under `../app/fixtures/seed/` (`base_feats.json` plus the six
`base_feat_required_*.json` prerequisite tables), scoped down to the
Grundregelwerk feats plus any other-sourcebook feat whose prerequisite
mentions a race/class currently in the database.

**Its output ids are deterministic, but one input isn't — restore
`base_feats.json` before rerunning.** Every id the script writes is derived
either from the PRD import's own stable id (new feats) or from
`RECONCILE_BY_NAME` (the 16 hand-seeded feats, matched by name to keep the
id their existing `character_feats` rows point at) or from a content hash
(requirement rows, `_stable_id()`/`ID_NAMESPACE` — feat + kind + fields,
deliberately excluding `group_id` since that's just a same-run correlation
tag, not part of a row's identity). So two runs against the same *inputs*
produce byte-identical output, and `app.seed.feat_seed` upserts cleanly
either way. The catch: the reconciliation step's input **is**
`app/fixtures/seed/base_feats.json` itself, so if you run the script,
commit nothing, and run it again, that second run reconciles against its
own already-merged output instead of the pre-merge 16-feat file. Restore
that one file from git (`git checkout -- ../app/fixtures/seed/base_feats.json`)
before rerunning during iteration.

**Prerequisite OR-groups** ("Elf oder Halb-Elf") land in a nullable
`group_id` column added to all six `BaseFeatRequired*` tables — rows sharing
a `(feat_id, group_id)` pair are OR-ed together (possibly across different
tables, e.g. a BAB requirement OR'd with a class-level one — see
"Kranichstil" test data: "GAB +2 oder Mönch 1"), then AND-ed against
everything else for that feat (see `BaseFeatRequiredFeat`'s docstring for
full semantics). Splitting is clause-by-clause (`;` = always AND) and, within
a clause containing "oder", only the *trailing* comma-run is oder-split into
the OR-core; earlier comma items in the same clause are walked backward and
absorbed into the OR-run only while they resolve to the same requirement
*kind* as the core — otherwise they're independent AND atoms. This matters
because natural-language enumerations mix kinds, e.g. "KO 13, Halb-Ork, Ork
oder Zwerg" is "CON 13 AND (half-orc OR orc OR dwarf)", not a 3-way OR that
swallows the CON requirement — an early version of this script got exactly
that wrong before the kind-matching backward-walk was added. If a clause's
OR-run ends up with fewer than two atoms actually resolving against the
current catalogs (e.g. "Elf oder Halb-Elf" when Halb-Elf isn't a modeled
race), the lone resolved atom is emitted as a plain ungrouped AND
requirement instead of a group — safe, since the unresolvable side of the OR
can never apply to any character that can currently exist in this database.
Individual atoms that don't resolve at all (referencing a race/class/ability
not in the DB yet, or free prose with no structured shape) are dropped
either way: an under-enforced prerequisite is recoverable (the raw text is
always kept in `base_feats.prerequisite_text`), a wrongly-enforced one
isn't.

## 5. Weapon and gear/tool tables → flat catalog staging files

The `Ausruestungskompendium` (equipment compendium) pages are a third shape,
different from both §1's DataTables JSON and §2/§3's free prose: hand-authored
wiki tables (`<div class="table_wrapper"><table class="usertable"><tr
class="userrow"><td class="usercell">...`), one row per item, no client-side
JS involved. Useful trick specific to the weapons page: it uniquely bundles
full prose descriptions for every simple/martial/exotic weapon on the *same*
page, under a `<h4>Waffenbeschreibungen</h4>` section (ending at the next
`<h4>`, "Meisterarbeiten von Waffen") - `<strong>{Name}:</strong> {text}`
entries, one per weapon, matched back to table rows by name. Before assuming
a full description needs a per-item page fetch (as in §2), check whether the
index/table page has an analogous `<h4>{X}beschreibungen</h4>` section first;
it's cheaper when it exists. It doesn't always: the adventuring-gear and
tools tables have no such section anywhere on their pages, so per those
scripts' docstrings, full per-item text is left unfetched for now (only the
row's own permalink URL is kept as `source_url`) - same "only worth it when
actually needed" reasoning as §2's bulk-feat-text call.

**Known quirks:**
- The weapon tables use `<td class="usercell" colspan="9">` (11 for the
  firearms table, which adds Fehlzündung/misfire and Kapazität/capacity
  columns) for two different things that need telling apart: a
  `<em>{subheading}</em>`-only cell (a subgroup marker like "Leichte Waffen",
  applying to subsequent rows until the next one) vs. a footnote row (starts
  with `<sup>`, no `<em>`) that isn't a weapon row at all and is skipped.
- The `Waffenbeschreibungen` entries are inconsistently punctuated: usually
  `<strong>Name:</strong> text`, but occasionally the colon sits *outside*
  the bold (`<strong>Name</strong>: text`) or there's stray whitespace
  *inside* it before the colon (`<strong>Name:  </strong>`). A regex
  requiring the literal sequence `:</strong>` silently mis-parses these -
  it keeps extending its non-greedy match past the malformed entry looking
  for the next place that literal sequence occurs, silently merging two (or
  more) unrelated weapons' worth of text into one entry. Fix: match every
  `<strong>...</strong>` span first, then resolve the colon's position (in
  bold, or just after) relative to that match, instead of anchoring the
  whole pattern on where the colon has to be.
- Not every table name matches a `Waffenbeschreibungen` entry
  case/whitespace-normalized (~80% hit rate) - remaining misses are genuine
  site inconsistencies (a table name carrying a quantity suffix like
  "Schuriken (5)" vs. the prose's plain "Schuriken"; singular/plural drift
  like "Bolas" vs. "Bola"; a literal hyphen in one heading,
  "Zweihändige-Axt", vs. the table's "Zweihändige Axt"). Left `null` rather
  than fuzzy-matched, same policy as unresolved feat prerequisites in §4.

Scripts: `import_waffen_prd.py` → `../app/fixtures/imported/waffen_prd_import.json`
(198 weapons: simple/martial/exotic/firearm, with description where matched);
`import_ausruestung_prd.py` → `../app/fixtures/imported/ausruestung_prd_import.json`
(292 rows: adventuring gear + tools, summary columns only, `source_url` kept
per row for on-demand full-text fetch later).

## 6. Poison/disease tables → `BaseCondition` seed rows directly

`build_conditions_seed.py` (roadmap slice 5) is a fourth shape again: a
`<table>` of example poisons (same wiki-table shape as §5) at
`.../Gebrechen/Gifte`, but the diseases page (`.../Gebrechen/Krankheiten`)
has no table at all — one `<h5><span class="cl-stat-block-title">{Name}
</span></h5>` per disease, followed by a single `<p>` stat block
(`<strong>Art</strong>`/`Rettungswurf`/`Inkubationszeit`/`Frequenz`/
`Effekt`/`Heilung` lines). The standard PF1e conditions (Verängstigt,
Gelähmt, ...) aren't on any PRD page in structured form either — same
"hand-transcribe it" situation as §3's bloodline lists — so they're a plain
Python list literal in the script itself, not fetched.

Unlike every other script here, this one skips the fetch/build split (no
`app/fixtures/imported/` intermediate): `BaseCondition` only has `name`/
`description` (see `models/effect.py`), so there's no cross-catalog
resolution step that would need the raw fetch kept around separately — the
table/stat-block fields get formatted straight into one `description` block
per row (a poison/disease's SG/Inkubationszeit/Frequenz becomes descriptive
text, not separate columns; the actual numbers get typed in by the player at
activation time, see roadmap.md's slice 5).

**Known quirk:** the diseases page's stat-block paragraph doesn't reliably
end at the first `</p>` — some entries have additional prose inside the same
`<p>` past a stray nested tag, which cut a naive `<br />(.*?)</p>` match off
mid-sentence (caught on "Trübe Sieche", whose blindness-on-heavy-damage
clause got truncated). Fixed by capturing everything up to the next entry's
leading anchor (`<!--notypo--><a name="p`) instead of trusting `</p>`.

Script: `build_conditions_seed.py` → `../app/fixtures/seed/base_conditions.json`
(79 rows: 33 conditions + 35 poisons + 11 diseases), loaded via
`app.seed.condition_seed` (same upsert-by-id pattern as `trait_seed.py`).

## 7. Spell index + per-page stat blocks → `base_spells`/`base_class_spells`

Same two-step shape as talente (§1 bulk index, §2 per-page full text), plus
a §4-style build step, but for `/ZauberIndex`:

- `import_zauber_prd.py` → `../app/fixtures/imported/zauber_prd_import.json`
  (1901 unique spells across every sourcebook, from
  `/cache/prd_datatable__zauber.txt`; per-class grade columns keyed by PRD
  class name, not yet matched against `base_classes`).
- `fetch_zauber_prd_details.py` → `../app/fixtures/imported/zauber_prd_details.json`
  (one page fetch per spell for the stat block — Schule/Zeitaufwand/
  Komponenten/Reichweite/Ziel-Effekt-Bereich/Wirkungsdauer/Rettungswurf/
  Zauberresistenz — plus full prose; ~1900 requests, so resumable: reruns
  skip ids already in the output file and merge in only what's missing, with
  a checkpoint save every 50 fetches in case of interruption).
- `build_spells_seed.py` → `../app/fixtures/seed/base_spells.json` +
  `base_class_spells.json`, scoped to spells accessible to a class currently
  modeled with a `spell_tradition` (same "only currently relevant" call as
  §4's race/class filter). **Same restore-before-rerun pitfall as §4**: its
  reconciliation step's input is the seed files it writes, so
  `git checkout -- ../app/fixtures/seed/base_spells.json
  ../app/fixtures/seed/base_class_spells.json` before rerunning during
  iteration, or a second run reconciles against its own prior output instead
  of the original hand-seeded rows.

**Known quirk:** not every spell page restates its own `Schule:` line — a
"funktioniert wie {Basiszauber}" variant (e.g. "Ameisenstärke,
Gemeinschaftliche") or a mythic "Legendäre {Basiszauber}" addendum (Ausbauregeln
V: Legenden) can have no stat block at all beyond prose, which would leave
`school` empty. `build_spells_seed.py` falls back to the bulk index's own
`school` column in that case (it's always populated there) rather than
seeding an empty string — an earlier version didn't, and an empty-string
"school" broke `/api/spell-schools`'s distinct-school list (used by the
Zauberfokus feat's sub-choice picker), since `sorted()` puts `""` first.

## 8. Wesenszüge (traits) prose page → `BaseTrait` seed rows directly

`build_traits_seed.py` is the same direct fetch-into-seed shape as
§6/`build_conditions_seed.py` (`BaseTrait` only has `name`/`description`/
`area`, so no cross-catalog resolution step is needed), applied to a single
prose page:

```
http://prd.5footstep.de/AusbauregelnIVKampagnen/Charakterhintergrund/Wesenszuege
```

Structurally this page nests `h3`/`h4`/`h5` category headers (four
"Grundwesenszüge" groups — Glaube/Kampf/Magie/Sozial — plus "Wesenszüge
(Regional)"/"(Religion)"/"(Volk)", the last one further split per race and a
sibling "Blutlinie" subsection), each containing one `<p class="auto"
id="...">...<strong>{Name}:</strong> {description}</p>` block per trait —
same shape as §2/§6's prose entries.

**Known quirk:** every category/race subsection opens with an intro
sentence (e.g. "Nur Elfen können diese Wesenszüge wählen:") inside a `<p>`
that WackoWiki never closes before the first trait's own nested `<p>`
starts. A naive parse that anchors `<strong>` at the start of the outer
paragraph's match therefore silently drops the *first* trait of every
subsection — the intro sentence is what's at the start, not the trait name.
Fixed by `re.search`ing for the first `<strong>...</strong>` anywhere in the
paragraph body instead of requiring it at the start.

**Encoding correction (applies to every script in this file, not just this
one):** this page's own `<meta>` tag and this document's general guidance
above both say `iso-8859-1`, but at least one entry ("Eifernder Krieger")
contains a cp1252-only byte (a German „curly quote", 0x93) that strict
`iso-8859-1` decodes into a C1 control character instead of the actual
character — verified against the raw response bytes. `cp1252` is a superset
of `iso-8859-1` for every other byte observed on this site, so decoding as
`cp1252` instead is strictly a fix, not a behavior change, for content that
stays within true `iso-8859-1`. Not (yet) back-verified against every other
script's already-fetched output in this directory — if a future script's
output turns up stray `\x80`–`\x9f` characters, this is almost certainly why.

**`area` mapping:** the four "Grundwesenszüge" groups map directly
(Glaube→`faith`, Kampf→`combat`, Magie→`magic`, Sozial→`social`);
"Wesenszüge (Regional)" reuses the pre-existing `region` tag. Two new tags:
`religion` for "Wesenszüge (Religion)" (deity/alignment-specific traits —
PF1e's Additional Traits/Ultimate Campaign rules treat these as their own
trait type, not a Glaube subtype, for the one-trait-per-area rule) and
`race` for "Wesenszüge (Volk)" (the 7 per-race subsections plus the sibling
"Blutlinie" heritage subsection, which isn't itself race-restricted but is
grouped with the race traits on the source page). `BaseTrait` has no field
for "only choosable by race X" — the 7 per-race subsections' restriction
(stated once, in the subsection's own intro sentence, not per trait) is
preserved by prefixing each of those traits' descriptions with "(Nur für
{Rasse} wählbar.)" instead of being silently dropped.

Script: `build_traits_seed.py` → `../app/fixtures/seed/base_traits.json`
(220 rows, replacing the 10 hand-written placeholder traits that shipped
before this import), loaded via `app.seed.trait_seed` (same upsert-by-id
pattern as `build_conditions_seed.py`).

## Finding a class/section's page path

`/{Book}/Klassen/{ClassSlug}` — book prefix matches the left nav on any PRD
page (`Grundregelwerk`, `Expertenregeln`, `Ausbauregeln-II-Kampf`, ...), slug
usually the German class name with umlauts stripped to plain vowels
(`Kaempfer`, `Waldlaeufer`, `Moench`). Cheapest way to confirm the exact slug
for a class/page you don't already have the URL for: fetch the book's
`/{Book}/Klassen` overview page and grep its links rather than guessing.
