"""
Base plotting module for WoW Guild Analysis.

This module provides the abstract base class and common functionality
for creating table-style plots with data visualization.
"""

import logging
import os
import re
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..config import DEFAULT_DPI, HEADER_FONT, NAME_FONT, TITLE_FONT, PlotColors
from ..utils import format_number, format_percentage
from .styles import PlotStyleManager

logger = logging.getLogger(__name__)


class BaseTablePlot(ABC):
    """
    Base class for creating table-style plots.

    This class provides common functionality for creating table-style visualizations
    with bars, change indicators, and class-based coloring.
    """

    def __init__(
        self,
        title: str,
        date: str,
        df: pd.DataFrame,
        previous_data: Optional[dict[str, Any]] = None,
        value_column: str = "value",
        value_column_name: Optional[str] = None,
        name_column: str = "player_name",
        class_column: Optional[str] = "class",
        current_fight_duration: Optional[int] = None,
        previous_fight_duration: Optional[int] = None,
        show_totals: bool = True,
    ) -> None:
        """
        Initialize the plot.

        :param title: Plot title
        :param date: Date string to display
        :param df: DataFrame with current data
        :param previous_data: Dictionary mapping names to previous values
        :param value_column: Name of the column containing current values
        :param value_column_name: Display name for the value column
        :param name_column: Name of the column containing player/item names
        :param class_column: Name of the column containing class information
        :param current_fight_duration: Current total fight duration in milliseconds
        :param previous_fight_duration: Previous total fight duration in milliseconds
        :param show_totals: Whether to show totals row at bottom
        """
        self.title = title
        self.date = date
        self.df = df.copy()
        self.previous_data = previous_data or {}
        self.value_column = value_column
        self.value_column_name = value_column_name or value_column.title()
        self.name_column = name_column
        self.class_column = class_column
        self.current_fight_duration = current_fight_duration
        self.previous_fight_duration = previous_fight_duration
        self.show_totals = show_totals

        self._setup_plot_style()
        self._prepare_data()

    def _setup_plot_style(self) -> None:
        """Configure matplotlib style settings."""
        PlotStyleManager.setup_plot_style()

    def _prepare_data(self) -> None:
        """Prepare and sort data for visualization."""
        # Sort by value column in descending order
        self.df = self.df.sort_values(self.value_column, ascending=False)

        # Add previous values column
        self.df["previous_value"] = self.df[self.name_column].map(self.previous_data)

        # Calculate totals if needed
        if self.show_totals:
            self._calculate_totals()

    def _calculate_totals(self) -> None:
        """Calculate totals for the current and previous data."""
        # For percentage plots, calculate average instead of sum
        if isinstance(self, PercentagePlot):
            # Calculate current average
            self.current_total = self.df[self.value_column].mean()

            # Calculate previous average from previous_data
            previous_values = [self.previous_data.get(name, 0) for name in self.df[self.name_column]]
            # Filter out None/NaN values
            valid_previous = [val for val in previous_values if pd.notna(val)]
            self.previous_total = sum(valid_previous) / len(valid_previous) if valid_previous else None
        else:
            # For number plots, calculate sum
            self.current_total = self.df[self.value_column].sum()

            # Calculate previous total from previous_data
            previous_values = [self.previous_data.get(name, 0) for name in self.df[self.name_column]]
            # Filter out None/NaN values
            valid_previous = [val for val in previous_values if pd.notna(val)]
            self.previous_total = sum(valid_previous) if valid_previous else None

    @abstractmethod
    def _get_value_display(self, value: Any) -> str:
        """
        Format value for display.

        :param value: Raw value to format
        :returns: Formatted string representation
        """
        pass

    @abstractmethod
    def _get_bar_width_ratio(self, value: Any, max_value: Any) -> float:
        """
        Calculate bar width ratio for visualization.

        :param value: Current value
        :param max_value: Maximum value in dataset
        :returns: Width ratio between 0 and 1
        """
        pass

    def _calculate_change(self, current: Any, previous: Any) -> tuple[str, str]:
        """
        Calculate and format change between current and previous values.

        :param current: Current value
        :param previous: Previous value
        :returns: Tuple of (change_text, change_color)
        """
        if pd.isna(previous):
            # return "N/A", PlotColors.TEXT_SECONDARY
            return "", PlotColors.TEXT_SECONDARY

        try:
            # Check for numeric types including numpy types
            if isinstance(current, (int, float, np.integer, np.floating)) and isinstance(
                previous, (int, float, np.integer, np.floating)
            ):
                # For percentage plots, keep the absolute change
                if isinstance(self, PercentagePlot):
                    change = current - previous
                    change = round(change, 2)
                else:
                    # For number plots, calculate total change relative to duration
                    if isinstance(self, NumberPlot) and self.current_fight_duration and self.previous_fight_duration:
                        # Calculate rates per minute (duration is in milliseconds)
                        current_rate = current / (self.current_fight_duration / 60000)
                        previous_rate = previous / (self.previous_fight_duration / 60000)

                        # Scale the rate difference to show meaningful change values
                        # Use the current duration as the baseline for scaling
                        rate_difference = current_rate - previous_rate
                        change = float(rate_difference * (self.current_fight_duration / 60000))
                        # Format duration-based changes (per minute rates)
                        if abs(change) > 100:
                            formatted_change = format_number(change, 0)
                        elif abs(change) > 10:
                            formatted_change = format_number(change, 1)
                        elif abs(change) > 1:
                            formatted_change = format_number(change, 2)
                        else:
                            # For small changes, use 3 decimal places
                            formatted_change = format_number(change, 3)

                        # Add "+" prefix if positive and doesn't already have a sign
                        if change > 0 and not formatted_change.startswith(("+", "-")):
                            formatted_change = f"+ {formatted_change}"
                        elif change < 0 and formatted_change.startswith("-"):
                            formatted_change = formatted_change.replace("-", "- ", 1)
                        return (
                            formatted_change,
                            PlotStyleManager.get_change_color(change),
                        )
                    else:
                        # Simple difference calculation for totals without fight counts
                        change = float(current - previous)
                        # Format the change appropriately
                        if abs(change) >= 1000:
                            formatted_change = format_number(change, 0)
                        elif abs(change) >= 100:
                            formatted_change = format_number(change, 1)
                        else:
                            formatted_change = format_number(change, 2)

                        # Add "+" prefix if positive and doesn't already have a sign
                        if change > 0 and not formatted_change.startswith(("+", "-")):
                            formatted_change = f"+ {formatted_change}"
                        elif change < 0 and formatted_change.startswith("-"):
                            formatted_change = formatted_change.replace("-", "- ", 1)
                        return (
                            formatted_change,
                            PlotStyleManager.get_change_color(change),
                        )

                return (
                    (f"+ {change}" if change > 0 else f"- {abs(change)}" if change < 0 else str(change)),
                    PlotStyleManager.get_change_color(float(change)),
                )
            else:
                return "N/A", PlotColors.TEXT_SECONDARY

        except (TypeError, ValueError):
            return "N/A", PlotColors.TEXT_SECONDARY

    def create_plot(self, figsize: Optional[tuple[int, int]] = None) -> plt.Figure:
        """
        Create and return the complete plot.

        :param figsize: Optional figure size tuple
        :returns: Matplotlib figure object
        """
        if figsize is None:
            # Calculate height based on number of rows plus totals row if needed
            total_rows = len(self.df) + (1 if self.show_totals else 0)
            figsize = (
                20,  # Default figure width
                int(total_rows * 0.7),  # Row height multiplier
            )

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor(PlotColors.BACKGROUND)
        ax.set_facecolor(PlotColors.BACKGROUND)
        ax.axis("off")

        # Configuration
        row_height = 0.6
        header_height = 0.6
        table_width = 12
        max_value = self.df[self.value_column].max()

        # Column configuration
        columns = [
            {"name": "Name", "width": 2.0, "align": "left"},
            {"name": "", "width": 1.5, "align": "right"},
            {"name": self.value_column_name, "width": 6.5, "align": "left"},
            {"name": "Change", "width": 2.0, "align": "left"},
        ]

        # Calculate column positions
        col_positions = []
        current_x = 0.2
        for col in columns:
            col_positions.append(current_x)
            # Type ignore for dynamic dict access
            current_x += col["width"]  # type: ignore[operator]

        # Draw title and date - position closer to header
        title_y = float(len(self.df)) + 1.15
        ax.text(
            table_width / 2,
            title_y,
            self.title,
            fontsize=22,
            fontweight="bold",
            color=PlotColors.TEXT_PRIMARY,
            ha="center",
            fontfamily=TITLE_FONT,
        )
        ax.text(
            table_width / 2,
            title_y - 0.4,
            self.date,
            fontsize=18,
            style="italic",
            color=PlotColors.TEXT_PRIMARY,
            ha="center",
            fontfamily=TITLE_FONT,
        )

        # Draw header (use only data rows for positioning)
        self._draw_header(
            ax,
            columns,
            col_positions,
            len(self.df),
            table_width,
            header_height,
        )

        # Draw data rows
        self._draw_data_rows(ax, columns, col_positions, row_height, table_width, max_value)

        # Draw totals row if enabled
        if self.show_totals:
            self._draw_totals_row(ax, columns, col_positions, row_height)

        # Set axis limits - tighten vertical spacing
        ax.set_xlim(-0.2, table_width + 0.2)

        # Calculate actual totals row position to set proper limits
        if self.show_totals:
            last_data_row_y = len(self.df) - (len(self.df) - 1) * row_height - row_height / 2
            totals_y_pos = last_data_row_y - row_height
            bottom_limit = totals_y_pos - row_height / 2  # Give some margin below totals
        else:
            bottom_limit = len(self.df) - len(self.df) * row_height

        ax.set_ylim(bottom_limit, len(self.df) + 1.5)

        return fig

    @staticmethod
    def _draw_header(
        ax: plt.Axes,
        columns: list[dict],
        col_positions: list[float],
        num_rows: int,
        table_width: float,
        header_height: float,
    ) -> None:
        """Draw table header."""
        header_y = num_rows + 0.3
        header_rect = plt.Rectangle(
            (0, header_y - header_height / 2),
            table_width,
            header_height,
            facecolor=PlotColors.CHART_BG,
            alpha=0.8,
            linewidth=1,
            edgecolor=PlotColors.BORDER,
        )
        ax.add_patch(header_rect)

        for col, x_pos in zip(columns, col_positions):
            ax.text(
                x_pos + (col["width"] / 2 if col["align"] == "center" else 0.1),
                header_y,
                col["name"],
                fontsize=18,
                fontweight="bold",
                color=PlotColors.TEXT_PRIMARY,
                ha=col["align"],
                va="center",
                fontfamily=HEADER_FONT,
            )

    def _draw_data_rows(
        self,
        ax: plt.Axes,
        columns: list[dict],
        col_positions: list[float],
        row_height: float,
        table_width: float,
        max_value: Any,
    ) -> None:
        """Draw data rows with values and bars."""
        for idx, (_, row) in enumerate(self.df.iterrows()):
            y_pos = len(self.df) - idx * row_height - row_height / 2

            # Row background
            row_rect = plt.Rectangle(
                (0, y_pos - row_height / 2),
                table_width,
                row_height,
                facecolor=(PlotColors.ROW_ALT if idx % 2 == 1 else PlotColors.CHART_BG),
                alpha=1 if idx % 2 == 1 else 0.2,
            )
            ax.add_patch(row_rect)

            # Name with class color
            name = row[self.name_column]
            class_color = PlotColors.TEXT_PRIMARY
            if self.class_column and self.class_column in row:
                class_color = PlotStyleManager.get_class_color(row[self.class_column])

            ax.text(
                col_positions[0] + 0.1,
                y_pos,
                name,
                fontsize=18,
                fontweight="normal",
                color=class_color,
                ha="left",
                va="center",
                fontfamily=NAME_FONT,
            )

            # Value number in separate column
            current_value = row[self.value_column]
            value_display = self._get_value_display(current_value)

            ax.text(
                col_positions[1] + columns[1]["width"] - 0.1,
                y_pos,
                value_display,
                fontsize=18,
                fontweight="normal",
                color="white",
                ha="right",
                va="center",
            )

            # Value bar
            self._draw_value_bar(
                ax,
                col_positions[2],
                y_pos,
                current_value,
                max_value,
                class_color,
            )

            # Change indicator
            prev_value = row["previous_value"]
            change_text, change_color = self._calculate_change(current_value, prev_value)

            ax.text(
                col_positions[3] + 0.1,
                y_pos,
                change_text,
                fontsize=18,
                fontweight="normal",
                color=change_color,
                ha="left",
                va="center",
            )

    def _draw_totals_row(
        self,
        ax: plt.Axes,
        columns: list[dict],
        col_positions: list[float],
        row_height: float,
    ) -> None:
        """Draw the totals row at the bottom of the table."""
        last_data_row_y = len(self.df) - (len(self.df) - 1) * row_height - row_height / 2
        totals_y_pos = last_data_row_y - row_height

        # Separator line above totals
        separator_y = totals_y_pos + row_height / 2
        ax.axhline(
            y=separator_y,
            xmin=0.02,
            xmax=0.98,
            color=PlotColors.BORDER,
            linewidth=2,
            alpha=1.0,
        )

        # Totals label
        label_text = "Average" if isinstance(self, PercentagePlot) else "Total"
        ax.text(
            col_positions[0] + 0.1,
            totals_y_pos,
            label_text,
            fontsize=18,
            fontweight="bold",
            color=PlotColors.TEXT_PRIMARY,
            ha="left",
            va="center",
            fontfamily=HEADER_FONT,
        )

        # Totals value
        total_display = self._get_value_display(self.current_total)
        ax.text(
            col_positions[1] + columns[1]["width"] - 0.1,
            totals_y_pos,
            total_display,
            fontsize=18,
            fontweight="bold",
            color=PlotColors.TEXT_PRIMARY,
            ha="right",
            va="center",
        )

        # Change indicator
        if self.previous_total is not None:
            change_text, change_color = self._calculate_change(self.current_total, self.previous_total)
            ax.text(
                col_positions[3] + 0.1,
                totals_y_pos,
                change_text,
                fontsize=18,
                fontweight="bold",
                color=change_color,
                ha="left",
                va="center",
            )

    def _draw_value_bar(
        self,
        ax: plt.Axes,
        col_x: float,
        y_pos: float,
        value: Any,
        max_value: Any,
        color: str,
    ) -> None:
        """Draw value visualization bar."""
        bar_start_x = col_x + 0.1
        bar_width = 6.3
        bar_height = 0.4

        # Background bar
        bg_rect = plt.Rectangle(
            (bar_start_x, y_pos - bar_height / 2),
            bar_width,
            bar_height,
            facecolor=PlotColors.CHART_BG,
            alpha=0.5,
            linewidth=1,
            edgecolor="black",
        )
        ax.add_patch(bg_rect)

        # Value bar
        if value > 0:
            fill_width = self._get_bar_width_ratio(value, max_value) * bar_width
            value_rect = plt.Rectangle(
                (bar_start_x, y_pos - bar_height / 2),
                fill_width,
                bar_height,
                facecolor=color,
                alpha=0.8,
                linewidth=1,
                edgecolor="black",
            )
            ax.add_patch(value_rect)

    def _generate_filename(self) -> str:
        """Generate filename from title with report date prefix."""
        # Use the report date from self.date, fallback to current date if parsing fails
        try:
            # Parse date in DD.MM.YYYY format
            if self.date and re.match(r"\d{2}\.\d{2}\.\d{4}", self.date):
                # Convert DD.MM.YYYY to YYYY-MM-DD
                day, month, year = self.date.split(".")
                date_stamp = f"{year}-{month}-{day}"
            else:
                date_stamp = datetime.now().strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            # Fallback to current date if parsing fails
            date_stamp = datetime.now().strftime("%Y-%m-%d")

        # Clean the title for filename
        clean_title = re.sub(r"[^\w\s-]", "", self.title)  # Remove special chars
        clean_title = re.sub(r"[-\s]+", "_", clean_title)  # Replace spaces/hyphens with underscores
        clean_title = clean_title.strip("_").lower()  # Remove leading/trailing underscores, lowercase

        # Create filename
        filename = f"{date_stamp}_{clean_title}.png"

        # Ensure plots directory exists
        plots_dir = "plots"
        os.makedirs(plots_dir, exist_ok=True)

        return os.path.join(plots_dir, filename)

    def show(self) -> None:
        """Display the plot."""
        self.create_plot()
        plt.show()

    def save(self, filename: Optional[str] = None, dpi: Optional[int] = None) -> str:
        """
        Save the plot to file.

        :param filename: Output filename (optional, auto-generated if not provided)
        :param dpi: Resolution in dots per inch (optional, uses DEFAULT_DPI if not provided)
        :returns: Path to saved file
        """
        if filename is None:
            filename = self._generate_filename()

        if dpi is None:
            dpi = DEFAULT_DPI

        fig = self.create_plot()
        try:
            fig.savefig(
                filename,
                dpi=dpi,
                bbox_inches="tight",
                facecolor=PlotColors.BACKGROUND,
            )
            logger.info(f"Plot saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to save plot to {filename}: {e}")
            raise
        finally:
            plt.close(fig)


