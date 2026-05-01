"""
Cooldown assignment compliance checking.

Parses an MRT-style assignment note and verifies, per fight, whether the
named player used the assigned cooldown within a configurable margin of the
expected timestamp (relative to the start of its phase).

This module is intentionally separate from the standard boss analysis flow
and is meant to be invoked manually via ``scripts/check-cd-assignments``.
"""

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Optional

from ..api.client import WarcraftLogsAPIClient
from ..config.constants import load_spells_data

logger = logging.getLogger(__name__)


_DIFFICULTY_MAP = {
    "LFR": 1,
    "Normal": 3,
    "Heroic": 4,
    "Mythic": 5,
}

# Resurrect spell IDs we treat as "alive again" markers. The cast event's
# targetID is the player being resurrected (source == target for self-rezzes
# such as Reincarnation and Soulstone Resurrection).
_RESURRECT_SPELL_IDS: list[int] = [
    20484,   # Rebirth (Druid)
    7328,    # Redemption (Paladin)
    2008,    # Ancestral Spirit (Shaman)
    2006,    # Resurrection (Priest)
    115178,  # Resuscitate (Monk)
    20707,   # Soulstone Resurrection (Warlock)
    391054,  # Intercession (Paladin)
    212036,  # Mass Resurrection
    21169,   # Reincarnation (Shaman self-rez)
    361227,  # Return (Evoker)
]


@dataclass
class Assignment:
    """A single cooldown assignment from an MRT note."""

    time_seconds: int
    phase: int
    player_name: str
    spell_id: int
    boss_spell_id: Optional[int] = None
    text: Optional[str] = None


@dataclass
class AssignmentNote:
    """Parsed assignment note with header metadata and CD assignments."""

    encounter_id: int
    difficulty: int
    name: str
    assignments: list[Assignment]


@dataclass
class AssignmentResult:
    """Result of checking a single assignment against a single fight."""

    report_code: str
    fight_id: int
    phase: int
    expected_time_seconds: int
    expected_timestamp_ms: int
    player_name: str
    spell_id: int
    spell_name: str
    boss_spell_id: Optional[int]
    text: Optional[str]
    hit: bool
    actual_offset_seconds: Optional[float]
    player_in_roster: bool
    phase_reached: bool
    player_dead: bool = False
    player_role: Optional[str] = None
    player_class: Optional[str] = None


@dataclass
class FightInfo:
    """Per-fight metadata for table rendering."""

    report_code: str
    fight_id: int
    start_time_ms: int
    end_time_ms: int
    pull_index: int  # 1-based pull number within its report


@dataclass
class ComplianceReport:
    """All inputs and outputs needed to render an assignment-compliance table."""

    note: AssignmentNote
    margin_seconds: float
    assignments: list[Assignment]  # post-filter, in display order
    fights: list[FightInfo]
    # results indexed by (report_code, fight_id, assignment_index)
    results: dict[tuple[str, int, int], AssignmentResult] = field(default_factory=dict)
    spell_names: dict[int, str] = field(default_factory=dict)


def _parse_kv_line(line: str) -> dict[str, str]:
    """Parse a ``key:value;key:value;`` MRT line into a dict."""
    out: dict[str, str] = {}
    for token in line.rstrip(";").split(";"):
        if ":" not in token:
            continue
        key, _, value = token.partition(":")
        out[key.strip()] = value.strip()
    return out


def parse_assignment_note(text: str) -> AssignmentNote:
    """
    Parse an MRT-style cooldown assignment note.

    The expected format is a header line ``EncounterID:N;Difficulty:Mythic;Name:Foo``
    followed by lines of the form ``time:T;ph:P;[bossSpell:B;]tag:Player;spellid:S;``.
    Lines whose ``tag`` field contains multiple players (whitespace-separated)
    or that do not carry a ``spellid`` are skipped, since they describe
    soak/positional assignments rather than cooldown usage.

    :param text: Raw note contents.
    :returns: Parsed :class:`AssignmentNote`.
    :raises ValueError: If the header line is missing or malformed.
    """
    encounter_id: Optional[int] = None
    difficulty: Optional[int] = None
    name: Optional[str] = None
    assignments: list[Assignment] = []

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if "EncounterID:" in line and "Difficulty:" in line:
            header = _parse_kv_line(line)
            try:
                encounter_id = int(header["EncounterID"])
            except (KeyError, ValueError) as exc:
                raise ValueError(f"Malformed EncounterID in header: {line!r}") from exc

            diff_raw = header.get("Difficulty", "").strip()
            if diff_raw in _DIFFICULTY_MAP:
                difficulty = _DIFFICULTY_MAP[diff_raw]
            elif diff_raw.isdigit():
                difficulty = int(diff_raw)
            else:
                raise ValueError(f"Unknown difficulty {diff_raw!r} in header")
            name = header.get("Name", "")
            continue

        if not line.startswith("time:"):
            continue

        fields_ = _parse_kv_line(line)
        spellid = fields_.get("spellid")
        tag = fields_.get("tag", "")
        if not spellid or not tag or " " in tag:
            continue

        try:
            assignments.append(
                Assignment(
                    time_seconds=int(fields_["time"]),
                    phase=int(fields_.get("ph", "1")),
                    player_name=tag,
                    spell_id=int(spellid),
                    boss_spell_id=(int(fields_["bossSpell"]) if "bossSpell" in fields_ else None),
                    text=fields_.get("text"),
                )
            )
        except (KeyError, ValueError):
            logger.debug("Skipping unparseable line: %r", line)
            continue

    if encounter_id is None or difficulty is None:
        raise ValueError("Assignment note is missing the EncounterID/Difficulty/Name header line")

    return AssignmentNote(
        encounter_id=encounter_id,
        difficulty=difficulty,
        name=name or "",
        assignments=assignments,
    )


