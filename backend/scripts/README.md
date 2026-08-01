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

## Finding a class/section's page path

`/{Book}/Klassen/{ClassSlug}` — book prefix matches the left nav on any PRD
page (`Grundregelwerk`, `Expertenregeln`, `Ausbauregeln-II-Kampf`, ...), slug
usually the German class name with umlauts stripped to plain vowels
(`Kaempfer`, `Waldlaeufer`, `Moench`). Cheapest way to confirm the exact slug
for a class/page you don't already have the URL for: fetch the book's
`/{Book}/Klassen` overview page and grep its links rather than guessing.