class NumberPlot(BaseTablePlot):
    """Plot for displaying number data with formatted values."""

    def _get_value_display(self, value: Any) -> str:
        """Format number count for display."""
        return format_number(value)

    def _get_bar_width_ratio(self, value: Any, max_value: Any) -> float:
        """Calculate bar width ratio for number count."""
        if max_value == 0:
            return 0.0
        return float(value) / float(max_value)


class PercentagePlot(BaseTablePlot):
    """Plot for displaying percentage data with formatted values."""

    def _get_value_display(self, value: Any) -> str:
        """Format percentage for display."""
        return format_percentage(value)

    def _get_bar_width_ratio(self, value: Any, max_value: Any) -> float:
        """Calculate bar width ratio for percentage."""
        if max_value == 0:
            return 0.0
        return float(value) / float(max_value)


class HitCountPlot(BaseTablePlot):
    """Plot for displaying hit count data with damage values shown alongside."""

    def __init__(
        self,
        title: str,
        date: str,
        df: pd.DataFrame,
        previous_data: Optional[dict[str, Any]] = None,
        value_column: str = "hit_count",
        value_column_name: Optional[str] = None,
        damage_column: str = "damage_taken",
        name_column: str = "player_name",
        class_column: Optional[str] = "class",
        current_fight_duration: Optional[int] = None,
        previous_fight_duration: Optional[int] = None,
        show_totals: bool = True,
    ) -> None:
        """
        Initialize the hit count plot.

        :param title: Plot title
        :param date: Date string to display
        :param df: DataFrame with current data
        :param previous_data: Dictionary mapping names to previous values
        :param value_column: Name of the column containing hit count values
        :param value_column_name: Display name for the value column
        :param damage_column: Name of the column containing damage values
        :param name_column: Name of the column containing player/item names
        :param class_column: Name of the column containing class information
        :param current_fight_duration: Current total fight duration in milliseconds
        :param previous_fight_duration: Previous total fight duration in milliseconds
        :param show_totals: Whether to show totals row at bottom
        """
        self.damage_column = damage_column
        super().__init__(
            title=title,
            date=date,
            df=df,
            previous_data=previous_data,
            value_column=value_column,
            value_column_name=value_column_name,
            name_column=name_column,
            class_column=class_column,
            current_fight_duration=current_fight_duration,
            previous_fight_duration=previous_fight_duration,
            show_totals=show_totals,
        )

    def _get_value_display(self, value: Any) -> str:
        """Format hit count for display."""
        return format_number(value, 0)  # Hit counts are always integers

    def _get_bar_width_ratio(self, value: Any, max_value: Any) -> float:
        """Calculate bar width ratio for hit count."""
        if max_value == 0:
            return 0.0
        return float(value) / float(max_value)

    def create_plot(self, figsize: Optional[tuple[int, int]] = None) -> plt.Figure:
        """
        Create and return the complete plot with custom column structure.

        :param figsize: Optional figure size tuple
        :returns: Matplotlib figure object
        """
        if figsize is None:
            # Calculate height based on number of rows plus totals row if needed
            total_rows = len(self.df) + (1 if self.show_totals else 0)
            figsize = (
                22,  # Wider to accommodate damage column
                int(total_rows * 0.7),  # Row height multiplier
            )

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor(PlotColors.BACKGROUND)
        ax.set_facecolor(PlotColors.BACKGROUND)
        ax.axis("off")

        # Configuration
        row_height = 0.6
        header_height = 0.6
        table_width = 13
        max_value = self.df[self.value_column].max()

        columns = [
            {"name": "Name", "width": 2.0, "align": "left"},
            {"name": "", "width": 1.5, "align": "right"},
            {"name": self.value_column_name, "width": 6.5, "align": "left"},
            {"name": "", "width": 1.0, "align": "left"},
            {"name": "Change", "width": 2.0, "align": "left"},
        ]

        col_positions = []
        current_x = 0.2
        for col in columns:
            col_positions.append(current_x)
            current_x += col["width"]

        title_y = float(len(self.df)) + 1.15
        ax.text(
            table_width / 2,
            title_y,
            self.title,
            fontsize=22,
            fontweight="bold",
            color=PlotColors.TEXT_PRIMARY,
            ha="center",
            fontfamily=TITLE_FONT,
        )
        ax.text(
            table_width / 2,
            title_y - 0.4,
            self.date,
            fontsize=18,
            style="italic",
            color=PlotColors.TEXT_PRIMARY,
            ha="center",
            fontfamily=TITLE_FONT,
        )

        self._draw_header(
            ax,
            columns,
            col_positions,
            len(self.df),
            table_width,
            header_height,
        )

        self._draw_data_rows(ax, columns, col_positions, row_height, table_width, max_value)

        if self.show_totals:
            self._draw_totals_row_hitcount(ax, columns, col_positions, row_height)

        ax.set_xlim(-0.2, table_width + 0.2)

        # Calculate actual totals row position to set proper limits
        if self.show_totals:
            last_data_row_y = len(self.df) - (len(self.df) - 1) * row_height - row_height / 2
            totals_y_pos = last_data_row_y - row_height
            bottom_limit = totals_y_pos - row_height / 2  # Give some margin below totals
        else:
            bottom_limit = len(self.df) - len(self.df) * row_height

        ax.set_ylim(bottom_limit, len(self.df) + 1.5)

        return fig

    def _draw_data_rows(
        self,
        ax: plt.Axes,
        columns: list[dict],
        col_positions: list[float],
        row_height: float,
        table_width: float,
        max_value: Any,
    ) -> None:
        """Draw data rows with values, bars, and damage column."""
        for idx, (_, row) in enumerate(self.df.iterrows()):
            y_pos = len(self.df) - idx * row_height - row_height / 2

            # Row background
            row_rect = plt.Rectangle(
                (0, y_pos - row_height / 2),
                table_width,
                row_height,
                facecolor=(PlotColors.ROW_ALT if idx % 2 == 1 else PlotColors.CHART_BG),
                alpha=1 if idx % 2 == 1 else 0.2,
            )
            ax.add_patch(row_rect)

            # Name with class color
            name = row[self.name_column]
            class_color = PlotColors.TEXT_PRIMARY
            if self.class_column and self.class_column in row:
                class_color = PlotStyleManager.get_class_color(row[self.class_column])

            ax.text(
                col_positions[0] + 0.1,
                y_pos,
                name,
                fontsize=18,
                fontweight="normal",
                color=class_color,
                ha="left",
                va="center",
                fontfamily=NAME_FONT,
            )

            # Value number in separate column
            current_value = row[self.value_column]
            value_display = self._get_value_display(current_value)

            ax.text(
                col_positions[1] + columns[1]["width"] - 0.1,
                y_pos,
                value_display,
                fontsize=18,
                fontweight="normal",
                color="white",
                ha="right",
                va="center",
            )

            # Value bar
            self._draw_value_bar(
                ax,
                col_positions[2],
                y_pos,
                current_value,
                max_value,
                class_color,
            )

            damage_value = row.get(self.damage_column, 0)
            damage_display = format_number(damage_value)

            ax.text(
                col_positions[3] + columns[3]["width"] - 0.1,
                y_pos,
                damage_display,
                fontsize=18,
                fontweight="normal",
                color="white",
                ha="right",
                va="center",
            )

            # Change indicator
            prev_value = row["previous_value"]
            change_text, change_color = self._calculate_change(current_value, prev_value)

            ax.text(
                col_positions[4] + 0.1,
                y_pos,
                change_text,
                fontsize=18,
                fontweight="normal",
                color=change_color,
                ha="left",
                va="center",
            )

    def _draw_totals_row_hitcount(
        self,
        ax: plt.Axes,
        columns: list[dict],
        col_positions: list[float],
        row_height: float,
    ) -> None:
        """Draw the totals row at the bottom of the table."""
        last_data_row_y = len(self.df) - (len(self.df) - 1) * row_height - row_height / 2
        totals_y_pos = last_data_row_y - row_height

        # Separator line above totals
        separator_y = totals_y_pos + row_height / 2
        ax.axhline(
            y=separator_y,
            xmin=0.02,
            xmax=0.98,
            color=PlotColors.BORDER,
            linewidth=2,
            alpha=1.0,
        )

        # Totals label
        ax.text(
            col_positions[0] + 0.1,
            totals_y_pos,
            "Total",
            fontsize=18,
            fontweight="bold",
            color=PlotColors.TEXT_PRIMARY,
            ha="left",
            va="center",
            fontfamily=HEADER_FONT,
        )

        # Totals value
        total_display = self._get_value_display(self.current_total)
        ax.text(
            col_positions[1] + columns[1]["width"] - 0.1,
            totals_y_pos,
            total_display,
            fontsize=18,
            fontweight="bold",
            color=PlotColors.TEXT_PRIMARY,
            ha="right",
            va="center",
        )

        # Total damage
        total_damage = self.df[self.damage_column].sum()
        damage_display = format_number(total_damage)
        ax.text(
            col_positions[3] + columns[3]["width"] - 0.1,
            totals_y_pos,
            damage_display,
            fontsize=18,
            fontweight="bold",
            color=PlotColors.TEXT_PRIMARY,
            ha="right",
            va="center",
        )

        # Change indicator
        if self.previous_total is not None:
            change_text, change_color = self._calculate_change(self.current_total, self.previous_total)
            ax.text(
                col_positions[4] + 0.1,
                totals_y_pos,
                change_text,
                fontsize=18,
                fontweight="bold",
                color=change_color,
                ha="left",
                va="center",
            )