# --------------------------------------------------------------------------
# Warcraft Logs queries
# --------------------------------------------------------------------------


def _fetch_fights_with_phases(
    api_client: WarcraftLogsAPIClient,
    report_code: str,
    encounter_id: int,
    difficulty: int,
) -> tuple[list[dict[str, Any]], int]:
    query = """
    query GetFightsWithPhases(
        $reportCode: String!, $encounterId: Int!, $difficulty: Int!
    ) {
      reportData {
        report(code: $reportCode) {
          startTime
          fights(encounterID: $encounterId, difficulty: $difficulty) {
            id
            startTime
            endTime
            phaseTransitions { id startTime }
          }
        }
      }
    }
    """
    variables = {
        "reportCode": report_code,
        "encounterId": encounter_id,
        "difficulty": difficulty,
    }
    result = api_client.make_request(query, variables)
    report = result.get("data", {}).get("reportData", {}).get("report") or {}
    fights = report.get("fights") or []
    report_start_ms = int(report.get("startTime") or 0)
    return fights, report_start_ms


def _fetch_participants(
    api_client: WarcraftLogsAPIClient,
    report_code: str,
    fight_ids: list[int],
) -> list[dict[str, Any]]:
    query = """
    query GetPlayerDetails($reportCode: String!, $fightIds: [Int!]!) {
      reportData {
        report(code: $reportCode) {
          playerDetails(fightIDs: $fightIds)
        }
      }
    }
    """
    result = api_client.make_request(query, {"reportCode": report_code, "fightIds": fight_ids})
    pd_block = (
        result.get("data", {})
        .get("reportData", {})
        .get("report", {})
        .get("playerDetails", {})
    )
    if not pd_block:
        return []
    player_data = pd_block.get("data", {}).get("playerDetails", {})

    seen: set[str] = set()
    players: list[dict[str, Any]] = []
    for role_key, role in (("tanks", "tank"), ("healers", "healer"), ("dps", "dps")):
        for entry in player_data.get(role_key, []) or []:
            name = entry.get("name")
            if not name or name in seen:
                continue
            seen.add(name)
            specs_field = entry.get("specs") or []
            spec_name: Optional[str] = None
            if specs_field:
                first = specs_field[0]
                spec_name = first.get("spec") if isinstance(first, dict) else first
            players.append(
                {
                    "id": entry["id"],
                    "name": name,
                    "role": role,
                    "class": (entry.get("type") or "").upper() or None,
                    "spec": spec_name,
                }
            )
    return players


def _fetch_cast_events(
    api_client: WarcraftLogsAPIClient,
    report_code: str,
    fight_ids: list[int],
    spell_id: int,
) -> list[dict[str, Any]]:
    query = """
    query GetCasts(
        $reportCode: String!, $fightIDs: [Int]!, $abilityID: Float!,
        $startTime: Float
    ) {
      reportData {
        report(code: $reportCode) {
          events(
            fightIDs: $fightIDs,
            dataType: Casts,
            hostilityType: Friendlies,
            abilityID: $abilityID,
            useAbilityIDs: true,
            startTime: $startTime,
            limit: 10000
          ) {
            data
            nextPageTimestamp
          }
        }
      }
    }
    """
    events: list[dict[str, Any]] = []
    next_ts: Optional[float] = None
    while True:
        variables = {
            "reportCode": report_code,
            "fightIDs": fight_ids,
            "abilityID": float(spell_id),
            "startTime": next_ts,
        }
        result = api_client.make_request(query, variables)
        block = (
            result.get("data", {})
            .get("reportData", {})
            .get("report", {})
            .get("events")
            or {}
        )
        events.extend(block.get("data") or [])
        next_ts = block.get("nextPageTimestamp")
        if next_ts is None:
            break
    return events


