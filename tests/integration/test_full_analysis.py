"""Integration tests for the complete analysis workflow."""

from unittest.mock import Mock, patch

import pytest

from src.guild_log_analysis.analysis.registry import get_registered_bosses
from src.guild_log_analysis.main import GuildLogAnalyzer


@pytest.mark.integration
class TestFullAnalysisWorkflow:
    """Integration tests for the complete analysis workflow."""

    @patch("src.guild_log_analysis.main.get_access_token")
    @patch("src.guild_log_analysis.main.WarcraftLogsAPIClient")
    def test_analyzer_initialization(self, mock_api_client_class, mock_get_access_token):
        """Test analyzer initialization with OAuth token acquisition and auto-registration."""
        mock_get_access_token.return_value = "oauth_token"

        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        analyzer = GuildLogAnalyzer()

        # Check that OAuth flow was used and API client was created
        mock_get_access_token.assert_called_once()
        mock_api_client_class.assert_called_once_with(access_token="oauth_token")
        assert analyzer.api_client == mock_api_client
        assert analyzer.analyses == {}

        # Check that auto-registration created methods
        assert hasattr(analyzer, "analyze_one_armed_bandit")
        assert hasattr(analyzer, "generate_one_armed_bandit_plots")
        assert callable(getattr(analyzer, "analyze_one_armed_bandit"))
        assert callable(getattr(analyzer, "generate_one_armed_bandit_plots"))

    @patch("src.guild_log_analysis.main.WarcraftLogsAPIClient")
    def test_analyzer_initialization_with_token(self, mock_api_client_class):
        """Test analyzer initialization with provided token."""
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        analyzer = GuildLogAnalyzer(access_token="provided_token")

        mock_api_client_class.assert_called_once_with(access_token="provided_token")
        assert analyzer.api_client == mock_api_client

    def test_auto_registration_system(self):
        """Test that the auto-registration system works correctly."""
        # Import to trigger registration
        import src.guild_log_analysis.analysis.bosses.one_armed_bandit  # noqa: F401

        # Check that boss was registered
        registered = get_registered_bosses()
        assert "one_armed_bandit" in registered

        # Create analyzer and verify methods were created
        with patch("src.guild_log_analysis.main.get_access_token") as mock_token:
            mock_token.return_value = "test_token"
            analyzer = GuildLogAnalyzer()

            # Check auto-generated methods exist
            assert hasattr(analyzer, "analyze_one_armed_bandit")
            assert hasattr(analyzer, "generate_one_armed_bandit_plots")

            # Check they are callable
            assert callable(analyzer.analyze_one_armed_bandit)
            assert callable(analyzer.generate_one_armed_bandit_plots)

    @patch("src.guild_log_analysis.main.get_access_token")
    def test_dynamic_boss_methods_exist(self, mock_get_access_token):
        """Test that dynamically created boss methods exist and are callable."""
        mock_get_access_token.return_value = "oauth_token"

        analyzer = GuildLogAnalyzer()

        # Should have dynamically created methods for registered bosses
        assert hasattr(analyzer, "analyze_one_armed_bandit")
        assert hasattr(analyzer, "generate_one_armed_bandit_plots")
        assert callable(getattr(analyzer, "analyze_one_armed_bandit"))
        assert callable(getattr(analyzer, "generate_one_armed_bandit_plots"))

    @patch("src.guild_log_analysis.main.get_access_token")
    def test_plot_methods_accept_progress_plots_parameter(self, mock_get_access_token):
        """Test that plot methods accept include_progress_plots parameter."""
        mock_get_access_token.return_value = "oauth_token"

        analyzer = GuildLogAnalyzer()

        # Mock an analysis to avoid actual execution
        mock_analysis = Mock()
        mock_analysis.generate_plots = Mock()
        analyzer.analyses["one_armed_bandit"] = mock_analysis

        # Should be able to call with include_progress_plots parameter
        plot_method = getattr(analyzer, "generate_one_armed_bandit_plots")
        plot_method(include_progress_plots=True)
        plot_method(include_progress_plots=False)

        # Verify generate_plots was called with the correct parameters
        assert mock_analysis.generate_plots.call_count == 2
        mock_analysis.generate_plots.assert_any_call(include_progress_plots=True)
        mock_analysis.generate_plots.assert_any_call(include_progress_plots=False)

    @patch("src.guild_log_analysis.main.get_access_token")
    @patch("src.guild_log_analysis.plotting.NumberPlot")
    @patch("src.guild_log_analysis.plotting.PercentagePlot")
    def test_generate_plots_success(self, mock_percentage_plot, mock_number_plot, mock_get_access_token):
        """Test successful plot generation."""
        mock_get_access_token.return_value = "oauth_token"

        # Create mock analysis with sample results
        mock_analysis = Mock()
        mock_analysis.results = [
            {
                "starttime": 1640995200.0,
                "fight_ids": {1, 2},
                "analysis": [{"data": [{}]}],
            }
        ]

        # Mock find_analysis_data method to return data
        def mock_find_analysis_data(analysis_name, column_key_1, name_column):
            for analysis_data in mock_analysis.results[0]["analysis"]:
                if analysis_data["name"] == analysis_name:
                    return analysis_data["data"], {}
            return [], {}

        mock_analysis.find_analysis_data.side_effect = mock_find_analysis_data

        # Mock plot instances
        mock_plot_instance = Mock()
        mock_number_plot.return_value = mock_plot_instance
        mock_percentage_plot.return_value = mock_plot_instance

        analyzer = GuildLogAnalyzer()
        analyzer.analyses["one_armed_bandit"] = mock_analysis

        # Just test that the method can be called without errors
        # The actual plotting logic is tested in unit tests
        try:
            analyzer.generate_one_armed_bandit_plots()
            # If we get here without exception, the test passes
            assert True
        except Exception as e:
            pytest.fail(f"generate_one_armed_bandit_plots raised an exception: {e}")

    @patch("src.guild_log_analysis.main.get_access_token")
    def test_generate_plots_no_analysis(self, mock_get_access_token):
        """Test plot generation with no analysis data."""
        mock_get_access_token.return_value = "oauth_token"

        analyzer = GuildLogAnalyzer()

        # Should not raise exception, just log error
        analyzer.generate_one_armed_bandit_plots()

    @patch("src.guild_log_analysis.main.get_access_token")
    def test_generate_plots_no_results(self, mock_get_access_token):
        """Test plot generation with analysis but no results."""
        mock_get_access_token.return_value = "oauth_token"

        mock_analysis = Mock()
        mock_analysis.results = []

        analyzer = GuildLogAnalyzer()
        analyzer.analyses["one_armed_bandit"] = mock_analysis

        # Should not raise exception, just log warning
        analyzer.generate_one_armed_bandit_plots()

    @patch("src.guild_log_analysis.main.GuildLogAnalyzer")
    def test_main_function_success(self, mock_analyzer_class):
        """Test main function successful execution."""
        mock_analyzer = Mock()
        mock_analyzer_class.return_value = mock_analyzer

        from src.guild_log_analysis.main import main

        main()

        mock_analyzer_class.assert_called_once()
        mock_analyzer.analyze_one_armed_bandit.assert_called_once()
        mock_analyzer.generate_one_armed_bandit_plots.assert_called_once()

    @patch("src.guild_log_analysis.main.GuildLogAnalyzer")
    def test_main_function_with_exception(self, mock_analyzer_class):
        """Test main function with exception."""
        mock_analyzer_class.side_effect = Exception("Test error")

        from src.guild_log_analysis.main import main

        with pytest.raises(Exception):
            main()


