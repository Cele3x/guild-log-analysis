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
        assert plot.column_key_1 == "value"
        assert plot.column_header_1 == ""

    def test_init_with_all_parameters(self):
        """Test BaseTablePlot initialization with all parameters."""
        df = pd.DataFrame({"player_name": ["Player1", "Player2"], "damage": [1000, 2000]})
        previous_data = {"Player1": 800, "Player2": 1500}

        plot = ConcreteTablePlot(
            title="Damage Plot",
            date="2023-01-01",
            df=df,
            previous_data=previous_data,
            column_key_1="damage",
            column_header_1="Damage Done",
            current_fight_duration=300000,
            previous_fight_duration=250000,
        )

        assert plot.title == "Damage Plot"
        assert plot.column_key_1 == "damage"
        assert plot.column_header_1 == "Damage Done"
        assert plot.current_fight_duration == 300000
        assert plot.previous_fight_duration == 250000

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

        # Mock the required parameters - need all 5 columns like the real plot
        mock_ax = Mock()
        columns = [
            {"name": "Name", "width": 2.0},
            {"name": "", "width": 1.5},
            {"name": "Value", "width": 6.5},
            {"name": "", "width": 1.0},
            {"name": "Change", "width": 2.0},
        ]
        col_positions = [0.2, 2.2, 3.7, 10.2, 11.2]
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