def _fetch_death_events(
    api_client: WarcraftLogsAPIClient,
    report_code: str,
    fight_ids: list[int],
) -> list[dict[str, Any]]:
    query = """
    query GetDeaths(
        $reportCode: String!, $fightIDs: [Int]!, $startTime: Float
    ) {
      reportData {
        report(code: $reportCode) {
          events(
            fightIDs: $fightIDs,
            dataType: Deaths,
            hostilityType: Friendlies,
            startTime: $startTime,
            limit: 10000
          ) {
            data
            nextPageTimestamp
          }
        }
      }
    }
    """
    events: list[dict[str, Any]] = []
    next_ts: Optional[float] = None
    while True:
        result = api_client.make_request(
            query,
            {"reportCode": report_code, "fightIDs": fight_ids, "startTime": next_ts},
        )
        block = (
            result.get("data", {})
            .get("reportData", {})
            .get("report", {})
            .get("events")
            or {}
        )
        events.extend(block.get("data") or [])
        next_ts = block.get("nextPageTimestamp")
        if next_ts is None:
            break
    return events


def _fetch_resurrect_events(
    api_client: WarcraftLogsAPIClient,
    report_code: str,
    fight_ids: list[int],
) -> list[dict[str, Any]]:
    """
    Fetch resurrect-style cast events.

    The WCL ``EventDataType`` enum has no dedicated ``Resurrects`` value, so we
    pull cast events for each known resurrect spell ID. The cast's ``targetID``
    is the player being resurrected (and equals ``sourceID`` for self-rezzes).
    """
    events: list[dict[str, Any]] = []
    for spell_id in _RESURRECT_SPELL_IDS:
        events.extend(_fetch_cast_events(api_client, report_code, fight_ids, spell_id))
    return events


def _fetch_master_abilities(
    api_client: WarcraftLogsAPIClient,
    report_code: str,
) -> dict[int, str]:
    query = """
    query GetAbilities($reportCode: String!) {
      reportData {
        report(code: $reportCode) {
          masterData(translate: true) {
            abilities { gameID name }
          }
        }
      }
    }
    """
    result = api_client.make_request(query, {"reportCode": report_code})
    abilities = (
        result.get("data", {})
        .get("reportData", {})
        .get("report", {})
        .get("masterData", {})
        .get("abilities")
        or []
    )
    out: dict[int, str] = {}
    for a in abilities:
        gid = a.get("gameID")
        name = a.get("name")
        if gid is None or not name:
            continue
        try:
            out[int(gid)] = name
        except (TypeError, ValueError):
            continue
    return out


# --------------------------------------------------------------------------
# Spell-name lookup (spells.yaml + masterData fallback)
# --------------------------------------------------------------------------


def _build_spell_name_lookup() -> dict[int, str]:
    data = load_spells_data() or {}
    out: dict[int, str] = {}
    for class_spells in data.values():
        for spell in class_spells or []:
            sid = spell.get("spellID")
            name = spell.get("name")
            if sid is None or not name:
                continue
            try:
                out[int(sid)] = name
            except (TypeError, ValueError):
                continue
    return out


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------