@pytest.mark.integration
@pytest.mark.slow
class TestAPIIntegration:
    """Integration tests for API interactions (requires mocking)."""

    @patch("src.guild_log_analysis.api.WarcraftLogsAPIClient.make_request")
    def test_full_analysis_with_mocked_api(
        self,
        mock_make_request,
        sample_api_response,
        sample_player_details_response,
        sample_actors_response,
        sample_damage_response,
        sample_interrupt_events,
    ):
        """Test full analysis workflow with mocked API responses."""
        # Setup API response sequence
        mock_make_request.side_effect = [
            sample_api_response,  # get_fight_ids
            sample_api_response,  # get_start_time
            sample_api_response,  # get_total_fight_duration (for uptime)
            sample_player_details_response,  # get_participants
            sample_interrupt_events,  # analyze_interrupts
            {  # analyze_debuff_uptime events
                "data": {"reportData": {"report": {"events": {"data": [], "nextPageTimestamp": None}}}}
            },
            sample_actors_response,  # get_damage_to_actor - actors
            sample_damage_response,  # get_damage_to_actor - damage
        ]

        from src.guild_log_analysis.analysis import OneArmedBanditAnalysis
        from src.guild_log_analysis.api import WarcraftLogsAPIClient

        # Create API client and analysis
        api_client = WarcraftLogsAPIClient(access_token="test_token")
        analysis = OneArmedBanditAnalysis(api_client)

        # Run analysis
        analysis.analyze(["test_report"])

        # Verify that analysis was attempted (even if no results due to no players)
        # The test should pass if the analysis runs without errors
        assert isinstance(analysis.results, list)  # Results should be a list
        # Note: Results may be empty if no players found, which is expected with mock data

    @patch("src.guild_log_analysis.api.WarcraftLogsAPIClient.make_request")
    def test_damage_taken_from_ability_integration(self, mock_execute_query, sample_players_data):
        """Test damage taken from ability analysis integration."""
        # Mock responses for the various API calls needed
        mock_execute_query.side_effect = [
            # Damage taken response
            {
                "data": {
                    "reportData": {
                        "report": {
                            "table": {
                                "data": {
                                    "entries": [
                                        {"name": "TestPlayer1", "total": 15000},
                                        {"name": "TestPlayer2", "total": 8000},
                                        {"name": "TestPlayer3", "total": 12000},
                                    ]
                                }
                            }
                        }
                    }
                }
            }
        ]

        from src.guild_log_analysis.analysis.base import BossAnalysisBase
        from src.guild_log_analysis.api import WarcraftLogsAPIClient

        # Create a test boss analysis with damage taken configuration
        class TestDamageTakenAnalysis(BossAnalysisBase):
            def __init__(self, api_client):
                super().__init__(api_client)
                self.boss_name = "Test Damage Taken Boss"
                self.encounter_id = 3014
                self.difficulty = 5

            CONFIG = [
                {
                    "name": "Travelling Flames Damage",
                    "analysis": {
                        "type": "damage_taken_from_ability",
                        "ability_id": 1223999,
                    },
                    "plot": {
                        "type": "NumberPlot",
                        "title": "Damage Taken from Travelling Flames",
                        "column_key_1": "travelling_flames_damage",
                        "column_header_2": "Damage Taken",
                    },
                }
            ]

            def get_fight_ids(self, report_code):
                return {1, 2}

            def get_start_time(self, report_code, fight_ids):
                return 1640995200.0

            def get_total_fight_duration(self, report_code, fight_ids):
                return 300000

            def get_participants(self, report_code, fight_ids):
                return sample_players_data

        # Create API client and analysis
        api_client = WarcraftLogsAPIClient(access_token="test_token")
        analysis = TestDamageTakenAnalysis(api_client)

        # Run analysis using configuration
        analysis._analyze_generic(["test_report"])

        # Verify results
        assert len(analysis.results) == 1
        report_result = analysis.results[0]
        assert report_result["reportCode"] == "test_report"
        assert len(report_result["analysis"]) == 1

        damage_analysis = report_result["analysis"][0]
        assert damage_analysis["name"] == "Travelling Flames Damage"
        assert len(damage_analysis["data"]) == 3

        # Check that damage was properly assigned with correct result_key
        player_data = damage_analysis["data"]
        player1 = next(p for p in player_data if p["player_name"] == "TestPlayer1")
        assert player1["travelling_flames_damage"] == 15000
        assert "damage_taken" not in player1  # Original field should be renamed

        # Verify API was called with correct parameters
        mock_execute_query.assert_called_once()
        call_args = mock_execute_query.call_args[0]
        query = call_args[0]
        variables = call_args[1]

        assert "dataType: DamageTaken" in query
        assert "abilityID: $abilityID" in query
        assert variables["abilityID"] == 1223999