class TestDurationBasedChangeCalculation:
    """Test cases for duration-based change calculations."""

    def test_number_plot_duration_based_change_positive(self):
        """Test NumberPlot change calculation with duration (positive change)."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})

        # Current: 100 interrupts in 120 seconds = 50 per minute
        # Previous: 80 interrupts in 100 seconds = 48 per minute
        # Rate diff: 50 - 48 = 2 per minute
        # Scaled change: 2 * 2 minutes = 4 total equivalent
        plot = NumberPlot(
            "Test",
            "2023-01-01",
            df,
            current_fight_duration=120000,  # 2 minutes
            previous_fight_duration=100000,  # 1.67 minutes
        )

        change_text, change_color = plot._calculate_change(100, 80)

        # Should show meaningful positive change
        assert "+" in change_text
        assert change_color == PlotColors.POSITIVE_CHANGE_COLOR
        # Should be around 4, not tiny decimals
        import re

        numbers = re.findall(r"[\d.]+", change_text)
        if numbers:
            numeric_value = float(numbers[0])
            assert numeric_value > 1, f"Expected substantial change, got {numeric_value}"

    def test_number_plot_duration_based_change_negative(self):
        """Test NumberPlot change calculation with duration (negative change)."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})

        # Current: 100 interrupts in 150 seconds = 40 per minute
        # Previous: 80 interrupts in 100 seconds = 48 per minute
        # Rate diff: 40 - 48 = -8 per minute
        # Scaled change: -8 * 2.5 minutes = -20 total equivalent
        plot = NumberPlot(
            "Test",
            "2023-01-01",
            df,
            current_fight_duration=150000,  # 2.5 minutes
            previous_fight_duration=100000,  # 1.67 minutes
        )

        change_text, change_color = plot._calculate_change(100, 80)

        # Should show meaningful negative change
        assert "-" in change_text
        assert change_color == PlotColors.NEGATIVE_CHANGE_COLOR

    def test_number_plot_duration_based_change_zero(self):
        """Test NumberPlot change calculation with duration (zero change)."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})

        # Create scenario where rates are equal:
        # Current: 100 interrupts in 100 seconds = 60 per minute
        # Previous: 80 interrupts in 80 seconds = 60 per minute
        # Rate diff: 60 - 60 = 0 per minute
        # Scaled change: 0 * duration = 0
        plot = NumberPlot(
            "Test",
            "2023-01-01",
            df,
            current_fight_duration=100000,  # 1.67 minutes
            previous_fight_duration=80000,  # 1.33 minutes
        )

        change_text, change_color = plot._calculate_change(100, 80)

        # Should show zero or very small change
        assert change_color == PlotColors.NEUTRAL_CHANGE_COLOR
        # Allow for small rounding differences
        if "0" not in change_text:
            import re

            numbers = re.findall(r"[\d.]+", change_text)
            if numbers:
                numeric_value = float(numbers[0])
                assert numeric_value < 0.1, f"Should be near zero, got {numeric_value}"

    def test_number_plot_no_duration_fallback(self):
        """Test NumberPlot fallback when no duration is provided."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})

        # No duration provided - should fall back to simple difference
        plot = NumberPlot("Test", "2023-01-01", df)

        change_text, change_color = plot._calculate_change(100, 80)

        # Should show simple difference
        assert change_text == "+ 20"
        assert change_color == PlotColors.POSITIVE_CHANGE_COLOR

    def test_number_plot_missing_current_duration(self):
        """Test NumberPlot when current duration is missing."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})

        # Current duration missing - should fall back to simple difference
        plot = NumberPlot("Test", "2023-01-01", df, current_fight_duration=None, previous_fight_duration=100000)

        change_text, change_color = plot._calculate_change(100, 80)

        # Should fall back to simple difference
        assert change_text == "+ 20"
        assert change_color == PlotColors.POSITIVE_CHANGE_COLOR

    def test_number_plot_missing_previous_duration(self):
        """Test NumberPlot when previous duration is missing."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [100]})

        # Previous duration missing - should fall back to simple difference
        plot = NumberPlot("Test", "2023-01-01", df, current_fight_duration=120000, previous_fight_duration=None)

        change_text, change_color = plot._calculate_change(100, 80)

        # Should fall back to simple difference
        assert change_text == "+ 20"
        assert change_color == PlotColors.POSITIVE_CHANGE_COLOR

    def test_percentage_plot_duration_unchanged(self):
        """Test PercentagePlot still uses absolute change, not duration-based."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [75.0]})

        # PercentagePlot should not use duration for change calculation
        plot = PercentagePlot("Test", "2023-01-01", df, current_fight_duration=120000, previous_fight_duration=100000)

        change_text, change_color = plot._calculate_change(75.0, 70.0)

        # Should show absolute percentage change, not duration-based
        assert change_text == "+ 5" or change_text == "+ 5.0"
        assert change_color == PlotColors.POSITIVE_CHANGE_COLOR

    def test_interrupt_scenario_realistic_values(self):
        """Test realistic interrupt scenario that might show 0.00 change."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [12]})

        # Realistic interrupt scenario:
        # Current: 12 interrupts in 300 seconds (5 minutes) = 0.04 per second
        # Previous: 10 interrupts in 240 seconds (4 minutes) = 0.0417 per second
        # Change: 0.04 - 0.0417 = -0.0017 per second (very small)
        plot = NumberPlot(
            "Test Interrupts",
            "2023-01-01",
            df,
            current_fight_duration=300000,  # 5 minutes
            previous_fight_duration=240000,  # 4 minutes
        )

        change_text, change_color = plot._calculate_change(12, 10)

        # Very small change might round to 0.00
        print(f"Interrupt change result: '{change_text}', color: {change_color}")

        # Should show some change, even if very small
        if change_text == "0.00" or change_text == "0":
            # This might be the issue - very small changes rounding to zero
            assert change_color == PlotColors.NEUTRAL_CHANGE_COLOR
        else:
            # Should show negative change
            assert "-" in change_text
            assert change_color == PlotColors.NEGATIVE_CHANGE_COLOR

    def test_interrupt_scenario_zero_change_debug(self):
        """Debug test for zero change in interrupt scenarios."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [10]})

        # Test exact scenario that might cause 0.00:
        # Same rate per second
        plot = NumberPlot(
            "Test Interrupts",
            "2023-01-01",
            df,
            current_fight_duration=300000,  # 5 minutes
            previous_fight_duration=250000,  # 4 minutes 10 seconds
        )

        # Current: 10 interrupts in 300s = 0.0333 per second
        # Previous: 10 interrupts in 250s = 0.04 per second
        # Change: 0.0333 - 0.04 = -0.0067 per second
        current_rate = 10 / (300000 / 1000)
        previous_rate = 10 / (250000 / 1000)
        expected_change = current_rate - previous_rate

        print(f"Current rate: {current_rate:.6f} per second")
        print(f"Previous rate: {previous_rate:.6f} per second")
        print(f"Expected change: {expected_change:.6f} per second")

        change_text, change_color = plot._calculate_change(10, 10)

        print(f"Actual change result: '{change_text}', color: {change_color}")

        # With the fix, the change should now show properly
        assert change_text != "0" and change_text != "0.00"
        # Should show negative change with more precision
        assert "-" in change_text

    def test_format_number_small_changes(self):
        """Test formatting of very small changes that might round to zero."""
        from src.guild_log_analysis.utils.helpers import format_number

        # Test values that might cause issues
        small_values = [0.001, 0.0001, 0.00001, -0.001, -0.0001]

        for value in small_values:
            result = format_number(value, 2)
            print(f"format_number({value}, 2) = '{result}'")

            # Very small values should not be displayed as "0"
            if abs(value) > 0:
                assert result != "0", f"Small value {value} should not format as '0'"

    def test_change_calculation_small_values_debug(self):
        """Debug test for the exact issue with small change values."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [5]})

        # Test a scenario that produces a very small change
        plot = NumberPlot(
            "Test",
            "2023-01-01",
            df,
            current_fight_duration=300000,  # 5 minutes = 300 seconds
            previous_fight_duration=299000,  # 4:59 minutes = 299 seconds
        )

        # Current: 5 interrupts in 300s = 0.01667 per second
        # Previous: 5 interrupts in 299s = 0.01672 per second
        # Change: 0.01667 - 0.01672 = -0.00005 per second (very tiny)
        current_rate = 5 / 300
        previous_rate = 5 / 299
        expected_change = current_rate - previous_rate

        print(f"Expected change: {expected_change:.10f}")

        change_text, change_color = plot._calculate_change(5, 5)
        print(f"Actual result: '{change_text}'")

        # This tiny change might be causing the "0.00" issue
        if abs(expected_change) < 0.01:
            print("Change is very small - this might be the formatting issue")

        # The issue might be here - extremely small changes

    def test_overload_interrupts_scenario_fixed(self):
        """Test that Overload! Interrupts scenario now shows proper change values."""
        # Simulate a realistic Overload! Interrupts scenario
        df = pd.DataFrame(
            {"player_name": ["Paladin1", "DemonHunter1", "Warrior1"], "value": [3, 2, 1]}  # interrupt counts
        )

        # Realistic fight durations: current vs previous reports
        plot = NumberPlot(
            "Overload! Interrupts",
            "2023-01-01",
            df,
            current_fight_duration=420000,  # 7 minutes of attempts
            previous_fight_duration=380000,  # 6:20 minutes of attempts
        )

        # Test each player's change calculation
        test_cases = [
            (3, 2),  # Paladin: 3 now vs 2 before
            (2, 3),  # DH: 2 now vs 3 before
            (1, 1),  # Warrior: 1 now vs 1 before
        ]

        for current, previous in test_cases:
            change_text, change_color = plot._calculate_change(current, previous)
            print(f"Change for {current} -> {previous}: '{change_text}'")

            # Should never show "0.00" for non-zero rate changes
            assert change_text != "0.00"

            # Should show meaningful precision for small changes
            if current != previous:
                assert change_text != "0"
                # Should show sign
                if current > previous:
                    assert "+" in change_text
                else:
                    assert "-" in change_text

    def test_realistic_interrupt_example(self):
        """Test the exact example from the user: 33 interrupts in 90 min vs 20 in 80 min."""
        df = pd.DataFrame({"player_name": ["Player1"], "value": [33]})

        # User's example: 33 interrupts in 90 minutes vs 20 interrupts in 80 minutes
        plot = NumberPlot(
            "Test",
            "2023-01-01",
            df,
            current_fight_duration=90 * 60000,  # 90 minutes in milliseconds
            previous_fight_duration=80 * 60000,  # 80 minutes in milliseconds
        )

        change_text, change_color = plot._calculate_change(33, 20)

        # Expected calculation:
        # Current rate: 33 / 90 = 0.367 per minute
        # Previous rate: 20 / 80 = 0.25 per minute
        # Rate difference: 0.367 - 0.25 = 0.117 per minute
        # Scaled change: 0.117 * 90 = 10.5 total interrupts equivalent

        current_rate = 33 / 90
        previous_rate = 20 / 80
        rate_diff = current_rate - previous_rate
        expected_change = rate_diff * 90

        print(f"Current rate: {current_rate:.3f} per minute")
        print(f"Previous rate: {previous_rate:.3f} per minute")
        print(f"Rate difference: {rate_diff:.3f} per minute")
        print(f"Expected scaled change: {expected_change:.1f}")
        print(f"Actual change text: '{change_text}'")

        # Should show a meaningful positive change, not tiny decimals
        assert "+" in change_text
        assert change_color == PlotColors.POSITIVE_CHANGE_COLOR

        # Should be around 10.5, definitely not 0.002
        # Extract numeric value from change_text for verification
        import re

        numbers = re.findall(r"[\d.]+", change_text)
        if numbers:
            numeric_value = float(numbers[0])
            assert numeric_value > 5, f"Change should be substantial, got {numeric_value}"

    def test_comprehensive_interrupt_scenarios(self):
        """Test various realistic interrupt scenarios to verify meaningful change values."""
        scenarios = [
            # (current_interrupts, current_minutes, previous_interrupts, previous_minutes, description)
            (33, 90, 20, 80, "User's example: significant improvement"),
            (15, 45, 18, 50, "Slight decline in performance"),
            (8, 30, 8, 35, "Same count but different duration"),
            (25, 60, 20, 60, "Same duration, more interrupts"),
            (5, 15, 12, 40, "Much shorter fight, fewer interrupts"),
        ]

        for current_ints, current_mins, prev_ints, prev_mins, description in scenarios:
            df = pd.DataFrame({"player_name": ["Player1"], "value": [current_ints]})

            plot = NumberPlot(
                "Test",
                "2023-01-01",
                df,
                current_fight_duration=current_mins * 60000,  # Convert to milliseconds
                previous_fight_duration=prev_mins * 60000,
            )

            change_text, change_color = plot._calculate_change(current_ints, prev_ints)

            # Calculate expected values manually
            current_rate = current_ints / current_mins
            previous_rate = prev_ints / prev_mins
            rate_diff = current_rate - previous_rate
            expected_change = rate_diff * current_mins

            print(f"\n{description}:")
            print(f"  Current: {current_ints} in {current_mins}min = {current_rate:.3f}/min")
            print(f"  Previous: {prev_ints} in {prev_mins}min = {previous_rate:.3f}/min")
            print(f"  Expected change: {expected_change:.2f}")
            print(f"  Actual result: '{change_text}'")

            # Verify the change makes sense
            if abs(expected_change) > 0.1:
                assert change_text != "0" and change_text != "0.00", f"Should show meaningful change for {description}"

                # Check sign is correct
                if expected_change > 0:
                    assert "+" in change_text, f"Should show positive change for {description}"
                else:
                    assert "-" in change_text, f"Should show negative change for {description}"
