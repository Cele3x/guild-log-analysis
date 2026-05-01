"""Loader for Midnight-expansion defensive abilities from the markdown reference."""

import logging
import os
import re
from typing import Optional

logger = logging.getLogger(__name__)


DEFAULT_DEFENSIVES_PATH = (
    "/home/jonathan/Notes/Default/World of Warcraft/Raid Managment/Defensives.md"
)

# Map class abbreviations / names from the Class column to WCL class names.
_CLASS_ALIASES = {
    "DK": "DEATHKNIGHT",
    "DH": "DEMONHUNTER",
    "DEATHKNIGHT": "DEATHKNIGHT",
    "DEMONHUNTER": "DEMONHUNTER",
    "DEATH KNIGHT": "DEATHKNIGHT",
    "DEMON HUNTER": "DEMONHUNTER",
    "DRUID": "DRUID",
    "EVOKER": "EVOKER",
    "HUNTER": "HUNTER",
    "MAGE": "MAGE",
    "MONK": "MONK",
    "PALADIN": "PALADIN",
    "PRIEST": "PRIEST",
    "ROGUE": "ROGUE",
    "SHAMAN": "SHAMAN",
    "WARLOCK": "WARLOCK",
    "WARRIOR": "WARRIOR",
}

_VALID_TYPES = {"defensive", "heal", "external", "raid_defensive", "consumable"}

# Spell IDs of regular and demonic Healthstones. Warlocks should only ever
# show the demonic version; everyone else only the regular one.
_HEALTHSTONE_SPELL_ID = 6262
_DEMONIC_HEALTHSTONE_SPELL_ID = 452930

# Some abilities log under multiple spell IDs in WCL (e.g. consuming a
# Demonic Healthstone fires a cast of Healthstone (6262) — the demonic
# upgrade only modifies the heal effect 452930). Map listed spell_id to
# the full set of cast IDs that should count as a "use".
_CAST_ID_ALIASES: dict[int, set[int]] = {
    _DEMONIC_HEALTHSTONE_SPELL_ID: {_DEMONIC_HEALTHSTONE_SPELL_ID, _HEALTHSTONE_SPELL_ID},
}


def cast_ids_for(spell_id: int) -> set[int]:
    """Return all WCL cast IDs that should count as a use of ``spell_id``."""
    return _CAST_ID_ALIASES.get(spell_id, {spell_id})

# Available-column values that count as "the player likely has this".
# Only `Yes` qualifies — `Situational`, `No`, and `?` are excluded.
_INCLUDED_AVAILABLE = {"yes"}


def _parse_int(value: str) -> Optional[int]:
    value = value.strip()
    if not value or value in {"—", "-"}:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _parse_table_row(line: str) -> Optional[list[str]]:
    """Return cells of a markdown table row, or None if not a data row."""
    line = line.rstrip("\n").strip()
    if not line.startswith("|") or not line.endswith("|"):
        return None
    # Strip leading and trailing pipe, then split on remaining pipes.
    inner = line[1:-1]
    cells = [c.strip() for c in inner.split("|")]
    # Skip header / separator rows.
    if not cells or set("".join(cells)) <= {"-", ":", " "}:
        return None
    return cells


