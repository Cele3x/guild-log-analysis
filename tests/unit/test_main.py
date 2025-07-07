"""Tests for main analyzer functionality."""

from unittest.mock import patch

from src.guild_log_analysis.main import GuildLogAnalyzer


class TestGuildLogAnalyzer:
    """Test cases for GuildLogAnalyzer class."""

    @patch("src.guild_log_analysis.main.get_access_token")
    def test_init_without_token(self, mock_get_access_token):
        """Test GuildLogAnalyzer initialization without provided token."""
        mock_get_access_token.return_value = "mock_token"

        analyzer = GuildLogAnalyzer()

        mock_get_access_token.assert_called_once()
        assert analyzer.api_client is not None

    @patch("src.guild_log_analysis.main.get_access_token")
    def test_init_with_token(self, mock_get_access_token):
        """Test GuildLogAnalyzer initialization with provided token."""
        analyzer = GuildLogAnalyzer(access_token="provided_token")

        # Should not call get_access_token when token is provided
        mock_get_access_token.assert_not_called()
        assert analyzer.api_client is not None

    @patch("src.guild_log_analysis.main.get_access_token")
    def test_analyses_dict_initialized(self, mock_get_access_token):
        """Test that analyses dictionary is initialized."""
        mock_get_access_token.return_value = "mock_token"

        analyzer = GuildLogAnalyzer()

        assert hasattr(analyzer, "analyses")
        assert isinstance(analyzer.analyses, dict)
        assert len(analyzer.analyses) == 0

    @patch("src.guild_log_analysis.main.get_access_token")
    @patch("src.guild_log_analysis.main.get_registered_bosses")
    def test_dynamic_method_creation(self, mock_get_registered_bosses, mock_get_access_token):
        """Test that dynamic methods are created for registered bosses."""
        mock_get_access_token.return_value = "mock_token"
        mock_get_registered_bosses.return_value = {"test_boss": type}

        analyzer = GuildLogAnalyzer()

        # Should have dynamically created methods
        assert hasattr(analyzer, "analyze_test_boss")
        assert hasattr(analyzer, "generate_test_boss_plots")
        assert callable(getattr(analyzer, "analyze_test_boss"))
        assert callable(getattr(analyzer, "generate_test_boss_plots"))

    @patch("src.guild_log_analysis.main.get_access_token")
    def test_plot_method_with_progress_plots_parameter(self, mock_get_access_token):
        """Test that generated plot methods accept include_progress_plots parameter."""
        mock_get_access_token.return_value = "mock_token"

        analyzer = GuildLogAnalyzer()

        # Test with one_armed_bandit (should exist)
        if hasattr(analyzer, "generate_one_armed_bandit_plots"):
            plot_method = getattr(analyzer, "generate_one_armed_bandit_plots")

            # Should be able to call with include_progress_plots parameter
            # Mock the analysis to avoid actual execution
            analyzer.analyses["one_armed_bandit"] = type(
                "MockAnalysis", (), {"generate_plots": lambda include_progress_plots=True: None}
            )()

            # Should not raise an exception
            plot_method(include_progress_plots=True)
            plot_method(include_progress_plots=False)
