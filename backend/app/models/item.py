import uuid

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class BaseItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Catalog of gear/equipment, replacing `items.json`'s flat name/price
    list. `category` is a plain categorization tag (e.g. "weapon", "armor",
    "shield", "gear", "tool", "consumable") — same plain-string convention as
    `BaseFeat.type`/`BaseTrait.area`, mostly not evaluated by any rule logic
    (no attack-bonus computation exists yet), only there so a picker can
    group/filter by it. `price` is in gold pieces; fractional (e.g. 0.01 for
    a torch).

    `ac_bonus`/`max_dex_bonus` (roadmap slice 4) are the exception: real,
    computed fields for category "armor"/"shield" — `ac_bonus` is the flat
    AC bonus while equipped, `max_dex_bonus` (armor only) caps the Dex
    modifier applied to AC while worn. Both null for every other category.

    `weapon_group` (e.g. "leichte_klingen", "keulen") is only set for
    category "weapon" — same plain-tag convention as `category`, not
    evaluated by any rule logic yet. Exists so a class feature that grants a
    bonus per weapon *group* rather than per weapon (Kämpfer's
    Waffentraining) has something to pick from; still unpopulated for every
    weapon row (a different, still-open catalog gap than the one below).

    `damage_small`/`damage_medium`/`critical`/`weapon_range`/`damage_type`/
    `weapon_type`/`special` (imported from the German PRD, see
    `backend/scripts/import_waffen_prd.py`) are only set for category
    "weapon": `damage_small`/`damage_medium` are the raw damage-die strings
    for Small/Medium wielders (e.g. "1W6"/"1W8"), `critical` is the raw
    threat-range/multiplier string (e.g. "19-20/×2"), `weapon_range` is the
    raw thrown/ranged distance (e.g. "6 m", null for melee-only weapons),
    `damage_type` is the raw damage-type letter(s) ("H"/"S"/"W" or
    combinations like "H oder S"), `weapon_type` is the weapon proficiency
    category ("simple"/"martial"/"exotic"/"firearm" — distinct from
    `category`, which stays the picker-filter tag "weapon", and distinct
    from `weapon_group` above, which is a different taxonomy), and `special`
    is free-text property notes (e.g. "Nicht tödlich"). These are plain
    imported strings, not evaluated by any rule logic.

    `is_light` (weapon only, backfilled by `backend/scripts/
    backfill_weapon_is_light.py`) is not a literal weight-class flag — it's
    scoped to exactly one question: does Waffenfinesse (`rules/feats.py`'s
    `WAFFENFINESSE`, `sheet.py`'s `_build_weapon_attacks`) let Dex replace
    Str on this weapon's attack roll. `True` for the PRD's "Leichte Waffen"
    subgroup plus PF1e's named non-light exceptions (Rapier, Peitsche,
    Stachelkette, Elfisches Krummschwert — RAW lets the feat apply to these
    by name even though none of them is actually light), `False` for every
    other classified weapon, `null` for the handful of rows with no PRD
    `subgroup` at all.

    `hands` ("one"/"two", weapon only) is the one exception that *is*
    computed from (roadmap.md's Slice-4 weapon-slot item, 2026-08-11): which
    paperdoll weapon slot(s) an equipped weapon occupies
    (`rules.equipment_slots`) and, together with `sheet.py`'s Str modifier,
    the attack-bonus/damage-dice readout. Backfilled from the PRD import's
    `subgroup` column (`Zweihandwaffen`/`Zweihändige Feuerwaffen*` -> "two",
    `Einhandwaffen`/`Leichte Waffen`/`Einhändige Feuerwaffen*` -> "one"; see
    `backend/scripts/README.md`'s weapon-import section) — that column
    itself was never persisted to `BaseItem` before, only the price/damage
    table it came with. For the `Fernkampfwaffen` (ranged) subgroup, which
    mixes bows (two-handed), crossbows (mostly two-handed, hand crossbows
    one-handed) and thrown weapons (one-handed) under one PRD heading with
    no further column to disambiguate, each row was hand-classified by name
    against the PRD text rather than guessed by a blanket rule. Null for
    every non-"weapon" row and for the handful of weapon rows with no
    PRD-sourced `subgroup` at all (the 16 old placeholder rows predating the
    PRD import, see roadmap.md's "Waffenkatalog ohne Kampfwerte") — those
    render with no paperdoll weapon slot until re-matched to a PRD row.

    `weight_lb` (raw string, e.g. "4 Pfd.") and `description` (prose text)
    are generic across every category but only populated for "weapon" and
    "tool" rows so far (import scope so far); armor/gear/consumable rows
    stay null until a later pass backfills them.

    `slot`/`activation`/`uses_per_day`/`max_charges`/`granted_ability`/
    `ability_bonus` (roadmap.md's "Wondrous-Item-Katalog mit echter
    Attributsboni-Wirkung", decided 2026-08-04) are only set for category
    "wondrous"/"ring"/"wand" — composition-only catalog *maximums*, the
    changeable per-character counters live on `CharacterGear` instead (same
    reasoning as `CharacterGear.enhancement`: state that moves during play
    doesn't belong in the catalog). `slot` is one of `rules.equipment_slots`'s
    paperdoll slot keys, except rings use the generic value "ring" (valid for
    either of the two ring slots) rather than a fixed key. `activation` is
    "permanent" or "activatable" (plain tag, same convention as `category`).
    `uses_per_day` is the N in "N-mal pro Tag" (1 covers "once per day" too,
    no separate flag for that); null means either permanent or unlimited-use
    activatable. `max_charges` is a wand's charge ceiling (50 by default) but
    generic enough to reuse for the rare non-wand charge item. `granted_ability`
    (e.g. "constitution") + `ability_bonus` (e.g. 2) are only set for the
    attribute-boosting item family (belts/headbands/gloves/amulets); each
    bonus tier (+2/+4/+6) is its own catalog row with its own price, same
    "one row per tier" pattern as `BaseWeaponSpecialAbility.bonus_equivalent`
    rather than a price list crammed into one field."""

    __tablename__ = "base_items"

    name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(64))
    price: Mapped[float] = mapped_column(Float)
    ac_bonus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_dex_bonus: Mapped[int | None] = mapped_column(Integer, nullable=True)
    weapon_group: Mapped[str | None] = mapped_column(String(64), nullable=True)
    damage_small: Mapped[str | None] = mapped_column(String(32), nullable=True)
    damage_medium: Mapped[str | None] = mapped_column(String(32), nullable=True)
    critical: Mapped[str | None] = mapped_column(String(32), nullable=True)
    weapon_range: Mapped[str | None] = mapped_column(String(32), nullable=True)
    damage_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    weapon_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    special: Mapped[str | None] = mapped_column(String(255), nullable=True)
    hands: Mapped[str | None] = mapped_column(String(8), nullable=True)
    is_light: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    weight_lb: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    slot: Mapped[str | None] = mapped_column(String(32), nullable=True)
    activation: Mapped[str | None] = mapped_column(String(16), nullable=True)
    uses_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_charges: Mapped[int | None] = mapped_column(Integer, nullable=True)
    granted_ability: Mapped[str | None] = mapped_column(String(16), nullable=True)
    ability_bonus: Mapped[int | None] = mapped_column(Integer, nullable=True)


class BaseWeaponSpecialAbility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Catalog of named magic weapon special abilities (roadmap.md's
    "Magische Verzauberung/Material als Berechnung statt Freitext"),
    replacing `CharacterGear.properties`' freetext for the ~90 abilities the
    German PRD defines — composition-only, same convention as
    `BaseRaceAbility`/`BaseFeat`: what an ability *is* lives here as data,
    what it actually *does* (mostly nothing computed — see
    `app.rules.weapon_abilities`'s module docstring for why) is resolved by
    id, not by a schema column.

    `bonus_equivalent` (1-5) is the PF1e "enchantment slot" cost used for the
    +10 total-bonus cap and the price table — not always the same number as
    the ability's actual gold price (a few, e.g. "Undurchdringbar", cost a
    flat gp amount instead of a bonus-equivalent formula; that flat price
    itself isn't modeled, this app doesn't compute market prices, see
    `import_waffeneigenschaften_prd.py`). Nullable: two abilities
    ("Duell", "Selbstverwandelnd") sit under a table section spanning two
    tiers with a flat price that doesn't disambiguate which — left unset
    rather than guessed, same "don't guess" policy as everywhere else in
    this catalog's import.

    `applicable_categories` (subset of "melee"/"ranged"/"ammunition" — which
    of the PRD's three price tables list the ability) is informative for a
    future selection dialog, not a DB constraint, same pattern as
    `restriction_note` below.

    `restriction_note` is a short PRD footnote tag for narrower restrictions
    that don't fit `applicable_categories` (e.g. "Nur Wuchtwaffen.") or
    mutual exclusions (e.g. Verlässlich vs. Mächtige Verlässlichkeit) —
    informative only, never enforced server-side, same non-DB-constraint
    pattern `BaseClassOptionChoice`'s docstring describes for the Talent-Sub-
    Wahl-Schema. `description` is the full PRD rule text, never evaluated by
    rule logic; null for the handful of abilities the source page names in
    a table but never gives their own prose entry to (see the import
    script's docstring)."""

    __tablename__ = "base_weapon_special_abilities"

    name: Mapped[str] = mapped_column(String(255))
    bonus_equivalent: Mapped[int | None] = mapped_column(Integer, nullable=True)
    applicable_categories: Mapped[list[str]] = mapped_column(JSON, default=list)
    restriction_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


class CharacterGearSpecialAbility(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Which special abilities (`BaseWeaponSpecialAbility`) a specific
    `CharacterGear` row has — a gear item can carry more than one (up to the
    PF1e +10 cap, not enforced here, see `BaseWeaponSpecialAbility`'s
    docstring), each ability at most once per item."""

    __tablename__ = "character_gear_special_abilities"
    __table_args__ = (UniqueConstraint("gear_id", "ability_id"),)

    gear_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("character_gear.id"))
    ability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("base_weapon_special_abilities.id")
    )


class BaseItemGrantedSpell(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Which spells a `BaseItem` keeps its wearer permanently under the
    effect of while equipped (e.g. Brustplatte des Freibeuters ->
    permanently "Auf Wasser gehen") — composition-only catalog data, same
    convention as `CharacterGearSpecialAbility`/`BaseClassSpell`: *what* an
    item grants is data, *what the spell actually does* is resolved by
    `rules.handlers`/`EFFECT_HANDLERS` off the spell's own id like any other
    spell effect, keyed by `spell_id`, not by this row.

    A join table rather than a single nullable FK on `BaseItem` itself
    (contrast `BaseItem.granted_ability`/`ability_bonus`) because a single
    named magic item can carry more than one such spell (a ring granting
    both, say, `Wasseratmung` and `Auf Wasser gehen`), unlike the
    attribute-bonus family where one item only ever grants one bonus.

    Not tracked via `CharacterEffect`/`character.effects` — that table
    models player-toggled, duration-countdown instances (roadmap slice 5);
    this is unconditional and un-cancelable for as long as the item stays
    equipped, with no duration to count down, so `sheet.py` derives it
    fresh from the equipped-gear set on every sheet build instead (see
    `_build_item_granted_effects`) rather than storing a row that would
    need to be created/deleted in lockstep with equip/unequip.

    `note` is optional item-specific rider text (e.g. a restriction or
    variance from the plain spell) appended to the spell's own catalog
    description for display — null when the spell's own description
    already covers everything relevant (the common case)."""

    __tablename__ = "base_item_granted_spells"
    __table_args__ = (UniqueConstraint("item_id", "spell_id"),)

    item_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_items.id"))
    spell_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("base_spells.id"))
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