def check_assignments(
    api_client: WarcraftLogsAPIClient,
    report_codes: list[str],
    note: AssignmentNote,
    margin_seconds: float = 10.0,
    healers_only: bool = False,
) -> ComplianceReport:
    """
    Check, for each report, whether each assignment was honored within ``margin_seconds``.

    A cast counts as on-time if it happened in the same fight, in the same
    phase, and within ``margin_seconds`` of ``phase_start + assignment.time``.

    :param api_client: Authenticated Warcraft Logs API client.
    :param report_codes: List of report codes to check.
    :param note: Parsed assignment note.
    :param margin_seconds: Tolerance window around the expected timestamp.
    :param healers_only: If true, restrict to assignments whose assigned player
        is detected as a healer in at least one of the analyzed reports.
    :returns: A :class:`ComplianceReport` with all rows + metadata.
    """
    margin_ms = int(margin_seconds * 1000)

    # Pass 1: gather participants per report up front so we can apply the
    # healers-only filter before we issue any cast queries.
    per_report_state: list[dict[str, Any]] = []
    name_to_roles: dict[str, set[str]] = defaultdict(set)
    name_to_class: dict[str, str] = {}

    for report_code in report_codes:
        logger.info("Fetching fights for %s", report_code)
        fights, report_start_ms = _fetch_fights_with_phases(
            api_client, report_code, note.encounter_id, note.difficulty
        )
        if not fights:
            logger.warning("No fights found for %s", report_code)
            per_report_state.append({"report_code": report_code, "fights": [], "players": []})
            continue
        fights.sort(key=lambda f: int(f["startTime"]))
        fight_ids = [f["id"] for f in fights]
        players = _fetch_participants(api_client, report_code, fight_ids)
        for p in players:
            name_to_roles[p["name"]].add(p.get("role") or "")
            if p.get("class"):
                name_to_class.setdefault(p["name"], p["class"])
        per_report_state.append(
            {
                "report_code": report_code,
                "fights": fights,
                "report_start_ms": report_start_ms,
                "players": players,
            }
        )

    # Filter assignments.
    assignments = list(note.assignments)
    if healers_only:
        assignments = [
            a for a in assignments
            if "healer" in name_to_roles.get(a.player_name, set())
        ]
        if not assignments:
            logger.warning("No healer assignments matched the players found in the reports")

    # Stable display order: phase, then time, then player name.
    assignments.sort(key=lambda a: (a.phase, a.time_seconds, a.player_name))

    # Build spell-name lookup from spells.yaml.
    spell_names = _build_spell_name_lookup()

    # Track which spell IDs we still need names for.
    needed_spell_ids = {a.spell_id for a in assignments if a.spell_id not in spell_names}
    # Use the set of unique spell IDs across all assignments for cast queries.
    query_spell_ids = sorted({a.spell_id for a in assignments})

    fights_out: list[FightInfo] = []
    results_by_key: dict[tuple[str, int, int], AssignmentResult] = {}

    for state in per_report_state:
        report_code: str = state["report_code"]
        fights: list[dict[str, Any]] = state["fights"]
        players: list[dict[str, Any]] = state["players"]
        if not fights:
            continue

        id_to_player = {p["id"]: p for p in players}
        name_to_id = {p["name"]: p["id"] for p in players}
        fight_ids = [f["id"] for f in fights]

        # Fill in any still-missing spell names from masterData.
        if needed_spell_ids:
            master = _fetch_master_abilities(api_client, report_code)
            for sid in list(needed_spell_ids):
                if sid in master:
                    spell_names[sid] = master[sid]
                    needed_spell_ids.discard(sid)

        # Build a death/resurrect timeline per (fight, player). Each entry is
        # ``(timestamp_ms, kind)`` where ``kind`` is ``"death"`` or ``"rez"``.
        # A player is dead at time T iff the latest event at or before T is a death.
        life_events: dict[int, dict[str, list[tuple[int, str]]]] = defaultdict(
            lambda: defaultdict(list)
        )
        for ev in _fetch_death_events(api_client, report_code, fight_ids):
            target = id_to_player.get(ev.get("targetID"))
            fight_id = ev.get("fight")
            if not target or fight_id is None:
                continue
            life_events[fight_id][target["name"]].append(
                (int(ev.get("timestamp", 0)), "death")
            )
        for ev in _fetch_resurrect_events(api_client, report_code, fight_ids):
            target = id_to_player.get(ev.get("targetID"))
            fight_id = ev.get("fight")
            if not target or fight_id is None:
                continue
            life_events[fight_id][target["name"]].append(
                (int(ev.get("timestamp", 0)), "rez")
            )
        for fight_map in life_events.values():
            for events in fight_map.values():
                events.sort(key=lambda kv: kv[0])

        # Fetch cast events once per spell, then bucket by (player, spell).
        casts: dict[str, dict[int, list[tuple[int, int]]]] = defaultdict(lambda: defaultdict(list))
        for spell_id in query_spell_ids:
            for ev in _fetch_cast_events(api_client, report_code, fight_ids, spell_id):
                if ev.get("type") == "begincast":
                    continue
                if ev.get("type") not in (None, "cast"):
                    continue
                player = id_to_player.get(ev.get("sourceID"))
                if not player:
                    continue
                casts[player["name"]][spell_id].append(
                    (ev.get("fight"), int(ev.get("timestamp", 0)))
                )

        for pull_idx, fight in enumerate(fights, start=1):
            fight_id = fight["id"]
            fight_start = int(fight["startTime"])
            fight_end = int(fight["endTime"])
            phase_starts: dict[int, int] = {1: fight_start}
            for pt in fight.get("phaseTransitions") or []:
                phase_starts[int(pt["id"])] = int(pt["startTime"])

            fights_out.append(
                FightInfo(
                    report_code=report_code,
                    fight_id=fight_id,
                    start_time_ms=fight_start,
                    end_time_ms=fight_end,
                    pull_index=pull_idx,
                )
            )

            for a_idx, assignment in enumerate(assignments):
                phase_reached = assignment.phase in phase_starts
                player = id_to_player.get(name_to_id.get(assignment.player_name))
                expected_ms = (
                    phase_starts[assignment.phase] + assignment.time_seconds * 1000
                    if phase_reached else 0
                )
                best_offset_ms: Optional[int] = None
                if phase_reached:
                    for cast_fight, ts in casts.get(assignment.player_name, {}).get(
                        assignment.spell_id, []
                    ):
                        if cast_fight != fight_id:
                            continue
                        offset = ts - expected_ms
                        if best_offset_ms is None or abs(offset) < abs(best_offset_ms):
                            best_offset_ms = offset
                hit = (
                    phase_reached
                    and best_offset_ms is not None
                    and abs(best_offset_ms) <= margin_ms
                )

                # "Dead at the call" = MISSING (no cast at all in this fight)
                # AND the player was dead through the *entire* on-time window
                # ``[expected - margin, expected + margin]``. Any rez inside
                # that window — or being alive at its start — clears the flag.
                player_dead = False
                if (
                    phase_reached
                    and best_offset_ms is None
                    and assignment.player_name in name_to_id
                ):
                    timeline = life_events.get(fight_id, {}).get(
                        assignment.player_name, []
                    )
                    window_start = expected_ms - margin_ms
                    window_end = expected_ms + margin_ms

                    state_at_start = "alive"
                    for ts, kind in timeline:
                        if ts > window_start:
                            break
                        state_at_start = "dead" if kind == "death" else "alive"

                    rez_in_window = any(
                        kind == "rez" and window_start <= ts <= window_end
                        for ts, kind in timeline
                    )
                    if state_at_start == "dead" and not rez_in_window:
                        player_dead = True

                result = AssignmentResult(
                    report_code=report_code,
                    fight_id=fight_id,
                    phase=assignment.phase,
                    expected_time_seconds=assignment.time_seconds,
                    expected_timestamp_ms=expected_ms,
                    player_name=assignment.player_name,
                    spell_id=assignment.spell_id,
                    spell_name=spell_names.get(
                        assignment.spell_id, f"Spell {assignment.spell_id}"
                    ),
                    boss_spell_id=assignment.boss_spell_id,
                    text=assignment.text,
                    hit=hit,
                    actual_offset_seconds=(
                        best_offset_ms / 1000.0 if best_offset_ms is not None else None
                    ),
                    player_in_roster=assignment.player_name in name_to_id,
                    phase_reached=phase_reached,
                    player_dead=player_dead,
                    player_role=(player or {}).get("role"),
                    player_class=(player or {}).get("class")
                    or name_to_class.get(assignment.player_name),
                )
                results_by_key[(report_code, fight_id, a_idx)] = result

    # Make sure every assignment has a spell name (fallback).
    for a in assignments:
        spell_names.setdefault(a.spell_id, f"Spell {a.spell_id}")

    return ComplianceReport(
        note=note,
        margin_seconds=margin_seconds,
        assignments=assignments,
        fights=fights_out,
        results=results_by_key,
        spell_names=spell_names,
    )


