"""Tests for plotting functionality."""

from unittest.mock import Mock, patch

import pandas as pd

from src.guild_log_analysis.config import PlotColors
from src.guild_log_analysis.plotting.base import BaseTablePlot, NumberPlot, PercentagePlot
from src.guild_log_analysis.plotting.styles import PlotStyleManager


class ConcreteTablePlot(BaseTablePlot):
    """Concrete implementation of BaseTablePlot for testing."""

    def _get_value_display(self, value):
        return str(value)

    def _get_bar_width_ratio(self, value, max_value):
        return value / max_value if max_value > 0 else 0


class TestPlotStyleManager:
    """Test cases for PlotStyleManager class."""

    @patch("matplotlib.pyplot.style.use")
    @patch("matplotlib.pyplot.rcParams.update")
    def test_setup_plot_style(self, mock_rcparams_update, mock_style_use):
        """Test plot style setup."""
        PlotStyleManager.setup_plot_style()

        mock_style_use.assert_called_once_with("dark_background")
        mock_rcparams_update.assert_called_once()

        # Check that rcParams were updated with expected values
        call_args = mock_rcparams_update.call_args[0][0]
        assert call_args["figure.facecolor"] == PlotColors.BACKGROUND
        assert call_args["text.color"] == PlotColors.TEXT_PRIMARY

    def test_get_class_color_valid_class(self):
        """Test getting color for valid WoW class."""
        color = PlotStyleManager.get_class_color("warrior")
        assert color != PlotColors.TEXT_PRIMARY  # Should return specific class color

    def test_get_class_color_invalid_class(self):
        """Test getting color for invalid class."""
        color = PlotStyleManager.get_class_color("invalid_class")
        assert color == PlotColors.TEXT_PRIMARY

    def test_get_class_color_empty_string(self):
        """Test getting color for empty class name."""
        color = PlotStyleManager.get_class_color("")
        assert color == PlotColors.TEXT_PRIMARY

    def test_get_class_color_none(self):
        """Test getting color for None class name."""
        color = PlotStyleManager.get_class_color(None)
        assert color == PlotColors.TEXT_PRIMARY

    def test_get_change_color_positive(self):
        """Test getting color for positive change."""
        color = PlotStyleManager.get_change_color(5.0)
        assert color == PlotColors.POSITIVE_CHANGE_COLOR

    def test_get_change_color_negative(self):
        """Test getting color for negative change."""
        color = PlotStyleManager.get_change_color(-3.0)
        assert color == PlotColors.NEGATIVE_CHANGE_COLOR

    def test_get_change_color_zero(self):
        """Test getting color for zero change."""
        color = PlotStyleManager.get_change_color(0.0)
        assert color == PlotColors.NEUTRAL_CHANGE_COLOR


