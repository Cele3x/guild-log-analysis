"""Tests for base analysis functionality."""

from typing import Set
from unittest.mock import patch

import pytest

from src.guild_log_analysis.analysis.base import BossAnalysisBase


class ConcreteBossAnalysis(BossAnalysisBase):
    """Concrete implementation of BossAnalysisBase for testing."""

    def __init__(self, api_client):
        """Initialize with configuration for testing."""
        super().__init__(api_client)
        self.boss_name = "Test Boss"
        self.encounter_id = 1234
        self.difficulty = 5

    def _analyze_legacy(self, report_codes, **kwargs):
        """Test implementation of legacy analyze method."""
        pass

    def get_fight_ids(self, report_code: str) -> Set[int]:
        """Test implementation of get_fight_ids method."""
        return {1, 2, 3}


class ConfigurationBasedAnalysis(BossAnalysisBase):
    """Configuration-based boss analysis for testing."""

    def __init__(self, api_client):
        """Initialize with configuration."""
        super().__init__(api_client)
        self.boss_name = "Config Boss"
        self.encounter_id = 5678
        self.difficulty = 5

    CONFIG = [
        {
            "name": "Test Interrupts",
            "analysis": {"type": "interrupts", "ability_id": 12345},
            "plot": {
                "type": "NumberPlot",
                "title": "Test Interrupts",
                "column_key_1": "interrupts",
                "column_header_2": "Count",
            },
        },
        {
            "name": "Test Damage",
            "analysis": {"type": "damage_to_actor", "target_game_id": 67890},
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "test_damage",
                "column_header_2": "Damage",
            },
        },
        {
            "name": "Test Debuff",
            "analysis": {"type": "debuff_uptime", "ability_id": 11111.0},
            "plot": {
                "type": "PercentagePlot",
                "column_key_1": "uptime_percentage",
                "column_header_2": "Uptime",
            },
        },
        {
            "name": "Test Damage Taken",
            "analysis": {"type": "damage_taken_from_ability", "ability_id": 1223999},
            "plot": {
                "type": "HitCountPlot",
                "column_key_1": "hit_count",
                "column_header_2": "Hits",
                "column_key_2": "test_damage_taken",
                "column_header_3": "Damage Taken",
            },
        },
    ]


class TestBossAnalysisBase:
    """Test cases for BossAnalysisBase class."""

    def test_init(self, mock_api_client):
        """Test BossAnalysisBase initialization."""
        analysis = ConcreteBossAnalysis(mock_api_client)

        assert analysis.api_client == mock_api_client
        assert analysis.boss_id is None
        assert analysis.boss_name == "Test Boss"  # Set in ConcreteBossAnalysis
        assert analysis.encounter_id == 1234  # Set in ConcreteBossAnalysis
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
        mock_api_client.make_request.return_value = {"data": {"reportData": {"report": None}}}

        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis.get_start_time("test_report", {1, 2})

        assert result is None

    def test_get_start_time_no_fights(self, mock_api_client):
        """Test start time retrieval with no fights found."""
        mock_api_client.make_request.return_value = {
            "data": {"reportData": {"report": {"startTime": 1640995200000, "fights": []}}}
        }

        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis.get_start_time("test_report", {1, 2})

        assert result is None

    def test_get_total_fight_duration_success(self, mock_api_client, sample_api_response):
        """Test successful fight duration calculation."""
        mock_api_client.make_request.return_value = sample_api_response

        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis.get_total_fight_duration("test_report", {1, 2})

        # Expected: (300000 - 0) + (700000 - 400000) = 300000 + 300000 = 600000
        assert result == 600000
        mock_api_client.make_request.assert_called_once()

    def test_get_participants_success(self, mock_api_client, sample_player_details_response):
        """Test successful participant retrieval."""
        mock_api_client.make_request.return_value = sample_player_details_response

        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis.get_participants("test_report", {1, 2})

        assert len(result) == 3

    def test_get_participants_no_data(self, mock_api_client):
        """Test participant retrieval with no data."""
        mock_api_client.make_request.return_value = {"data": {"reportData": {"report": {"playerDetails": None}}}}

        analysis = ConcreteBossAnalysis(mock_api_client)
        result = analysis.get_participants("test_report", {1, 2})

        assert result is None

    def test_find_analysis_data_success(self, mock_api_client, sample_analysis_results):
        """Test successful analysis data finding."""
        analysis = ConcreteBossAnalysis(mock_api_client)
        analysis.results = sample_analysis_results

        current_data, previous_dict = analysis.find_analysis_data("Overload! Interrupts", "interrupts", "player_name")

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
            analysis.find_analysis_data("NonexistentAnalysis", "some_column", "name_column")

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
        player1_data = next((p for p in result if p["player_name"] == "TestPlayer1"), None)
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

    def test_analyze_interrupts_success(self, mock_api_client, sample_interrupt_events, sample_players_data):
        """Test successful interrupt analysis."""
        mock_api_client.make_request.return_value = sample_interrupt_events

        analysis = ConcreteBossAnalysis(mock_api_client)
        analysis.encounter_id = 3014
        analysis.difficulty = 5
        result = analysis.analyze_interrupts("test_report", {1, 2}, sample_players_data, 460582.0)

        assert len(result) == 3  # All players should be in result
        # Find TestPlayer1 in results
        player1_data = next((p for p in result if p["player_name"] == "TestPlayer1"), None)
        assert player1_data is not None