def load_defensives(path: str = DEFAULT_DEFENSIVES_PATH) -> dict[str, list[dict]]:
    """
    Parse the Midnight defensives markdown into per-class ability lists.

    The markdown has two relevant sections:

    - ``## Universal Consumables (any class / spec)`` — five-column table
      [Ability | Spell ID | CD (s) | Usually Available | Notes]. These rows
      are merged into every class (Demonic Healthstone is Warlock-only).
    - ``## Class & Spec Defensives & Heals`` — eight-column table
      [Class | Spec | Ability | Spell ID | CD | Type | Available | Notes].

    Rows whose ``Available`` value is not ``Yes`` or ``Situational`` are
    dropped (rarely-picked talents and uncertain entries shouldn't appear
    in death-availability checks). Duplicate spell IDs within a class are
    de-duped, keeping the first occurrence.

    :param path: Filesystem path to the markdown file.
    :return: dict of WCL class name -> list of ability dicts with keys
        ``spell_id``, ``name``, ``cooldown``, ``type``, ``spec``.
    """
    if not os.path.exists(path):
        logger.warning(f"Defensives markdown not found at {path}")
        return {}

    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    section: Optional[str] = None  # "consumables" | "main" | None
    by_class: dict[str, dict[int, dict]] = {}
    universal: list[dict] = []

    for raw in lines:
        line = raw.rstrip("\n")

        if line.startswith("## "):
            heading = line[3:].strip().lower()
            if heading.startswith("universal consumables"):
                section = "consumables"
            elif heading.startswith("class & spec"):
                section = "main"
            else:
                section = None
            continue

        if section is None:
            continue

        cells = _parse_table_row(line)
        if cells is None:
            continue

        if section == "consumables":
            # [Ability, Spell ID, CD (s), Usually Available, Notes]
            if len(cells) < 4:
                continue
            name = cells[0]
            spell_id = _parse_int(cells[1])
            cooldown = _parse_int(cells[2])
            available = cells[3].split()[0].lower().rstrip(",") if cells[3] else ""
            if spell_id is None or cooldown is None:
                continue
            if available not in _INCLUDED_AVAILABLE:
                continue
            universal.append({
                "spell_id": spell_id,
                "name": name,
                "cooldown": cooldown,
                "type": "consumable",
                "spec": "All",
                # Marker used downstream to scope warlock-only stones.
                "warlock_only": "warlock only" in cells[3].lower(),
                # Healthstones and combat potions reset on combat-leave, so
                # they're effectively once-per-fight regardless of the
                # listed cooldown (cross-fight casts must not block).
                "single_use_per_fight": True,
            })
            continue

        # main table: [Class, Spec, Ability, Spell ID, CD, Type, Available, Notes]
        if len(cells) < 7:
            continue
        cls_raw = cells[0].upper()
        cls = _CLASS_ALIASES.get(cls_raw)
        if cls is None:
            continue
        spec = cells[1] or "All"
        name = cells[2]
        spell_id = _parse_int(cells[3])
        cooldown = _parse_int(cells[4])
        ability_type = cells[5].strip().lower()
        available = cells[6].strip().lower()

        if spell_id is None or cooldown is None or ability_type not in _VALID_TYPES:
            continue
        if available not in _INCLUDED_AVAILABLE:
            continue

        entry = {
            "spell_id": spell_id,
            "name": name,
            "cooldown": cooldown,
            "type": ability_type,
            "spec": spec,
        }
        by_class.setdefault(cls, {}).setdefault(spell_id, entry)

    # Flatten and merge universal consumables into every class.
    result: dict[str, list[dict]] = {cls: list(m.values()) for cls, m in by_class.items()}

    for cls in _CLASS_ALIASES.values():
        existing_ids = {a["spell_id"] for a in result.get(cls, [])}
        for entry in universal:
            if entry.get("warlock_only") and cls != "WARLOCK":
                continue
            # Warlocks have Demonic Healthstone instead of the regular one.
            if entry["spell_id"] == _HEALTHSTONE_SPELL_ID and cls == "WARLOCK":
                continue
            if entry["spell_id"] in existing_ids:
                continue
            result.setdefault(cls, []).append({
                k: v for k, v in entry.items() if k != "warlock_only"
            })

    total = sum(len(v) for v in result.values())
    logger.info(f"Loaded {total} defensives across {len(result)} classes from {path}")
    return result


def all_defensive_spell_ids(by_class: dict[str, list[dict]]) -> set[int]:
    """Return the union of all defensive spell IDs across all classes."""
    return {a["spell_id"] for abilities in by_class.values() for a in abilities}