class TestBaseTablePlot:
    """Test cases for BaseTablePlot class."""

    def test_init_with_minimal_parameters(self):
        """Test BaseTablePlot initialization with minimal parameters."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "value": [100, 200]})

        plot = ConcreteTablePlot(title="Test Plot", date="2023-01-01", df=df)

        assert plot.title == "Test Plot"
        assert plot.date == "2023-01-01"
        assert len(plot.df) == 2
        assert plot.value_column == "value"
        assert plot.value_column_name == "Value"

    def test_init_with_all_parameters(self):
        """Test BaseTablePlot initialization with all parameters."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "damage": [1000, 2000]})
        previous_data = {"Player1": 800, "Player2": 1500}

        plot = ConcreteTablePlot(
            title="Damage Plot",
            date="2023-01-01",
            df=df,
            previous_data=previous_data,
            value_column="damage",
            value_column_name="Damage Done",
            current_fight_count=5,
            previous_fight_count=3,
        )

        assert plot.title == "Damage Plot"
        assert plot.value_column == "damage"
        assert plot.value_column_name == "Damage Done"
        assert plot.current_fight_count == 5
        assert plot.previous_fight_count == 3

    def test_prepare_data_sorting(self):
        """Test that data is sorted by value column in descending order."""
        df = pd.DataFrame(
            {
                "player_name": ["Player1", "Player2", "Player3"],
                "value": [100, 300, 200],
            }
        )

        plot = ConcreteTablePlot(title="Test Plot", date="2023-01-01", df=df)

        # Should be sorted: Player2 (300), Player3 (200), Player1 (100)
        assert plot.df.iloc[0]["value"] == 300
        assert plot.df.iloc[1]["value"] == 200
        assert plot.df.iloc[2]["value"] == 100

    def test_prepare_data_previous_values(self):
        """Test that previous values are correctly mapped."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "value": [100, 200]})
        previous_data = {"Player1": 80, "Player2": 150}

        plot = ConcreteTablePlot(
            title="Test Plot",
            date="2023-01-01",
            df=df,
            previous_data=previous_data,
        )

        # Check that previous values were mapped correctly
        assert "previous_value" in plot.df.columns
        # Data is sorted by value, so Player2 (200) should be first
        assert plot.df.iloc[0]["previous_value"] == 150
        assert plot.df.iloc[1]["previous_value"] == 80

    def test_calculate_change_positive(self):
        """Test change calculation for positive change."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})
        plot = ConcreteTablePlot("Test", "2023-01-01", df)

        change_text, change_color = plot._calculate_change(120, 100)

        assert change_text == "+ 20"
        assert change_color == PlotColors.POSITIVE_CHANGE_COLOR

    def test_calculate_change_negative(self):
        """Test change calculation for negative change."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})
        plot = ConcreteTablePlot("Test", "2023-01-01", df)

        change_text, change_color = plot._calculate_change(80, 100)

        assert change_text == "- 20"
        assert change_color == PlotColors.NEGATIVE_CHANGE_COLOR

    def test_calculate_change_zero(self):
        """Test change calculation for zero change."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})
        plot = ConcreteTablePlot("Test", "2023-01-01", df)

        change_text, change_color = plot._calculate_change(100, 100)

        assert change_text == "0"
        assert change_color == PlotColors.NEUTRAL_CHANGE_COLOR

    def test_calculate_change_no_previous(self):
        """Test change calculation with no previous value."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})
        plot = ConcreteTablePlot("Test", "2023-01-01", df)

        change_text, change_color = plot._calculate_change(100, None)

        assert change_text == ""
        assert change_color == PlotColors.TEXT_SECONDARY

    @patch("matplotlib.pyplot.subplots")
    def test_create_plot(self, mock_subplots):
        """Test plot creation."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "value": [100, 200]})

        plot = ConcreteTablePlot(title="Test Plot", date="2023-01-01", df=df)

        result = plot.create_plot()

        assert result == mock_fig
        mock_subplots.assert_called_once()
        mock_ax.axis.assert_called_once_with("off")

    @patch("matplotlib.pyplot.show")
    @patch.object(ConcreteTablePlot, "create_plot")
    def test_show(self, mock_create_plot, mock_show):
        """Test plot display."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})
        plot = ConcreteTablePlot("Test", "2023-01-01", df)

        plot.show()

        mock_create_plot.assert_called_once()
        mock_show.assert_called_once()

    @patch("matplotlib.pyplot.close")
    @patch.object(ConcreteTablePlot, "create_plot")
    def test_save(self, mock_create_plot, mock_close):
        """Test plot saving."""
        mock_fig = Mock()
        mock_create_plot.return_value = mock_fig

        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})
        plot = ConcreteTablePlot("Test", "2023-01-01", df)

        plot.save("test.png", dpi=150)

        mock_create_plot.assert_called_once()
        mock_fig.savefig.assert_called_once_with(
            "test.png",
            dpi=150,
            bbox_inches="tight",
            facecolor=PlotColors.BACKGROUND,
        )
        mock_close.assert_called_once_with(mock_fig)


class TestNumberPlot:
    """Test cases for NumberPlot class."""

    def test_get_value_display_integer(self):
        """Test number display formatting for integers."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [1000]})
        plot = NumberPlot("Test", "2023-01-01", df)

        result = plot._get_value_display(1000)
        assert result == "1.00k"

    def test_get_value_display_million(self):
        """Test number display formatting for millions."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [1500000]})
        plot = NumberPlot("Test", "2023-01-01", df)

        result = plot._get_value_display(1500000)
        assert result == "1.50m"

    def test_get_value_display_small_number(self):
        """Test number display formatting for small numbers."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [5]})
        plot = NumberPlot("Test", "2023-01-01", df)

        result = plot._get_value_display(5)
        assert result == "5"

    def test_get_bar_width_ratio(self):
        """Test bar width ratio calculation."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [50]})
        plot = NumberPlot("Test", "2023-01-01", df)

        ratio = plot._get_bar_width_ratio(50, 100)
        assert ratio == 0.5

    def test_get_bar_width_ratio_zero_max(self):
        """Test bar width ratio calculation with zero max value."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [50]})
        plot = NumberPlot("Test", "2023-01-01", df)

        ratio = plot._get_bar_width_ratio(50, 0)
        assert ratio == 0


