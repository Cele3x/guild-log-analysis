"""Tests for the CD assignment compliance checker."""

from unittest.mock import MagicMock

import matplotlib
matplotlib.use("Agg")  # noqa: E402

from guild_log_analysis.analysis.cd_assignments import (  # noqa: E402
    check_assignments,
    parse_assignment_note,
)
from guild_log_analysis.plotting.cd_assignments import CDAssignmentsPlot  # noqa: E402


SAMPLE_NOTE = """\
EncounterID:3306;Difficulty:Mythic;Name:Chimaerus

time:9;ph:1;bossSpell:1258610;tag:Neothion;spellid:472433;
time:26;ph:1;bossSpell:1246621;tag:Tharand;spellid:200183;
time:10;ph:2;tag:Neothion;spellid:472433;
time:19;ph:1;tag:Kuhwabanga Erâsêr Tharand;text:Group Soak;
time:191;ph:1;bossSpell:1245452;tag:Drakaschy;spellid:359816;text:Filler DF;
"""


def _mock_api(fights, players, casts_by_spell, abilities=None, deaths=None):
    api = MagicMock()

    def make_request(query, variables):
        if "fights(encounterID" in query:
            return {
                "data": {
                    "reportData": {
                        "report": {"startTime": 1_700_000_000_000, "fights": fights}
                    }
                }
            }
        if "playerDetails" in query:
            return {
                "data": {
                    "reportData": {
                        "report": {
                            "playerDetails": {
                                "data": {"playerDetails": players}
                            }
                        }
                    }
                }
            }
        if "GetDeaths" in query or "dataType: Deaths" in query:
            return {
                "data": {
                    "reportData": {
                        "report": {
                            "events": {
                                "data": deaths or [],
                                "nextPageTimestamp": None,
                            }
                        }
                    }
                }
            }
        if "Casts" in query:
            spell = int(variables["abilityID"])
            return {
                "data": {
                    "reportData": {
                        "report": {
                            "events": {
                                "data": casts_by_spell.get(spell, []),
                                "nextPageTimestamp": None,
                            }
                        }
                    }
                }
            }
        if "masterData" in query:
            return {
                "data": {
                    "reportData": {
                        "report": {
                            "masterData": {"abilities": abilities or []}
                        }
                    }
                }
            }
        raise AssertionError(f"unexpected query: {query[:80]}")

    api.make_request.side_effect = make_request
    return api


def test_parse_header_and_filtering() -> None:
    note = parse_assignment_note(SAMPLE_NOTE)
    assert note.encounter_id == 3306
    assert note.difficulty == 5
    assert note.name == "Chimaerus"
    assert len(note.assignments) == 4  # group-soak line skipped


def test_check_assignments_hits_within_margin() -> None:
    note = parse_assignment_note(SAMPLE_NOTE)
    fights = [
        {
            "id": 1,
            "startTime": 1000,
            "endTime": 500_000,
            "phaseTransitions": [{"id": 2, "startTime": 200_000}],
        }
    ]
    players = {
        "tanks": [],
        "healers": [{"id": 100, "name": "Neothion", "type": "shaman", "specs": ["Restoration"]}],
        "dps": [
            {"id": 101, "name": "Tharand", "type": "monk", "specs": ["Mistweaver"]},
            {"id": 102, "name": "Drakaschy", "type": "evoker", "specs": ["Devastation"]},
        ],
    }
    casts = {
        472433: [
            {"type": "cast", "sourceID": 100, "fight": 1, "timestamp": 12_000},
            {"type": "cast", "sourceID": 100, "fight": 1, "timestamp": 215_000},
        ],
        200183: [
            {"type": "cast", "sourceID": 101, "fight": 1, "timestamp": 40_000},
        ],
        359816: [],
    }
    api = _mock_api(fights, players, casts, abilities=[
        {"gameID": 472433, "name": "Spirit Link Totem"},
        {"gameID": 200183, "name": "Revival"},
        {"gameID": 359816, "name": "Dream Flight"},
    ])

    report = check_assignments(api, ["abc"], note, margin_seconds=10.0)

    assert len(report.assignments) == 4
    assert len(report.fights) == 1

    # Locate results by (player, phase, time)
    by_id = {
        (a.player_name, a.phase, a.time_seconds): a_idx
        for a_idx, a in enumerate(report.assignments)
    }

    n_p1 = report.results[("abc", 1, by_id[("Neothion", 1, 9)])]
    assert n_p1.hit is True
    assert n_p1.actual_offset_seconds == 2.0
    assert n_p1.spell_name and not n_p1.spell_name.startswith("Spell ")

    n_p2 = report.results[("abc", 1, by_id[("Neothion", 2, 10)])]
    assert n_p2.hit is True

    t_p1 = report.results[("abc", 1, by_id[("Tharand", 1, 26)])]
    assert t_p1.hit is False
    assert t_p1.actual_offset_seconds == 13.0

    d_p1 = report.results[("abc", 1, by_id[("Drakaschy", 1, 191)])]
    assert d_p1.hit is False
    assert d_p1.actual_offset_seconds is None  # MISSING


