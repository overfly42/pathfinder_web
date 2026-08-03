from sqlalchemy import Float, Integer, String, Text
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