class TestPercentagePlot:
    """Test cases for PercentagePlot class."""

    def test_get_value_display(self):
        """Test percentage display formatting."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [75.5]})
        plot = PercentagePlot("Test", "2023-01-01", df)

        result = plot._get_value_display(75.5)
        assert result == "75.5%"

    def test_get_bar_width_ratio(self):
        """Test bar width ratio calculation for percentages."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [25.0]})
        plot = PercentagePlot("Test", "2023-01-01", df)

        ratio = plot._get_bar_width_ratio(25.0, 100.0)
        assert ratio == 0.25

    def test_get_bar_width_ratio_zero_max(self):
        """Test bar width ratio calculation with zero max percentage."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [25.0]})
        plot = PercentagePlot("Test", "2023-01-01", df)

        ratio = plot._get_bar_width_ratio(25.0, 0.0)
        assert ratio == 0


class TestTotalsRowFunctionality:
    """Test cases for totals row functionality."""

    def test_init_with_show_totals_true(self):
        """Test initialization with show_totals=True."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "value": [100, 200]})
        plot = NumberPlot("Test", "2023-01-01", df, show_totals=True)

        assert plot.show_totals is True
        assert hasattr(plot, "current_total")
        assert hasattr(plot, "previous_total")

    def test_init_with_show_totals_false(self):
        """Test initialization with show_totals=False."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "value": [100, 200]})
        plot = NumberPlot("Test", "2023-01-01", df, show_totals=False)

        assert plot.show_totals is False
        # Should not have totals attributes when disabled
        assert not hasattr(plot, "current_total")
        assert not hasattr(plot, "previous_total")

    def test_init_show_totals_default(self):
        """Test that show_totals defaults to True."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "value": [100, 200]})
        plot = NumberPlot("Test", "2023-01-01", df)

        assert plot.show_totals is True

    def test_calculate_totals_number_plot(self):
        """Test totals calculation for NumberPlot (sum)."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2", "Player3"], "value": [100, 200, 300]})
        previous_data = {"Player1": 80, "Player2": 150, "Player3": 250}

        plot = NumberPlot("Test", "2023-01-01", df, previous_data=previous_data, show_totals=True)

        # Current total should be sum
        assert plot.current_total == 600
        # Previous total should be sum of previous values
        assert plot.previous_total == 480

    def test_calculate_totals_percentage_plot(self):
        """Test totals calculation for PercentagePlot (average)."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2", "Player3"], "value": [70.0, 80.0, 90.0]})
        previous_data = {"Player1": 60.0, "Player2": 70.0, "Player3": 80.0}

        plot = PercentagePlot("Test", "2023-01-01", df, previous_data=previous_data, show_totals=True)

        # Current total should be average
        assert plot.current_total == 80.0
        # Previous total should be average of previous values
        assert plot.previous_total == 70.0

    def test_calculate_totals_missing_previous_data(self):
        """Test totals calculation with missing previous data."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "value": [100, 200]})
        previous_data = {"Player1": 80}  # Missing Player2

        plot = NumberPlot("Test", "2023-01-01", df, previous_data=previous_data, show_totals=True)

        assert plot.current_total == 300
        assert plot.previous_total == 80  # Only Player1's previous value

    def test_calculate_totals_no_previous_data(self):
        """Test totals calculation with no previous data."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "value": [100, 200]})

        plot = NumberPlot("Test", "2023-01-01", df, show_totals=True)

        assert plot.current_total == 300
        # When no previous_data is provided, previous_total should be 0 for NumberPlot
        assert plot.previous_total == 0

    def test_calculate_change_for_totals_number_plot(self):
        """Test change calculation for NumberPlot totals."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "value": [150, 250]})
        previous_data = {"Player1": 100, "Player2": 200}

        plot = NumberPlot("Test", "2023-01-01", df, previous_data=previous_data, show_totals=True)

        change_text, change_color = plot._calculate_change(plot.current_total, plot.previous_total)

        assert change_text == "+ 100"
        assert change_color == PlotColors.POSITIVE_CHANGE_COLOR

    def test_calculate_change_for_totals_percentage_plot(self):
        """Test change calculation for PercentagePlot totals."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "value": [75.5, 82.3]})
        previous_data = {"Player1": 70.0, "Player2": 80.0}

        plot = PercentagePlot("Test", "2023-01-01", df, previous_data=previous_data, show_totals=True)

        change_text, change_color = plot._calculate_change(plot.current_total, plot.previous_total)

        # Average went from 75.0 to 78.9, so change should be +3.9
        assert change_text == "+ 3.9"
        assert change_color == PlotColors.POSITIVE_CHANGE_COLOR

    def test_calculate_change_numpy_types(self):
        """Test change calculation with numpy types (regression test)."""
        import numpy as np

        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})
        plot = NumberPlot("Test", "2023-01-01", df, show_totals=True)

        # Test with numpy types that caused the original issue
        current = np.int64(450)
        previous = 410

        change_text, change_color = plot._calculate_change(current, previous)

        assert change_text == "+ 40"
        assert change_color == PlotColors.POSITIVE_CHANGE_COLOR

    @patch("matplotlib.pyplot.subplots")
    def test_create_plot_with_totals(self, mock_subplots):
        """Test plot creation with totals enabled."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "value": [100, 200]})

        plot = NumberPlot("Test", "2023-01-01", df, show_totals=True)

        with patch.object(plot, "_draw_totals_row") as mock_draw_totals:
            plot.create_plot()

            # Should call _draw_totals_row when totals are enabled
            mock_draw_totals.assert_called_once()

    @patch("matplotlib.pyplot.subplots")
    def test_create_plot_without_totals(self, mock_subplots):
        """Test plot creation with totals disabled."""
        mock_fig = Mock()
        mock_ax = Mock()
        mock_subplots.return_value = (mock_fig, mock_ax)

        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "value": [100, 200]})

        plot = NumberPlot("Test", "2023-01-01", df, show_totals=False)

        with patch.object(plot, "_draw_totals_row") as mock_draw_totals:
            plot.create_plot()

            # Should not call _draw_totals_row when totals are disabled
            mock_draw_totals.assert_not_called()

    def test_draw_totals_row_parameters(self):
        """Test _draw_totals_row method signature and parameters."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})
        plot = NumberPlot("Test", "2023-01-01", df, show_totals=True)

        # Mock the required parameters - need all 4 columns like the real plot
        mock_ax = Mock()
        columns = [
            {"name": "Name", "width": 2.0},
            {"name": "", "width": 1.5},
            {"name": "Value", "width": 6.5},
            {"name": "Change", "width": 2.0},
        ]
        col_positions = [0.2, 2.2, 3.7, 10.2]
        row_height = 0.6

        # Should not raise an error with correct parameters
        try:
            plot._draw_totals_row(mock_ax, columns, col_positions, row_height)
        except TypeError as e:
            # If there's a TypeError, it means wrong number of parameters
            assert False, f"Wrong number of parameters: {e}"

    def test_figure_height_with_totals(self):
        """Test that figure height accounts for totals row."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "value": [100, 200]})

        # Create plots with and without totals
        plot_with_totals = NumberPlot("Test", "2023-01-01", df, show_totals=True)
        plot_without_totals = NumberPlot("Test", "2023-01-01", df, show_totals=False)

        with patch("matplotlib.pyplot.subplots") as mock_subplots:
            mock_fig = Mock()
            mock_ax = Mock()
            mock_subplots.return_value = (mock_fig, mock_ax)

            # Create both plots and capture figsize arguments
            plot_with_totals.create_plot()
            figsize_with_totals = mock_subplots.call_args[1]["figsize"]

            mock_subplots.reset_mock()

            plot_without_totals.create_plot()
            figsize_without_totals = mock_subplots.call_args[1]["figsize"]

            # Height should be larger when totals are enabled
            assert figsize_with_totals[1] > figsize_without_totals[1]