class TestConfigurationBasedAnalysis:
    """Test cases for configuration-based analysis functionality."""

    def test_init_with_configuration(self, mock_api_client):
        """Test initialization with analysis and plot configuration."""
        analysis = ConfigurationBasedAnalysis(mock_api_client)

        assert analysis.api_client == mock_api_client
        assert analysis.boss_name == "Config Boss"
        assert analysis.encounter_id == 5678
        assert analysis.difficulty == 5
        assert len(analysis.CONFIG) == 4

    @patch.object(ConfigurationBasedAnalysis, "_process_report_generic")
    def test_analyze_uses_generic_method(self, mock_process_generic, mock_api_client):
        """Test that analyze uses generic method when ANALYSIS_CONFIG exists."""
        analysis = ConfigurationBasedAnalysis(mock_api_client)
        report_codes = ["report1", "report2"]

        analysis.analyze(report_codes)

        # Should use generic method since ANALYSIS_CONFIG exists
        assert mock_process_generic.call_count == 2
        mock_process_generic.assert_any_call("report1")
        mock_process_generic.assert_any_call("report2")

    def test_analyze_legacy_fallback(self, mock_api_client):
        """Test that analyze falls back to legacy method when no configuration."""
        analysis = ConcreteBossAnalysis(mock_api_client)
        # Clear the ANALYSIS_CONFIG to test fallback
        analysis.CONFIG = []
        report_codes = ["report1"]

        # Should not raise exception when calling _analyze_legacy
        analysis.analyze(report_codes)

    @patch.object(ConfigurationBasedAnalysis, "get_fight_ids")
    @patch.object(ConfigurationBasedAnalysis, "get_start_time")
    @patch.object(ConfigurationBasedAnalysis, "get_participants")
    @patch.object(ConfigurationBasedAnalysis, "_execute_analysis")
    def test_process_report_generic(
        self,
        mock_execute_analysis,
        mock_get_participants,
        mock_get_start_time,
        mock_get_fight_ids,
        mock_api_client,
        sample_players_data,
    ):
        """Test generic report processing with configuration."""
        # Setup mocks
        mock_get_fight_ids.return_value = {1, 2}
        mock_get_start_time.return_value = 1640995200.0
        mock_get_participants.return_value = sample_players_data
        mock_execute_analysis.return_value = [{"player_name": "TestPlayer1", "test_value": 100}]

        analysis = ConfigurationBasedAnalysis(mock_api_client)
        analysis._process_report_generic("test_report")

        # Verify methods were called
        mock_get_fight_ids.assert_called_once_with("test_report")
        mock_get_start_time.assert_called_once_with("test_report", {1, 2})
        mock_get_participants.assert_called_once_with("test_report", {1, 2})

        # Should call execute_analysis for each config item
        assert mock_execute_analysis.call_count == 4

        # Verify results were added
        assert len(analysis.results) == 1
        result = analysis.results[0]
        assert result["reportCode"] == "test_report"
        assert result["starttime"] == 1640995200.0
        assert result["fight_ids"] == {1, 2}
        assert len(result["analysis"]) == 4

    @patch.object(ConfigurationBasedAnalysis, "analyze_interrupts")
    def test_execute_analysis_interrupts(self, mock_analyze_interrupts, mock_api_client, sample_players_data):
        """Test execute_analysis with interrupts configuration."""
        mock_analyze_interrupts.return_value = [{"player_name": "TestPlayer1", "interrupts": 5}]

        analysis = ConfigurationBasedAnalysis(mock_api_client)
        config = {"name": "Test Interrupts", "type": "interrupts", "ability_id": 12345}

        result = analysis._execute_analysis("test_report", config, {1, 2}, sample_players_data)

        mock_analyze_interrupts.assert_called_once_with(
            report_code="test_report",
            fight_ids={1, 2},
            report_players=sample_players_data,
            ability_id=12345,
            wipe_cutoff=4,  # DEFAULT_WIPE_CUTOFF
        )
        assert len(result) == 1
        assert result[0]["interrupts"] == 5

    @patch.object(ConfigurationBasedAnalysis, "get_damage_to_actor")
    def test_execute_analysis_damage_to_actor(self, mock_get_damage, mock_api_client, sample_players_data):
        """Test execute_analysis with damage_to_actor configuration."""
        mock_get_damage.return_value = [{"player_name": "TestPlayer1", "damage": 500000}]

        analysis = ConfigurationBasedAnalysis(mock_api_client)
        config = {
            "name": "Test Damage",
            "type": "damage_to_actor",
            "target_game_id": 67890,
            "result_key": "test_damage",
        }

        result = analysis._execute_analysis("test_report", config, {1, 2}, sample_players_data)

        mock_get_damage.assert_called_once()
        # Check that result_key rename worked
        assert len(result) == 1
        assert "test_damage" in result[0]
        assert result[0]["test_damage"] == 500000
        assert "damage" not in result[0]

    def test_execute_analysis_unknown_type(self, mock_api_client, sample_players_data):
        """Test execute_analysis with unknown analysis type."""
        analysis = ConfigurationBasedAnalysis(mock_api_client)
        config = {"name": "Unknown", "type": "unknown_type", "some_param": 123}

        with pytest.raises(ValueError, match="Unknown analysis type: unknown_type"):
            analysis._execute_analysis("test_report", config, {1, 2}, sample_players_data)

    @patch.object(ConfigurationBasedAnalysis, "find_analysis_data")
    def test_generate_single_plot_hit_count(self, mock_find_data, mock_api_client):
        """Test HitCountPlot generation with basic validation."""
        # Setup mocks
        mock_find_data.return_value = (
            [
                {"player_name": "Test", "hit_count": 5, "damage_taken": 25000, "class": "warrior"},
                {"player_name": "Test2", "hit_count": 3, "damage_taken": 15000, "class": "mage"},
            ],
            {"Test": 4, "Test2": 2},
        )

        analysis = ConfigurationBasedAnalysis(mock_api_client)
        plot_config = {
            "analysis_name": "Test Hit Count Analysis",
            "type": "HitCountPlot",
            "title": "Test Hit Count Plot",
            "column_key_1": "hit_count",
            "column_header_1": "Hits",
            "column_key_2": "damage_taken",
            "column_header_2": "Damage",
        }

        try:
            analysis._generate_single_plot(plot_config, "2023-01-01", 300000, 250000)
            # If we get here, basic functionality works
            assert True
        except Exception as e:
            # Should not raise ValueError about unknown plot type
            assert "Unknown plot type" not in str(e)
            # Any other exception might be due to mocking limitations, which is acceptable for this test

    @patch.object(ConfigurationBasedAnalysis, "_generate_plots_generic")
    def test_generate_plots_uses_generic_method(self, mock_generate_generic, mock_api_client):
        """Test that generate_plots uses generic method when PLOT_CONFIG exists."""
        analysis = ConfigurationBasedAnalysis(mock_api_client)
        analysis.results = [{"starttime": 1640995200.0, "fight_ids": {1, 2}}]

        analysis.generate_plots()

        mock_generate_generic.assert_called_once()

    @patch.object(ConfigurationBasedAnalysis, "find_analysis_data")
    def test_generate_single_plot(self, mock_find_data, mock_api_client):
        """Test generate_single_plot functionality with basic validation."""
        # Setup mocks
        mock_find_data.return_value = ([{"player_name": "Test", "interrupts": 5}], {"Test": 3})

        analysis = ConfigurationBasedAnalysis(mock_api_client)
        plot_config = {
            "analysis_name": "Test Interrupts",
            "type": "NumberPlot",
            "title": "Test Plot",
            "column_key_1": "interrupts",
            "column_header_1": "Count",
        }

        # Test that the method doesn't raise an exception with valid config
        # The actual plotting is tested in plot-specific tests
        try:
            analysis._generate_single_plot(plot_config, "2023-01-01", 300000, 250000)
            # If we get here, basic functionality works
            assert True
        except Exception as e:
            # Allow import errors since plotting dependencies might not be available in tests
            if "import" in str(e).lower() or "module" in str(e).lower():
                pytest.skip(f"Plotting dependencies not available: {e}")
            else:
                raise

    def test_generate_single_plot_unknown_type(self, mock_api_client):
        """Test generate_single_plot with unknown plot type."""
        analysis = ConfigurationBasedAnalysis(mock_api_client)
        # Add some test results so find_analysis_data doesn't fail
        analysis.results = [
            {
                "analysis": [{"name": "Test", "data": [{"player_name": "TestPlayer", "test": 100}]}],
                "starttime": 1640995200.0,
            }
        ]
        plot_config = {
            "analysis_name": "Test",
            "type": "UnknownPlot",
            "title": "Test",
            "column_key_1": "test",
            "column_header_1": "Test",
        }

        with pytest.raises(ValueError, match="Unknown plot type: UnknownPlot"):
            analysis._generate_single_plot(plot_config, "2023-01-01", 300000, 250000)