def test_healers_only_filters_assignments() -> None:
    note = parse_assignment_note(SAMPLE_NOTE)
    players = {
        "tanks": [],
        "healers": [{"id": 100, "name": "Neothion", "type": "shaman", "specs": ["Restoration"]}],
        "dps": [
            {"id": 101, "name": "Tharand", "type": "monk", "specs": ["Windwalker"]},
            {"id": 102, "name": "Drakaschy", "type": "evoker", "specs": ["Devastation"]},
        ],
    }
    fights = [{"id": 1, "startTime": 0, "endTime": 1000, "phaseTransitions": []}]
    api = _mock_api(fights, players, {}, abilities=[])

    report = check_assignments(
        api, ["abc"], note, margin_seconds=10.0, healers_only=True
    )

    assert {a.player_name for a in report.assignments} == {"Neothion"}


def test_phase_not_reached_marks_skipped() -> None:
    note = parse_assignment_note(
        "EncounterID:3306;Difficulty:Mythic;Name:Chimaerus\n"
        "time:5;ph:3;tag:Neothion;spellid:472433;\n"
    )
    fights = [{"id": 1, "startTime": 0, "endTime": 1000, "phaseTransitions": []}]
    players = {
        "tanks": [],
        "healers": [{"id": 100, "name": "Neothion", "type": "shaman", "specs": ["Restoration"]}],
        "dps": [],
    }
    api = _mock_api(fights, players, {}, abilities=[])

    report = check_assignments(api, ["abc"], note, margin_seconds=10.0)
    assert len(report.results) == 1
    only = next(iter(report.results.values()))
    assert only.phase_reached is False
    assert only.hit is False


def test_player_dead_marks_dead_when_no_cast() -> None:
    note = parse_assignment_note(
        "EncounterID:3306;Difficulty:Mythic;Name:Chimaerus\n"
        "time:30;ph:1;tag:Neothion;spellid:472433;\n"
    )
    fights = [{"id": 1, "startTime": 0, "endTime": 200_000, "phaseTransitions": []}]
    players = {
        "tanks": [],
        "healers": [{"id": 100, "name": "Neothion", "type": "shaman", "specs": ["Restoration"]}],
        "dps": [],
    }
    # Player died at 15s, expected at 30s, no cast
    deaths = [{"type": "death", "targetID": 100, "fight": 1, "timestamp": 15_000}]
    api = _mock_api(fights, players, {}, abilities=[], deaths=deaths)

    report = check_assignments(api, ["abc"], note, margin_seconds=10.0)
    only = next(iter(report.results.values()))
    assert only.hit is False
    assert only.player_dead is True
    assert only.actual_offset_seconds is None


def test_resurrect_before_call_clears_dead_flag() -> None:
    note = parse_assignment_note(
        "EncounterID:3306;Difficulty:Mythic;Name:Chimaerus\n"
        "time:30;ph:1;tag:Neothion;spellid:472433;\n"
    )
    fights = [{"id": 1, "startTime": 0, "endTime": 200_000, "phaseTransitions": []}]
    players = {
        "tanks": [],
        "healers": [{"id": 100, "name": "Neothion", "type": "shaman", "specs": ["Restoration"]}],
        "dps": [],
    }
    # Died at 10s, rezzed at 20s, expected at 30s, but did not cast → MISSING (not dead).
    deaths = [{"type": "death", "targetID": 100, "fight": 1, "timestamp": 10_000}]
    # Rez modeled as a cast of Ancestral Spirit (2008) targeting Neothion (id=100).
    casts = {2008: [{"type": "cast", "sourceID": 200, "targetID": 100, "fight": 1, "timestamp": 20_000}]}
    api = _mock_api(fights, players, casts, abilities=[], deaths=deaths)

    report = check_assignments(api, ["abc"], note, margin_seconds=5.0)
    only = next(iter(report.results.values()))
    assert only.player_dead is False
    assert only.hit is False
    assert only.actual_offset_seconds is None  # missing, not dead


