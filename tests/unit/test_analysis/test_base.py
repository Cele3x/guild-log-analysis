"""Tests for base analysis functionality."""

from typing import Set
from unittest.mock import Mock, patch

import pytest

from src.guild_log_analysis.analysis.base import BossAnalysisBase
from src.guild_log_analysis.api import DataNotFoundError, WarcraftLogsAPIClient


class ConcreteBossAnalysis(BossAnalysisBase):
    """Concrete implementation of BossAnalysisBase for testing."""

    def analyze(self, report_codes, **kwargs):
        """Test implementation of analyze method."""
        pass

    def get_fight_ids(self, report_code: str) -> Set[int]:
        """Test implementation of get_fight_ids method."""
        return {1, 2, 3}


class TestBossAnalysisBase:
    """Test cases for BossAnalysisBase class."""

    def test_init(self, mock_api_client):
        """Test BossAnalysisBase initialization."""
        analysis = ConcreteBossAnalysis(mock_api_client)

        assert analysis.api_client == mock_api_client
        assert analysis.boss_id is None
        assert analysis.boss_name is None
        assert analysis.encounter_id is None
        assert analysis.results == []

    def test_get_start_time_success(self, mock_api_client, sample_api_response):
        """Test successful start time retrieval."""
        mock_api_client.make_request.return_value = sample_api_response

        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis.get_start_time("test_report", {1, 2})

        # Expected: (1640995200000 + 0) / 1000 = 1640995200.0
        assert result == 1640995200.0
        mock_api_client.make_request.assert_called_once()

    def test_get_start_time_no_report(self, mock_api_client):
        """Test start time retrieval with no report found."""
        mock_api_client.make_request.return_value = {
            "data": {"reportData": {"report": None}}
        }

        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis.get_start_time("test_report", {1, 2})

        assert result is None

    def test_get_start_time_no_fights(self, mock_api_client):
        """Test start time retrieval with no fights found."""
        mock_api_client.make_request.return_value = {
            "data": {
                "reportData": {"report": {"startTime": 1640995200000, "fights": []}}
            }
        }

        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis.get_start_time("test_report", {1, 2})

        assert result is None

    def test_get_total_fight_duration_success(
        self, mock_api_client, sample_api_response
    ):
        """Test successful fight duration calculation."""
        mock_api_client.make_request.return_value = sample_api_response

        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis.get_total_fight_duration("test_report", {1, 2})

        # Expected: (300000 - 0) + (700000 - 400000) = 300000 + 300000 = 600000
        assert result == 600000
        mock_api_client.make_request.assert_called_once()

    def test_get_participants_success(
        self, mock_api_client, sample_player_details_response
    ):
        """Test successful participant retrieval."""
        mock_api_client.make_request.return_value = sample_player_details_response

        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis.get_participants("test_report", {1, 2})

        assert len(result) == 3

    def test_get_participants_no_data(self, mock_api_client):
        """Test participant retrieval with no data."""
        mock_api_client.make_request.return_value = {
            "data": {"reportData": {"report": {"playerDetails": None}}}
        }

        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis.get_participants("test_report", {1, 2})

        assert result is None

    def test_find_analysis_data_success(self, mock_api_client, sample_analysis_results):
        """Test successful analysis data finding."""
        analysis = ConcreteBossAnalysis(mock_api_client)
        analysis.results = sample_analysis_results

        current_data, previous_dict = analysis.find_analysis_data(
            "Overload! Interrupts", "interrupts", "player_name"
        )

        assert len(current_data) == 2

        assert "TestPlayer1" in previous_dict
        assert previous_dict["TestPlayer1"] == 3
        assert "TestPlayer2" in previous_dict
        assert previous_dict["TestPlayer2"] == 1

    def test_find_analysis_data_not_found(self, mock_api_client):
        """Test analysis data finding with no matching analysis."""
        analysis = ConcreteBossAnalysis(mock_api_client)
        analysis.results = []

        with pytest.raises(ValueError):
            analysis.find_analysis_data(
                "NonexistentAnalysis", "some_column", "name_column"
            )

    def test_get_damage_to_actor_success(
        self,
        mock_api_client,
        sample_actors_response,
        sample_damage_response,
        sample_players_data,
    ):
        """Test successful damage to actor retrieval."""
        # Mock the API calls
        mock_api_client.make_request.side_effect = [
            sample_actors_response,  # First call for actors
            sample_damage_response,  # Second call for damage data
        ]

        analysis = ConcreteBossAnalysis(mock_api_client)
        analysis.encounter_id = 3014
        analysis.difficulty = 5

        result = analysis.get_damage_to_actor(
            "test_report",
            {1, 2},
            231027,  # Premium Dynamite game ID
            sample_players_data,
        )

        assert len(result) == 3  # All players should be in result
        # Find TestPlayer1 in results
        player1_data = next(
            (p for p in result if p["player_name"] == "TestPlayer1"), None
        )
        assert player1_data is not None

    def test_get_damage_to_actor_no_targets(self, mock_api_client, sample_players_data):
        """Test damage to actor retrieval with no matching targets."""
        # Mock actors response with no matching game ID
        actors_response = {
            "data": {
                "reportData": {
                    "report": {
                        "masterData": {
                            "actors": [
                                {
                                    "id": 100,
                                    "name": "Other Enemy",
                                    "gameID": 999999,  # Different game ID
                                    "type": "NPC",
                                    "subType": "Enemy",
                                }
                            ]
                        }
                    }
                }
            }
        }

        mock_api_client.make_request.return_value = actors_response

        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis.get_damage_to_actor(
            "test_report",
            {1, 2},
            231027,  # Premium Dynamite game ID
            sample_players_data,
        )

        assert result == []

    def test_analyze_interrupts_success(
        self, mock_api_client, sample_interrupt_events, sample_players_data
    ):
        """Test successful interrupt analysis."""
        mock_api_client.make_request.return_value = sample_interrupt_events

        analysis = ConcreteBossAnalysis(mock_api_client)
        analysis.encounter_id = 3014
        analysis.difficulty = 5
        result = analysis.analyze_interrupts(
            "test_report", {1, 2}, sample_players_data, 460582.0
        )

        assert len(result) == 3  # All players should be in result
        # Find TestPlayer1 in results
        player1_data = next(
            (p for p in result if p["player_name"] == "TestPlayer1"), None
        )
        assert player1_data is not None

    def test_analyze_debuff_uptime_success(
        self, mock_api_client, sample_debuff_events, sample_players_data
    ):
        """Test successful debuff uptime analysis."""
        # Mock the debuff uptime table response
        debuff_table_response = {
            "data": {
                "reportData": {
                    "report": {
                        "table": {
                            "data": {
                                "totalTime": 20000,  # 20 seconds total
                                "auras": [
                                    {
                                        "name": "TestPlayer1",
                                        "totalUptime": 5000,  # 5 seconds uptime = 25%
                                    },
                                    {
                                        "name": "TestPlayer2",
                                        "totalUptime": 10000,  # 10 seconds uptime = 50%
                                    },
                                ],
                            }
                        }
                    }
                }
            }
        }

        mock_api_client.make_request.return_value = debuff_table_response

        analysis = ConcreteBossAnalysis(mock_api_client)
        analysis.encounter_id = 3014
        analysis.difficulty = 5
        result = analysis.analyze_debuff_uptime(
            "test_report", {1, 2}, sample_players_data, 460444.0
        )

        assert len(result) == 3  # All players should be in result
        # Find TestPlayer1 in results
        player1_data = next(
            (p for p in result if p["player_name"] == "TestPlayer1"), None
        )
        assert player1_data is not None
        # Should have some uptime percentage (exact calculation depends on implementation)

    def test_calculate_debuff_uptime_no_events(self, mock_api_client):
        """Test debuff uptime calculation with no events."""
        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis._calculate_debuff_uptime([], "TestPlayer", 10000)

        assert result == 0.0

    def test_calculate_debuff_uptime_with_events(self, mock_api_client):
        """Test debuff uptime calculation with events."""
        events = [
            {
                "type": "applydebuff",
                "timestamp": 1000,
                "targetName": "TestPlayer",
                "abilityGameID": 460444,
            },
            {
                "type": "removedebuff",
                "timestamp": 3000,
                "targetName": "TestPlayer",
                "abilityGameID": 460444,
            },
        ]

        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis._calculate_debuff_uptime(events, "TestPlayer", 10000)

        # 2000ms uptime out of 10000ms total = 20%
        assert result == 20.0
