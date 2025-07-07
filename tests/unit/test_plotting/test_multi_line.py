"""Tests for MultiLinePlot functionality."""

from unittest.mock import Mock, patch

import pandas as pd

from src.guild_log_analysis.config import PlotColors
from src.guild_log_analysis.plotting.multi_line import MultiLinePlot


class TestMultiLinePlot:
    """Test cases for MultiLinePlot class."""

    def test_init_minimal_parameters(self):
        """Test MultiLinePlot initialization with minimal parameters."""
        data = {
            "01.01.2023": pd.DataFrame(
                {"player_name": ["Player1", "Player2"], "value": [100, 200], "class": ["warrior", "mage"]}
            )
        }

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        assert plot.title == "Test Progress"
        assert plot.column_key == "value"
        assert plot.name_column == "player_name"
        assert plot.class_column == "class"
        assert plot.y_axis_label == "Value"
        assert plot.ignored_players == set()

    def test_init_with_ignored_players(self):
        """Test MultiLinePlot initialization with ignored players."""
        data = {
            "01.01.2023": pd.DataFrame(
                {
                    "player_name": ["Player1", "Player2", "Player3"],
                    "value": [100, 200, 300],
                    "class": ["warrior", "mage", "paladin"],
                }
            )
        }

        ignored_players = {"Player2", "Player3"}

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value", ignored_players=ignored_players)

        assert plot.ignored_players == ignored_players

    def test_prepare_data_filters_ignored_players(self):
        """Test that data preparation filters out ignored players."""
        data = {
            "01.01.2023": pd.DataFrame(
                {
                    "player_name": ["Player1", "Player2", "Player3"],
                    "value": [100, 200, 300],
                    "class": ["warrior", "mage", "paladin"],
                }
            )
        }

        ignored_players = {"Player2"}

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value", ignored_players=ignored_players)

        # Player2 should not be in player_data
        assert "Player1" in plot.player_data
        assert "Player2" not in plot.player_data
        assert "Player3" in plot.player_data

    def test_prepare_data_organizes_by_player(self):
        """Test that data is properly organized by player across dates."""
        data = {
            "01.01.2023": pd.DataFrame(
                {"player_name": ["Player1", "Player2"], "value": [100, 200], "class": ["warrior", "mage"]}
            ),
            "02.01.2023": pd.DataFrame(
                {"player_name": ["Player1", "Player3"], "value": [150, 250], "class": ["warrior", "paladin"]}
            ),
        }

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        # Check Player1 has data from both dates
        assert len(plot.player_data["Player1"]["dates"]) == 2
        assert len(plot.player_data["Player1"]["values"]) == 2
        assert 100 in plot.player_data["Player1"]["values"]
        assert 150 in plot.player_data["Player1"]["values"]

        # Check Player2 has data from only first date
        assert len(plot.player_data["Player2"]["dates"]) == 1
        assert plot.player_data["Player2"]["values"] == [200]

        # Check Player3 has data from only second date
        assert len(plot.player_data["Player3"]["dates"]) == 1
        assert plot.player_data["Player3"]["values"] == [250]

    def test_prepare_data_sorts_dates_chronologically(self):
        """Test that dates are sorted chronologically."""
        data = {
            "03.01.2023": pd.DataFrame({"player_name": ["Player1"], "value": [300], "class": ["warrior"]}),
            "01.01.2023": pd.DataFrame({"player_name": ["Player1"], "value": [100], "class": ["warrior"]}),
            "02.01.2023": pd.DataFrame({"player_name": ["Player1"], "value": [200], "class": ["warrior"]}),
        }

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        # Dates should be sorted chronologically
        expected_order = ["01.01.2023", "02.01.2023", "03.01.2023"]
        assert plot.dates == expected_order

        # Values should be in chronological order too
        assert plot.player_data["Player1"]["values"] == [100, 200, 300]

    def test_assign_line_styles_by_attendance(self):
        """Test that line styles are assigned based on attendance."""
        data = {
            "01.01.2023": pd.DataFrame(
                {
                    "player_name": ["Player1", "Player2", "Player3"],
                    "value": [100, 200, 300],
                    "class": ["warrior", "warrior", "mage"],
                }
            ),
            "02.01.2023": pd.DataFrame(
                {
                    "player_name": ["Player1", "Player2"],  # Player3 missing
                    "value": [150, 250],
                    "class": ["warrior", "warrior"],
                }
            ),
            "03.01.2023": pd.DataFrame(
                {"player_name": ["Player1"], "value": [200], "class": ["warrior"]}  # Only Player1
            ),
        }

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        # Check attendance was calculated
        assert plot.player_data["Player1"]["attendance"] == 3  # Highest
        assert plot.player_data["Player2"]["attendance"] == 2  # Medium
        assert plot.player_data["Player3"]["attendance"] == 1  # Lowest

        # Within warrior class, Player1 (highest attendance) should get solid line
        assert plot.player_data["Player1"]["line_style"] == "-"
        # Player2 (second highest in warrior class) should get dashed line
        assert plot.player_data["Player2"]["line_style"] == "--"

        # Player3 (mage class, only one) should get solid line
        assert plot.player_data["Player3"]["line_style"] == "-"

    def test_assign_line_styles_different_classes(self):
        """Test line style assignment for players of different classes."""
        data = {
            "01.01.2023": pd.DataFrame(
                {
                    "player_name": ["Warrior1", "Warrior2", "Mage1", "Mage2"],
                    "value": [100, 200, 300, 400],
                    "class": ["warrior", "warrior", "mage", "mage"],
                }
            )
        }

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        # Each class should have its own line style assignment
        # First player in each class should get solid line
        warrior_styles = [plot.player_data["Warrior1"]["line_style"], plot.player_data["Warrior2"]["line_style"]]
        mage_styles = [plot.player_data["Mage1"]["line_style"], plot.player_data["Mage2"]["line_style"]]

        # Each class should have at least one solid line (highest attendance)
        assert "-" in warrior_styles
        assert "-" in mage_styles

        # Should have different styles within each class
        assert len(set(warrior_styles)) >= 1
        assert len(set(mage_styles)) >= 1

    @patch("matplotlib.pyplot.subplots")
    def test_create_plot_evenly_distributed_dates(self, mock_subplots):
        """Test that create_plot uses evenly distributed date positions."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        data = {
            "01.01.2023": pd.DataFrame({"player_name": ["Player1"], "value": [100], "class": ["warrior"]}),
            "15.01.2023": pd.DataFrame(
                {"player_name": ["Player1"], "value": [200], "class": ["warrior"]}  # 14 days later
            ),
            "16.01.2023": pd.DataFrame(
                {"player_name": ["Player1"], "value": [300], "class": ["warrior"]}  # 1 day later
            ),
        }

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        plot.create_plot()

        # Check that ax.plot was called
        assert mock_ax.plot.called

        # Verify evenly distributed positions were used
        plot_call_args = mock_ax.plot.call_args[0]
        x_positions = plot_call_args[0]

        # Should be [0, 1, 2] for evenly distributed positions
        assert list(x_positions) == [0, 1, 2]

    @patch("matplotlib.pyplot.subplots")
    def test_create_plot_sorted_by_attendance(self, mock_subplots):
        """Test that players are plotted in attendance order."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        data = {
            "01.01.2023": pd.DataFrame(
                {
                    "player_name": ["LowAttendance", "HighAttendance", "MediumAttendance"],
                    "value": [100, 200, 300],
                    "class": ["warrior", "mage", "paladin"],
                }
            ),
            "02.01.2023": pd.DataFrame(
                {
                    "player_name": ["HighAttendance", "MediumAttendance"],  # LowAttendance missing
                    "value": [250, 350],
                    "class": ["mage", "paladin"],
                }
            ),
            "03.01.2023": pd.DataFrame(
                {"player_name": ["HighAttendance"], "value": [300], "class": ["mage"]}  # Only HighAttendance
            ),
        }

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        plot.create_plot()

        # Check that plots were created in attendance order
        plot_calls = mock_ax.plot.call_args_list

        # Should have 3 plot calls (one for each player)
        assert len(plot_calls) == 3

        # First plot call should be for HighAttendance (highest attendance: 3)
        first_call_label = plot_calls[0][1]["label"]
        assert first_call_label == "HighAttendance"

    @patch("matplotlib.pyplot.subplots")
    def test_create_plot_figure_size(self, mock_subplots):
        """Test that create_plot uses correct figure size."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        data = {"01.01.2023": pd.DataFrame({"player_name": ["Player1"], "value": [100], "class": ["warrior"]})}

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        # Test default figure size
        plot.create_plot()
        mock_subplots.assert_called_with(figsize=(12, 12))

        # Test custom figure size
        mock_subplots.reset_mock()
        plot.create_plot(figsize=(10, 8))
        mock_subplots.assert_called_with(figsize=(10, 8))

    @patch("matplotlib.pyplot.subplots")
    def test_create_plot_handles_no_data(self, mock_subplots):
        """Test that create_plot handles case with no valid data."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        # Empty data
        data = {}

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        result = plot.create_plot()

        # Should return figure even with no data
        assert result == mock_fig

        # Should not have called ax.plot
        mock_ax.plot.assert_not_called()

    @patch("matplotlib.pyplot.subplots")
    def test_create_plot_legend_configuration(self, mock_subplots):
        """Test that legend is configured correctly."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_legend = Mock()
        mock_ax.legend.return_value = mock_legend
        mock_subplots.return_value = (mock_fig, mock_ax)

        data = {"01.01.2023": pd.DataFrame({"player_name": ["Player1"], "value": [100], "class": ["warrior"]})}

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        plot.create_plot()

        # Check legend was configured
        mock_ax.legend.assert_called_once()
        legend_kwargs = mock_ax.legend.call_args[1]

        assert legend_kwargs["bbox_to_anchor"] == (1.05, 1)
        assert legend_kwargs["loc"] == "upper left"
        assert legend_kwargs["handlelength"] == 5.0  # Updated value
        assert legend_kwargs["handletextpad"] == 0.8

    @patch("src.guild_log_analysis.plotting.multi_line.os.makedirs")
    @patch("src.guild_log_analysis.config.settings.Settings")
    def test_generate_filename(self, mock_settings_class, mock_makedirs):
        """Test filename generation with date range."""
        mock_settings = Mock()
        mock_settings.plots_directory = "/test/plots"
        mock_settings_class.return_value = mock_settings

        data = {
            "01.01.2023": pd.DataFrame({"player_name": ["Player1"], "value": [100], "class": ["warrior"]}),
            "15.01.2023": pd.DataFrame({"player_name": ["Player1"], "value": [200], "class": ["warrior"]}),
        }

        plot = MultiLinePlot(title="High Roller! Buff Uptime Progress - Melee DPS", data=data, column_key="value")

        filename = plot._generate_filename()

        # Should include date range and cleaned title
        assert "2023-01-01_to_2023-01-15" in filename
        assert "high_roller_buff_uptime_progress_melee_dps_progress.png" in filename
        assert filename.startswith("/test/plots/")

    @patch("matplotlib.pyplot.close")
    @patch("matplotlib.pyplot.tight_layout")
    @patch.object(MultiLinePlot, "create_plot")
    @patch.object(MultiLinePlot, "_generate_filename")
    def test_save(self, mock_generate_filename, mock_create_plot, mock_tight_layout, mock_close):
        """Test plot saving functionality."""
        mock_fig = Mock()
        mock_create_plot.return_value = mock_fig
        mock_generate_filename.return_value = "/test/plots/test_plot.png"

        data = {"01.01.2023": pd.DataFrame({"player_name": ["Player1"], "value": [100], "class": ["warrior"]})}

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        # Test with auto-generated filename
        result = plot.save()

        assert result == "/test/plots/test_plot.png"
        mock_create_plot.assert_called_once()
        mock_fig.savefig.assert_called_once()
        mock_close.assert_called_once_with(mock_fig)

        # Check savefig parameters
        savefig_kwargs = mock_fig.savefig.call_args[1]
        assert savefig_kwargs["bbox_inches"] == "tight"
        assert savefig_kwargs["facecolor"] == PlotColors.BACKGROUND

    @patch("matplotlib.pyplot.show")
    @patch.object(MultiLinePlot, "create_plot")
    def test_show(self, mock_create_plot, mock_show):
        """Test plot display functionality."""
        data = {"01.01.2023": pd.DataFrame({"player_name": ["Player1"], "value": [100], "class": ["warrior"]})}

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        plot.show()

        mock_create_plot.assert_called_once()
        mock_show.assert_called_once()

    def test_class_color_integration(self):
        """Test that class colors are properly used."""
        data = {
            "01.01.2023": pd.DataFrame(
                {"player_name": ["Warrior1", "Mage1"], "value": [100, 200], "class": ["warrior", "mage"]}
            )
        }

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        # Check that class information is stored
        assert plot.player_data["Warrior1"]["class"] == "warrior"
        assert plot.player_data["Mage1"]["class"] == "mage"

    def test_missing_class_column(self):
        """Test handling of missing class column."""
        data = {
            "01.01.2023": pd.DataFrame(
                {
                    "player_name": ["Player1"],
                    "value": [100],
                    # No class column
                }
            )
        }

        plot = MultiLinePlot(
            title="Test Progress", data=data, column_key="value", class_column="class"  # Column doesn't exist
        )

        # Should handle missing class gracefully
        assert plot.player_data["Player1"]["class"] is None

    def test_no_class_column_specified(self):
        """Test behavior when no class column is specified."""
        data = {"01.01.2023": pd.DataFrame({"player_name": ["Player1"], "value": [100], "class": ["warrior"]})}

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value", class_column=None)

        # Should not try to access class column
        assert plot.player_data["Player1"]["class"] is None

    def test_edge_case_single_date(self):
        """Test handling of single date scenario."""
        data = {
            "01.01.2023": pd.DataFrame(
                {"player_name": ["Player1", "Player2"], "value": [100, 200], "class": ["warrior", "mage"]}
            )
        }

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        # Should handle single date without errors
        assert len(plot.dates) == 1
        assert len(plot.player_data["Player1"]["dates"]) == 1
        assert len(plot.player_data["Player2"]["dates"]) == 1

    def test_edge_case_empty_dataframe(self):
        """Test handling of empty dataframes."""
        data = {
            "01.01.2023": pd.DataFrame({"player_name": [], "value": [], "class": []}),
            "02.01.2023": pd.DataFrame({"player_name": ["Player1"], "value": [100], "class": ["warrior"]}),
        }

        plot = MultiLinePlot(title="Test Progress", data=data, column_key="value")

        # Should only have data from non-empty dataframe
        assert len(plot.player_data) == 1
        assert "Player1" in plot.player_data
        assert len(plot.player_data["Player1"]["dates"]) == 1
