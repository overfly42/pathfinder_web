import uuid

from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text, UniqueConstraint
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
    is free-text property notes (e.g. "Nicht tödlich"). All of these are
    plain imported strings, not evaluated by any rule logic — no attack-
    bonus/damage computation reads them yet, they only close the "no schema
    field existed at all" half of roadmap.md's "Waffenkatalog ohne
    Kampfwerte" gap; the computation half stays open.

    `weight_lb` (raw string, e.g. "4 Pfd.") and `description` (prose text)
    are generic across every category but only populated for "weapon" and
    "tool" rows so far (import scope so far); armor/gear/consumable rows
    stay null until a later pass backfills them."""

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
    weight_lb: Mapped[str | None] = mapped_column(String(32), nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)


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