def test_died_again_after_rez_marks_dead() -> None:
    note = parse_assignment_note(
        "EncounterID:3306;Difficulty:Mythic;Name:Chimaerus\n"
        "time:60;ph:1;tag:Neothion;spellid:472433;\n"
    )
    fights = [{"id": 1, "startTime": 0, "endTime": 200_000, "phaseTransitions": []}]
    players = {
        "tanks": [],
        "healers": [{"id": 100, "name": "Neothion", "type": "shaman", "specs": ["Restoration"]}],
        "dps": [],
    }
    # Died, rezzed, died again, all before expected at 60s.
    deaths = [
        {"type": "death", "targetID": 100, "fight": 1, "timestamp": 10_000},
        {"type": "death", "targetID": 100, "fight": 1, "timestamp": 50_000},
    ]
    casts = {2008: [{"type": "cast", "sourceID": 200, "targetID": 100, "fight": 1, "timestamp": 30_000}]}
    api = _mock_api(fights, players, casts, abilities=[], deaths=deaths)

    report = check_assignments(api, ["abc"], note, margin_seconds=5.0)
    only = next(iter(report.results.values()))
    assert only.player_dead is True


def test_rez_inside_margin_window_clears_dead() -> None:
    note = parse_assignment_note(
        "EncounterID:3306;Difficulty:Mythic;Name:Chimaerus\n"
        "time:30;ph:1;tag:Neothion;spellid:472433;\n"
    )
    fights = [{"id": 1, "startTime": 0, "endTime": 200_000, "phaseTransitions": []}]
    players = {
        "tanks": [],
        "healers": [{"id": 100, "name": "Neothion", "type": "shaman", "specs": ["Restoration"]}],
        "dps": [],
    }
    # Died at 5s, rezzed at 28s. Expected at 30s, margin=10s → window [20s, 40s].
    # Player was dead at window start, but rez at 28s is inside the window → not dead.
    deaths = [{"type": "death", "targetID": 100, "fight": 1, "timestamp": 5_000}]
    casts = {2008: [{"type": "cast", "sourceID": 200, "targetID": 100, "fight": 1, "timestamp": 28_000}]}
    api = _mock_api(fights, players, casts, abilities=[], deaths=deaths)

    report = check_assignments(api, ["abc"], note, margin_seconds=10.0)
    only = next(iter(report.results.values()))
    assert only.player_dead is False


def test_plot_renders_without_error() -> None:
    note = parse_assignment_note(SAMPLE_NOTE)
    fights = [
        {"id": 1, "startTime": 0, "endTime": 200_000, "phaseTransitions": []},
        {"id": 2, "startTime": 0, "endTime": 300_000, "phaseTransitions": []},
    ]
    players = {
        "tanks": [],
        "healers": [{"id": 100, "name": "Neothion", "type": "shaman", "specs": ["Restoration"]}],
        "dps": [
            {"id": 101, "name": "Tharand", "type": "monk", "specs": ["Mistweaver"]},
            {"id": 102, "name": "Drakaschy", "type": "evoker", "specs": ["Devastation"]},
        ],
    }
    casts = {
        472433: [{"type": "cast", "sourceID": 100, "fight": 1, "timestamp": 9_000}],
        200183: [],
        359816: [],
    }
    api = _mock_api(fights, players, casts, abilities=[])
    report = check_assignments(api, ["abc"], note, margin_seconds=10.0)

    plot = CDAssignmentsPlot(report, title="Chimaerus", date="30.04.2026")
    fig = plot.create_figure()
    assert fig is not None
    import matplotlib.pyplot as plt
    plt.close(fig)