def summarize_results(report: ComplianceReport) -> str:
    """
    Render a human-readable text summary of assignment compliance.

    :param report: A :class:`ComplianceReport` produced by :func:`check_assignments`.
    :returns: Multi-line text report.
    """
    lines: list[str] = []
    by_report: dict[str, list[AssignmentResult]] = defaultdict(list)
    for row in report.results.values():
        by_report[row.report_code].append(row)

    for report_code, rows in by_report.items():
        lines.append("")
        lines.append(f"=== Report {report_code} ===")

        per_player_hits: dict[str, list[int]] = defaultdict(lambda: [0, 0])
        for row in rows:
            if not row.phase_reached or not row.player_in_roster:
                continue
            per_player_hits[row.player_name][1] += 1
            if row.hit:
                per_player_hits[row.player_name][0] += 1

        if per_player_hits:
            lines.append("")
            lines.append("Per-player compliance:")
            lines.append(f"  {'Player':<20} {'Hits':>6} {'Total':>6} {'Rate':>7}")
            for name in sorted(per_player_hits):
                hits, total = per_player_hits[name]
                rate = (hits / total * 100.0) if total else 0.0
                lines.append(f"  {name:<20} {hits:>6} {total:>6} {rate:>6.1f}%")

    return "\n".join(lines).lstrip("\n")
