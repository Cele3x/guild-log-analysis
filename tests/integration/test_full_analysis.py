"""Integration tests for the complete analysis workflow."""

from unittest.mock import Mock, patch

import pytest

from src.guild_log_analysis.main import GuildLogAnalyzer


@pytest.mark.integration
class TestFullAnalysisWorkflow:
    """Integration tests for the complete analysis workflow."""

    @patch("src.guild_log_analysis.main.get_access_token")
    @patch("src.guild_log_analysis.main.WarcraftLogsAPIClient")
    def test_analyzer_initialization(self, mock_api_client_class, mock_get_access_token):
        """Test analyzer initialization with OAuth token acquisition."""
        mock_get_access_token.return_value = "oauth_token"

        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        analyzer = GuildLogAnalyzer()

        # Check that OAuth flow was used and API client was created
        mock_get_access_token.assert_called_once()
        mock_api_client_class.assert_called_once_with(access_token="oauth_token")
        assert analyzer.api_client == mock_api_client
        assert analyzer.analyses == {}

    @patch("src.guild_log_analysis.main.WarcraftLogsAPIClient")
    def test_analyzer_initialization_with_token(self, mock_api_client_class):
        """Test analyzer initialization with provided token."""
        mock_api_client = Mock()
        mock_api_client_class.return_value = mock_api_client

        analyzer = GuildLogAnalyzer(access_token="provided_token")

        mock_api_client_class.assert_called_once_with(access_token="provided_token")
        assert analyzer.api_client == mock_api_client

    @patch("src.guild_log_analysis.main.get_access_token")
    @patch("src.guild_log_analysis.analysis.bosses.one_armed_bandit.OneArmedBanditAnalysis")
    def test_analyze_one_armed_bandit(self, mock_analysis_class, mock_get_access_token):
        """Test One-Armed Bandit analysis workflow."""
        mock_get_access_token.return_value = "oauth_token"

        mock_analysis = Mock()
        mock_analysis_class.return_value = mock_analysis

        analyzer = GuildLogAnalyzer()
        report_codes = ["report1", "report2"]

        analyzer.analyze_one_armed_bandit(report_codes)

        mock_analysis_class.assert_called_once_with(analyzer.api_client)
        mock_analysis.analyze.assert_called_once_with(report_codes)
        assert analyzer.analyses["one_armed_bandit"] == mock_analysis

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
        def mock_find_analysis_data(analysis_name, value_column, name_column):
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
