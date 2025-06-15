"""Tests for One-Armed Bandit analysis."""

from unittest.mock import patch

from src.guild_log_analysis.analysis.bosses.one_armed_bandit import OneArmedBanditAnalysis
from src.guild_log_analysis.analysis.registry import get_registered_bosses


class TestOneArmedBanditAnalysis:
    """Test cases for OneArmedBanditAnalysis class."""

    def test_init(self, mock_api_client):
        """Test OneArmedBanditAnalysis initialization."""
        analysis = OneArmedBanditAnalysis(mock_api_client)

        assert analysis.api_client == mock_api_client
        assert analysis.boss_name == "One-Armed Bandit"
        assert analysis.encounter_id == 3014
        assert analysis.difficulty == 5
        assert analysis.results == []

    def test_analysis_configuration(self, mock_api_client):
        """Test that analysis has proper configuration."""
        analysis = OneArmedBanditAnalysis(mock_api_client)

        # Check ANALYSIS_CONFIG
        assert hasattr(analysis, "ANALYSIS_CONFIG")
        assert len(analysis.ANALYSIS_CONFIG) == 6

        # Verify specific analyses are configured
        analysis_names = [config["name"] for config in analysis.ANALYSIS_CONFIG]
        expected_names = [
            "Overload! Interrupts",
            "High Roller Uptime",
            "Premium Dynamite Booties Damage",
            "Reel Assistants Damage",
            "Boss Damage",
            "Absorbed Damage to Reel Assistants",
        ]
        for name in expected_names:
            assert name in analysis_names

    def test_plot_configuration(self, mock_api_client):
        """Test that analysis has proper plot configuration."""
        analysis = OneArmedBanditAnalysis(mock_api_client)

        # Check PLOT_CONFIG
        assert hasattr(analysis, "PLOT_CONFIG")
        assert len(analysis.PLOT_CONFIG) == 6

        # Verify specific plots are configured
        plot_titles = [config["title"] for config in analysis.PLOT_CONFIG]
        expected_titles = [
            "Overload! Interrupts",
            "High Roller Uptime",
            "Schaden auf Geschenke",
            "Schaden auf Reel Assistants",
            "Schaden auf Boss",
            "Absorbierter Schaden auf Reel Assistants",
        ]
        for title in expected_titles:
            assert title in plot_titles

    def test_boss_registration(self):
        """Test that OneArmedBanditAnalysis is properly registered."""
        # Import the module to trigger registration
        import src.guild_log_analysis.analysis.bosses.one_armed_bandit  # noqa: F401

        registered = get_registered_bosses()
        assert "one_armed_bandit" in registered
        assert registered["one_armed_bandit"] == OneArmedBanditAnalysis

    @patch.object(OneArmedBanditAnalysis, "_process_report_generic")
    def test_analyze_uses_configuration_system(self, mock_process_generic, mock_api_client):
        """Test that analyze uses the new configuration-based system."""
        analysis = OneArmedBanditAnalysis(mock_api_client)
        report_codes = ["report1", "report2"]

        analysis.analyze(report_codes)

        # Should use generic processing method since ANALYSIS_CONFIG exists
        assert mock_process_generic.call_count == 2
        mock_process_generic.assert_any_call("report1")
        mock_process_generic.assert_any_call("report2")

    @patch.object(OneArmedBanditAnalysis, "get_fight_ids")
    @patch.object(OneArmedBanditAnalysis, "get_start_time")
    @patch.object(OneArmedBanditAnalysis, "get_participants")
    @patch.object(OneArmedBanditAnalysis, "_execute_analysis")
    def test_configuration_based_analysis(
        self,
        mock_execute_analysis,
        mock_get_participants,
        mock_get_start_time,
        mock_get_fight_ids,
        mock_api_client,
        sample_players_data,
    ):
        """Test configuration-based analysis execution."""
        # Setup mocks
        mock_get_fight_ids.return_value = {1, 2}
        mock_get_start_time.return_value = 1640995200.0
        mock_get_participants.return_value = sample_players_data
        mock_execute_analysis.return_value = [{"player_name": "TestPlayer1", "test_value": 100}]

        analysis = OneArmedBanditAnalysis(mock_api_client)
        analysis._process_report_generic("test_report")

        # Should execute analysis for each configuration item
        assert mock_execute_analysis.call_count == 6  # 6 analyses configured

        # Verify results were added
        assert len(analysis.results) == 1
        result = analysis.results[0]
        assert result["reportCode"] == "test_report"
        assert len(result["analysis"]) == 6

    def test_configuration_values(self, mock_api_client):
        """Test that configuration contains expected values."""
        analysis = OneArmedBanditAnalysis(mock_api_client)

        # Check specific configuration items
        interrupts_config = next(
            (config for config in analysis.ANALYSIS_CONFIG if config["name"] == "Overload! Interrupts"), None
        )
        assert interrupts_config is not None
        assert interrupts_config["type"] == "interrupts"
        assert interrupts_config["ability_id"] == 460582

        uptime_config = next(
            (config for config in analysis.ANALYSIS_CONFIG if config["name"] == "High Roller Uptime"), None
        )
        assert uptime_config is not None
        assert uptime_config["type"] == "debuff_uptime"
        assert uptime_config["ability_id"] == 460444.0

        damage_config = next(
            (config for config in analysis.ANALYSIS_CONFIG if config["name"] == "Premium Dynamite Booties Damage"),
            None,
        )
        assert damage_config is not None
        assert damage_config["type"] == "damage_to_actor"
        assert damage_config["target_game_id"] == 231027
        assert damage_config["result_key"] == "damage_to_dynamite_booties"

    @patch.object(OneArmedBanditAnalysis, "_generate_plots_generic")
    def test_plot_generation_uses_configuration(self, mock_generate_plots, mock_api_client):
        """Test that plot generation uses the configuration system."""
        analysis = OneArmedBanditAnalysis(mock_api_client)
        analysis.results = [{"starttime": 1640995200.0, "fight_ids": {1, 2}}]

        analysis.generate_plots()

        # Should use generic plot generation since PLOT_CONFIG exists
        mock_generate_plots.assert_called_once()
