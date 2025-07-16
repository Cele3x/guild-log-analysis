"""
Base plotting module for WoW Guild Analysis.

This module provides the abstract base class and common functionality
for creating table-style plots with data visualization.
"""

import logging
import os
import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from ..config import (
    DEFAULT_DPI,
    HEADER_FONT,
    NAME_FONT,
    TITLE_FONT,
    PlotColors,
)
from ..utils import format_number, format_percentage
from .styles import PlotStyleManager

logger = logging.getLogger(__name__)

# Constants for optimized spacing and layout
ROW_HEIGHT = 0.6
HEADER_HEIGHT = 0.6
BAR_HEIGHT = 0.4
MARGIN_LEFT = 0.2
MARGIN_RIGHT = 0.2
MARGIN_COLUMN = 0.1
FIGURE_PADDING = 2
ROW_HEIGHT_MULTIPLIER = 0.7


@dataclass
class ColumnConfig:
    """Configuration for a table column."""

    name: str
    width: float
    align: str = "left"
    type: str = "value"


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
        column_key_1: str = "value",
        column_header_1: str = "",
        column_key_2: Optional[str] = None,
        column_header_2: str = "",
        column_key_3: Optional[str] = None,
        column_header_3: str = "",
        column_header_4: str = "",
        column_header_5: str = "",
        name_column: str = "player_name",
        class_column: Optional[str] = "class",
        current_fight_duration: Optional[int] = None,
        previous_fight_duration: Optional[int] = None,
        show_totals: bool = True,
        description: Optional[str] = None,
        invert_change_colors: bool = False,
    ) -> None:
        """
        Initialize the plot.

        :param title: Plot title
        :param date: Date string to display
        :param df: DataFrame with current data
        :param previous_data: Dictionary mapping names to previous values
        :param column_key_1: Name of the column containing primary values
        :param column_header_1: Display name for the primary value column (optional)
        :param column_key_2: Name of the column containing secondary values (optional)
        :param column_header_2: Display name for the secondary value column (optional)
        :param column_key_3: Name of the column containing tertiary values (optional)
        :param column_header_3: Display name for the tertiary value column (optional)
        :param column_header_4: Display name for the fourth column (optional)
        :param column_header_5: Display name for the fifth column (optional)
        :param name_column: Name of the column containing player/item names
        :param class_column: Name of the column containing class information
        :param current_fight_duration: Current total fight duration in milliseconds
        :param previous_fight_duration: Previous total fight duration in milliseconds
        :param show_totals: Whether to show totals row at bottom
        :param description: Optional description to display instead of date
        :param invert_change_colors: If True, invert change colors (negative=green, positive=red)
        """
        self.title = title
        self.date = date
        self.df = df.copy()
        self.previous_data = previous_data or {}
        self.column_key_1 = column_key_1
        self.column_header_1 = column_header_1
        self.column_key_2 = column_key_2
        self.column_header_2 = column_header_2
        self.column_key_3 = column_key_3
        self.column_header_3 = column_header_3
        self.column_header_4 = column_header_4
        self.column_header_5 = column_header_5
        self.name_column = name_column
        self.class_column = class_column
        self.current_fight_duration = current_fight_duration
        self.previous_fight_duration = previous_fight_duration
        self.show_totals = show_totals
        self.description = description
        self.invert_change_colors = invert_change_colors

        self._setup_plot_style()
        self._prepare_data()

    def _setup_plot_style(self) -> None:
        """Configure matplotlib style settings."""
        PlotStyleManager.setup_plot_style()

    def _build_dynamic_columns(self) -> list[ColumnConfig]:
        """
        Build optimized column configuration based on content requirements.

        Optimized for minimal empty space while maintaining readability:
        - Names: Compact for WoW character names (max 12 chars)
        - Values: Right-aligned numeric columns
        - Bar: Maximizes visualization space
        - Change: Compact indicator column

        :return: List of column configurations
        """
        columns = []
        has_column4 = self._should_show_column4()

        # Optimized widths - prevent overlap and improve readability
        name_width = 1.5 if has_column4 else 2  # Much wider for 4-column to prevent overlap
        value_width = 1.0  # Slightly wider to prevent overlap
        bar_width = 5.8 if has_column4 else 6.3  # Adjusted spacing for both layouts
        value2_width = 1.3  # Adequate width for secondary values
        change_width = 1.3 if has_column4 else 1.6  # Slightly wider for 5-column

        columns.extend(
            [
                ColumnConfig(self.column_header_1 or "Name", name_width, "left", "name"),
                ColumnConfig(self.column_header_2 or "", value_width, "right", "value1"),
                ColumnConfig(self.column_header_3 or "", bar_width, "left", "bar"),
            ]
        )

        if has_column4:
            columns.append(ColumnConfig(self.column_header_4 or "", value2_width, "left", "value2"))

        columns.append(
            ColumnConfig(
                self.column_header_5 or "Change",
                change_width,
                "left",
                "change",
            )
        )

        return columns

    def _should_show_column4(self) -> bool:
        """
        Determine if column 4 should be shown based on available data and configuration.

        :return: True if column 4 should be displayed
        """
        # Show column 4 if we have secondary data key and either:
        # 1. The column has a non-empty header, OR
        # 2. The dataframe actually contains the secondary data column
        if not self.column_key_2:
            return False

        has_header = bool(self.column_header_4 and self.column_header_4.strip())
        has_data = self.column_key_2 in self.df.columns

        return has_header or has_data

    def _calculate_table_width(self, columns: list[ColumnConfig]) -> float:
        """
        Calculate optimized table width with minimal padding.

        :param columns: List of column configurations
        :return: Total table width
        """
        total_width = 0
        for col in columns:
            col_width = col.width if hasattr(col, "width") else col.get("width", 1.0)
            total_width += col_width
        return MARGIN_LEFT + total_width + MARGIN_RIGHT

    def _get_column_index_by_type(self, columns: list[ColumnConfig], column_type: str) -> Optional[int]:
        """
        Get the index of a column by its type.

        :param columns: List of column configurations
        :param column_type: Type to search for
        :return: Index of the column, or None if not found
        """
        for idx, col in enumerate(columns):
            # Handle both ColumnConfig objects and dict (for test compatibility)
            col_type = col.type if hasattr(col, "type") else col.get("type")
            if col_type == column_type:
                return idx
        return None

    def _filter_data_rows(self) -> pd.DataFrame:
        """
        Filter out rows where data doesn't exist (only show rows with actual data).

        Keeps rows where:
        - Primary column value is non-zero, OR
        - Previous value exists and change would be non-zero

        :return: Filtered DataFrame
        """
        # Create a mask to identify rows with actual data
        has_current_data = (self.df[self.column_key_1].notna()) & (self.df[self.column_key_1] != 0)

        # Check for previous data that would result in non-zero change
        has_previous_data = pd.Series(False, index=self.df.index)
        for idx, row in self.df.iterrows():
            player_name = row[self.name_column]
            previous_value = self.previous_data.get(player_name)
            if previous_value is not None and previous_value != 0:
                has_previous_data.loc[idx] = True

        # Keep rows that have either current data or previous data
        data_mask = has_current_data | has_previous_data

        return self.df[data_mask].copy()

    def _prepare_data(self) -> None:
        """Prepare and sort data for visualization."""
        # Filter out rows where data doesn't exist (only show rows with actual data)
        self.df = self._filter_data_rows()

        # Sort by value column in descending order
        self.df = self.df.sort_values(self.column_key_1, ascending=False)

        # Add previous values column
        self.df["previous_value"] = self.df[self.name_column].map(self.previous_data)

        # Calculate totals if needed
        if self.show_totals:
            self._calculate_totals()

    def _calculate_totals(self) -> None:
        """Optimized totals calculation."""
        if isinstance(self, PercentagePlot):
            self.current_total = self.df[self.column_key_1].mean()
            valid_previous = [
                val for name in self.df[self.name_column] if pd.notna(val := self.previous_data.get(name, None))
            ]
            self.previous_total = sum(valid_previous) / len(valid_previous) if valid_previous else None
        else:
            self.current_total = self.df[self.column_key_1].sum()
            valid_previous = [
                val for name in self.df[self.name_column] if pd.notna(val := self.previous_data.get(name, None))
            ]
            self.previous_total = sum(valid_previous) if valid_previous else 0

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

    def _normalize_value_for_change_calculation(self, value: float) -> float:
        """
        Normalize a value for change calculation using current fight duration.

        :param value: Value to normalize
        :returns: Normalized value (per 30 minutes)
        """
        if (
            self.current_fight_duration is None
            or self.current_fight_duration <= 0
            or self.column_key_1 == "uptime_percentage"
            or self.column_key_1.endswith("_percentage")
        ):
            # Don't normalize percentage values or if duration is invalid
            return value

        # Convert to 30-minute units and normalize
        duration_30min = self.current_fight_duration / (1000 * 60 * 30)
        return value / duration_30min

    def _calculate_change(self, current: Any, previous: Any) -> tuple[str, str]:
        """
        Optimized change calculation with better performance.

        :param current: Current value
        :param previous: Previous value (already normalized)
        :returns: Tuple of (change_text, change_color)
        """
        if pd.isna(previous):
            return "", PlotColors.TEXT_SECONDARY

        try:
            if not isinstance(current, (int, float, np.integer, np.floating)) or not isinstance(
                previous, (int, float, np.integer, np.floating)
            ):
                return "N/A", PlotColors.TEXT_SECONDARY

            # Calculate change based on plot type
            if isinstance(self, PercentagePlot):
                # For percentage plots, calculate difference in percentage points (no rounding in calculation)
                change = current - previous
            else:
                # For all other plot types, normalize current value and calculate percentage change
                normalized_current = self._normalize_value_for_change_calculation(current)
                change = self._calculate_numeric_change(normalized_current, previous)

            # Format and return the change
            return self._format_change(change)

        except (TypeError, ValueError, ZeroDivisionError):
            return "N/A", PlotColors.TEXT_SECONDARY

    def _calculate_numeric_change(self, current: float, previous: float) -> float:
        """Calculate percentage change instead of absolute change."""
        # Handle zero current values - treat as no current data
        if current == 0 or abs(current) < 0.01:
            # If current value is 0, treat as if player had no current data
            # This will be handled by the caller to show no change indicator
            return float("inf")  # Special marker for "no current data"

        # Handle zero previous values - treat as no previous data
        if previous == 0:
            # If previous value is 0, treat as if player had no previous data
            # This will be handled by the caller to show no change indicator
            return float("inf")  # Special marker for "no previous data"

        # For very small previous values (< 0.01), treat as effectively zero to avoid extreme percentages
        if abs(previous) < 0.01:
            return float("inf")  # Special marker for "no previous data"

        # Calculate percentage change: ((current - previous) / previous) * 100
        percentage_change = ((current - previous) / previous) * 100

        # Cap extreme percentage changes to avoid misleading results
        # For example, if previous is 0.001 and current is 25.74, that's a 2,574,000% change
        # which is not meaningful for users
        if abs(percentage_change) > 999:
            return 999.0 if percentage_change > 0 else -999.0

        return float(percentage_change)

    def _format_change(self, change: float) -> tuple[str, str]:
        """Format change value as percentage with appropriate precision and sign."""
        # Handle special case: no previous data (zero or very small previous values)
        if change == float("inf") or change == float("-inf"):
            return "", PlotColors.TEXT_SECONDARY

        # For percentage plots, use the existing behavior (difference in percentage points)
        if isinstance(self, PercentagePlot):
            # Determine precision based on magnitude
            abs_change = abs(change)
            if abs_change >= 100:
                precision = 1
            elif abs_change >= 1:
                precision = 2
            else:
                precision = 3

            formatted_change = format_number(change, precision)

            # Remove trailing zeros for percentage plots to match test expectations
            if "." in formatted_change:
                formatted_change = formatted_change.rstrip("0").rstrip(".")

            # Add proper sign formatting
            if change > 0 and not formatted_change.startswith(("+", "-")):
                formatted_change = f"+ {formatted_change}"
            elif change < 0 and formatted_change.startswith("-"):
                formatted_change = formatted_change.replace("-", "- ", 1)
            elif change == 0:
                # Use ± ligature for zero changes
                formatted_change = f"± {formatted_change}"
        else:
            # For all other plot types, format as percentage (rounded to whole numbers)
            # Round to nearest integer and format as string
            rounded_change = round(change)
            formatted_change = str(rounded_change)

            # Add proper sign formatting and percentage symbol
            if rounded_change > 0:
                formatted_change = f"+ {formatted_change}%"
            elif rounded_change < 0:
                formatted_change = f"- {abs(rounded_change)}%"
            else:
                # Use ± ligature for zero changes
                formatted_change = f"± {formatted_change}%"

        return formatted_change, PlotStyleManager.get_change_color(change, self.invert_change_colors)

    def _create_empty_plot(self, figsize: Optional[tuple[int, int]] = None) -> plt.Figure:
        """
        Create a plot showing "No data to display" message.

        :param figsize: Optional figure size tuple
        :returns: Matplotlib figure object
        """
        if figsize is None:
            figsize = (8, 4)  # Default size for empty plot

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor(PlotColors.BACKGROUND)
        ax.set_facecolor(PlotColors.BACKGROUND)
        ax.axis("off")

        # Draw title
        ax.text(
            0.5,
            0.7,
            self.title,
            fontsize=22,
            fontweight="bold",
            color=PlotColors.TEXT_PRIMARY,
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontfamily=TITLE_FONT,
        )

        # Draw subtitle (description or date)
        subtitle_text = self.description if self.description else self.date

        ax.text(
            0.5,
            0.6,
            subtitle_text,
            fontsize=18,
            style="italic",
            color=PlotColors.TEXT_PRIMARY,
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontfamily=TITLE_FONT,
        )

        # Draw "No data" message
        ax.text(
            0.5,
            0.4,
            "No data to display",
            fontsize=16,
            color=PlotColors.TEXT_SECONDARY,
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontfamily=HEADER_FONT,
        )

        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)

        return fig

    def create_plot(self, figsize: Optional[tuple[int, int]] = None) -> plt.Figure:
        """
        Create optimized plot with minimal empty space.

        :param figsize: Optional figure size tuple
        :returns: Matplotlib figure object
        """
        # Handle empty DataFrame after filtering
        if self.df.empty:
            return self._create_empty_plot(figsize)

        max_value = self.df[self.column_key_1].max()
        # Handle NaN max_value (can happen with all-zero data)
        if pd.isna(max_value):
            max_value = 0

        columns = self._build_dynamic_columns()
        table_width = self._calculate_table_width(columns)

        if figsize is None:
            total_rows = len(self.df) + (1 if self.show_totals else 0)
            # Ensure minimum figure height to avoid matplotlib issues, but only for very small datasets
            calculated_height = int(total_rows * ROW_HEIGHT_MULTIPLIER)
            min_height = 2 if total_rows <= 1 else calculated_height
            figsize = (
                table_width + FIGURE_PADDING,
                max(min_height, calculated_height),
            )

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor(PlotColors.BACKGROUND)
        ax.set_facecolor(PlotColors.BACKGROUND)
        ax.axis("off")

        # Calculate optimized column positions
        col_positions = self._calculate_column_positions(columns)

        # Draw components with optimized spacing
        self._draw_title_and_date(ax, table_width)
        self._draw_header(
            ax,
            columns,
            col_positions,
            len(self.df),
            table_width,
            HEADER_HEIGHT,
        )
        self._draw_data_rows(ax, columns, col_positions, ROW_HEIGHT, table_width, max_value)

        if self.show_totals:
            self._draw_totals_row(ax, columns, col_positions, ROW_HEIGHT)

        # Set optimized axis limits
        self._set_axis_limits(ax, table_width)

        return fig

    def _calculate_column_positions(self, columns: list[ColumnConfig]) -> list[float]:
        """Calculate optimized column positions."""
        positions = []
        current_x = MARGIN_LEFT
        for col in columns:
            positions.append(current_x)
            col_width = col.width if hasattr(col, "width") else col.get("width", 1.0)
            current_x += col_width
        return positions

    def _draw_title_and_date(self, ax: plt.Axes, table_width: float) -> None:
        """Draw title and subtitle (description or date) with optimized positioning."""
        title_y = float(len(self.df)) + 1.15
        center_x = table_width / 2

        ax.text(
            center_x,
            title_y,
            self.title,
            fontsize=22,
            fontweight="bold",
            color=PlotColors.TEXT_PRIMARY,
            ha="center",
            fontfamily=TITLE_FONT,
        )

        # Use description if provided, otherwise use date
        subtitle_text = self.description if self.description else self.date

        ax.text(
            center_x,
            title_y - 0.4,
            subtitle_text,
            fontsize=18,
            style="italic",
            color=PlotColors.TEXT_PRIMARY,
            ha="center",
            fontfamily=TITLE_FONT,
        )

    @staticmethod
    def _draw_header(
        ax: plt.Axes,
        columns: list[ColumnConfig],
        col_positions: list[float],
        num_rows: int,
        table_width: float,
        header_height: float,
    ) -> None:
        """Draw optimized table header."""
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
            # Handle both ColumnConfig objects and dict (for test compatibility)
            col_name = col.name if hasattr(col, "name") else col.get("name", "")
            col_align = col.align if hasattr(col, "align") else col.get("align", "left")
            col_width = col.width if hasattr(col, "width") else col.get("width", 1.0)

            if col_align == "center":
                text_x = x_pos + (col_width / 2)
            elif col_align == "right":
                text_x = x_pos + col_width - MARGIN_COLUMN
            else:  # left alignment
                text_x = x_pos + MARGIN_COLUMN

            ax.text(
                text_x,
                header_y,
                col_name,
                fontsize=18,
                fontweight="bold",
                color=PlotColors.TEXT_PRIMARY,
                ha=col_align,
                va="center",
                fontfamily=HEADER_FONT,
            )

    def _draw_data_rows(
        self,
        ax: plt.Axes,
        columns: list[ColumnConfig],
        col_positions: list[float],
        row_height: float,
        table_width: float,
        max_value: Any,
    ) -> None:
        """Draw optimized data rows."""
        for idx, (_, row) in enumerate(self.df.iterrows()):
            y_pos = len(self.df) - idx * row_height - row_height / 2

            # Row background
            self._draw_row_background(ax, y_pos, row_height, table_width, idx)

            # Get class color once for efficiency
            class_color = self._get_class_color(row)
            current_value = row[self.column_key_1]

            # Draw all column content
            self._draw_name_column(
                ax,
                columns,
                col_positions,
                y_pos,
                row[self.name_column],
                class_color,
            )
            self._draw_value1_column(ax, columns, col_positions, y_pos, current_value)
            self._draw_bar_column(
                ax,
                columns,
                col_positions,
                y_pos,
                current_value,
                max_value,
                class_color,
            )
            self._draw_change_column(
                ax,
                columns,
                col_positions,
                y_pos,
                current_value,
                row["previous_value"],
            )

    def _draw_totals_row(
        self,
        ax: plt.Axes,
        columns: list[ColumnConfig],
        col_positions: list[float],
        row_height: float,
    ) -> None:
        """Draw optimized totals row."""
        totals_y_pos = self._calculate_totals_position(row_height)

        # Separator line
        ax.axhline(
            y=totals_y_pos + row_height / 2,
            xmin=0.02,
            xmax=0.98,
            color=PlotColors.BORDER,
            linewidth=2,
            alpha=1.0,
        )

        # Totals components
        label_text = "Average" if isinstance(self, PercentagePlot) else "Total"
        self._draw_totals_label(ax, columns, col_positions, totals_y_pos, label_text)
        self._draw_totals_value(ax, columns, col_positions, totals_y_pos)
        self._draw_totals_change(ax, columns, col_positions, totals_y_pos)

    def _calculate_totals_position(self, row_height: float) -> float:
        """Calculate totals row position."""
        last_data_row_y = len(self.df) - (len(self.df) - 1) * row_height - row_height / 2
        return last_data_row_y - row_height

    def _draw_totals_label(
        self,
        ax: plt.Axes,
        columns: list[ColumnConfig],
        col_positions: list[float],
        y_pos: float,
        label_text: str,
    ) -> None:
        """Draw totals label."""
        name_idx = self._get_column_index_by_type(columns, "name")
        if name_idx is not None:
            ax.text(
                col_positions[name_idx] + MARGIN_COLUMN,
                y_pos,
                label_text,
                fontsize=18,
                fontweight="bold",
                color=PlotColors.TEXT_PRIMARY,
                ha="left",
                va="center",
                fontfamily=HEADER_FONT,
            )

    def _draw_totals_value(
        self,
        ax: plt.Axes,
        columns: list[ColumnConfig],
        col_positions: list[float],
        y_pos: float,
    ) -> None:
        """Draw totals value."""
        value1_idx = self._get_column_index_by_type(columns, "value1")
        if value1_idx is not None:
            col = columns[value1_idx]
            col_width = col.width if hasattr(col, "width") else col.get("width", 1.0)
            ax.text(
                col_positions[value1_idx] + col_width - MARGIN_COLUMN,
                y_pos,
                self._get_value_display(self.current_total),
                fontsize=18,
                fontweight="bold",
                color=PlotColors.TEXT_PRIMARY,
                ha="right",
                va="center",
            )

    def _draw_totals_change(
        self,
        ax: plt.Axes,
        columns: list[ColumnConfig],
        col_positions: list[float],
        y_pos: float,
    ) -> None:
        """Draw totals change indicator."""
        if self.previous_total is not None:
            change_text, change_color = self._calculate_change(self.current_total, self.previous_total)
            change_idx = self._get_column_index_by_type(columns, "change")
            if change_idx is not None:
                ax.text(
                    col_positions[change_idx] + MARGIN_COLUMN,
                    y_pos,
                    change_text,
                    fontsize=18,
                    fontweight="bold",
                    color=change_color,
                    ha="left",
                    va="center",
                )

    def _set_axis_limits(self, ax: plt.Axes, table_width: float) -> None:
        """Set optimized axis limits."""
        ax.set_xlim(-MARGIN_LEFT, table_width + MARGIN_RIGHT)

        if self.show_totals:
            totals_y_pos = self._calculate_totals_position(ROW_HEIGHT)
            bottom_limit = totals_y_pos - ROW_HEIGHT / 2
        else:
            bottom_limit = len(self.df) - len(self.df) * ROW_HEIGHT

        ax.set_ylim(bottom_limit, len(self.df) + 1.5)

    def _draw_row_background(
        self,
        ax: plt.Axes,
        y_pos: float,
        row_height: float,
        table_width: float,
        idx: int,
    ) -> None:
        """Draw row background with alternating colors."""
        row_rect = plt.Rectangle(
            (0, y_pos - row_height / 2),
            table_width,
            row_height,
            facecolor=(PlotColors.ROW_ALT if idx % 2 == 1 else PlotColors.CHART_BG),
            alpha=1 if idx % 2 == 1 else 0.2,
        )
        ax.add_patch(row_rect)

    def _get_class_color(self, row: pd.Series) -> str:
        """Get class color for player."""
        if self.class_column and self.class_column in row:
            return PlotStyleManager.get_class_color(row[self.class_column])
        return PlotColors.TEXT_PRIMARY

    def _draw_name_column(
        self,
        ax: plt.Axes,
        columns: list[ColumnConfig],
        col_positions: list[float],
        y_pos: float,
        name: str,
        class_color: str,
    ) -> None:
        """Draw name column with class color."""
        name_idx = self._get_column_index_by_type(columns, "name")
        if name_idx is not None:
            ax.text(
                col_positions[name_idx] + MARGIN_COLUMN,
                y_pos,
                name,
                fontsize=18,
                fontweight="normal",
                color=class_color,
                ha="left",
                va="center",
                fontfamily=NAME_FONT,
            )

    def _draw_value1_column(
        self,
        ax: plt.Axes,
        columns: list[ColumnConfig],
        col_positions: list[float],
        y_pos: float,
        value: Any,
    ) -> None:
        """Draw primary value column."""
        value1_idx = self._get_column_index_by_type(columns, "value1")
        if value1_idx is not None:
            col = columns[value1_idx]
            col_width = col.width if hasattr(col, "width") else col.get("width", 1.0)
            ax.text(
                col_positions[value1_idx] + col_width - MARGIN_COLUMN,
                y_pos,
                self._get_value_display(value),
                fontsize=18,
                fontweight="normal",
                color="white",
                ha="right",
                va="center",
            )

    def _draw_bar_column(
        self,
        ax: plt.Axes,
        columns: list[ColumnConfig],
        col_positions: list[float],
        y_pos: float,
        value: Any,
        max_value: Any,
        color: str,
    ) -> None:
        """Draw visualization bar column."""
        bar_idx = self._get_column_index_by_type(columns, "bar")
        if bar_idx is not None:
            col = columns[bar_idx]
            col_width = col.width if hasattr(col, "width") else col.get("width", 1.0)
            self._draw_value_bar(
                ax,
                col_positions[bar_idx],
                y_pos,
                value,
                max_value,
                color,
                col_width,
            )

    def _draw_change_column(
        self,
        ax: plt.Axes,
        columns: list[ColumnConfig],
        col_positions: list[float],
        y_pos: float,
        current_value: Any,
        prev_value: Any,
    ) -> None:
        """Draw change indicator column."""
        change_idx = self._get_column_index_by_type(columns, "change")
        if change_idx is not None:
            change_text, change_color = self._calculate_change(current_value, prev_value)
            ax.text(
                col_positions[change_idx] + MARGIN_COLUMN,
                y_pos,
                change_text,
                fontsize=18,
                fontweight="normal",
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
        bar_column_width: float,
    ) -> None:
        """Draw optimized value visualization bar."""
        bar_start_x = col_x + MARGIN_COLUMN
        bar_width = bar_column_width - (2 * MARGIN_COLUMN)

        # Background bar
        bg_rect = plt.Rectangle(
            (bar_start_x, y_pos - BAR_HEIGHT / 2),
            bar_width,
            BAR_HEIGHT,
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
                (bar_start_x, y_pos - BAR_HEIGHT / 2),
                fill_width,
                BAR_HEIGHT,
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

        # Get plots directory from settings
        from ..config.settings import Settings

        plots_dir = Settings().plots_directory

        # Create subfolder for regular plots using report date
        report_date_dir = os.path.join(plots_dir, date_stamp)
        os.makedirs(report_date_dir, exist_ok=True)

        return os.path.join(report_date_dir, filename)

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


class SurvivabilityPlot(PercentagePlot):
    """Plot for displaying survivability percentage data."""

    def _get_value_display(self, value: Any) -> str:
        """Format survivability percentage for display with 2 decimal places."""
        return format_percentage(value, decimal_places=2)

    def _format_change(self, change: float) -> tuple[str, str]:
        """Format change value for survivability with 2 decimal places."""
        # Handle special case: no previous data (zero or very small previous values)
        if change == float("inf") or change == float("-inf"):
            return "", PlotColors.TEXT_SECONDARY

        # For survivability plots, use percentage point difference with 2 decimal places
        if change > 0:
            change_text = f"+ {change:.2f}%"
            color = PlotColors.POSITIVE_CHANGE_COLOR
        elif change < 0:
            change_text = f"- {abs(change):.2f}%"
            color = PlotColors.NEGATIVE_CHANGE_COLOR
        else:
            change_text = f"± {change:.2f}%"
            color = PlotColors.ZERO_CHANGE_COLOR

        # Apply color inversion if specified
        if self.invert_change_colors:
            if color == PlotColors.POSITIVE_CHANGE_COLOR:
                color = PlotColors.NEGATIVE_CHANGE_COLOR
            elif color == PlotColors.NEGATIVE_CHANGE_COLOR:
                color = PlotColors.POSITIVE_CHANGE_COLOR

        return change_text, color


class HitCountPlot(BaseTablePlot):
    """Optimized plot for displaying hit count data with damage values."""

    def _get_value_display(self, value: Any) -> str:
        """Format hit count for display."""
        return format_number(value, 0)

    def _get_bar_width_ratio(self, value: Any, max_value: Any) -> float:
        """Calculate bar width ratio for hit count."""
        return 0.0 if max_value == 0 else float(value) / float(max_value)

    def _draw_data_rows(
        self,
        ax: plt.Axes,
        columns: list[ColumnConfig],
        col_positions: list[float],
        row_height: float,
        table_width: float,
        max_value: Any,
    ) -> None:
        """Draw data rows with secondary value column for damage."""
        super()._draw_data_rows(ax, columns, col_positions, row_height, table_width, max_value)

        # Add secondary value column if present
        value2_idx = self._get_column_index_by_type(columns, "value2")
        if value2_idx is not None and self.column_key_2:
            for idx, (_, row) in enumerate(self.df.iterrows()):
                y_pos = len(self.df) - idx * row_height - row_height / 2
                damage_value = row.get(self.column_key_2, 0)

                ax.text(
                    col_positions[value2_idx] + MARGIN_COLUMN,
                    y_pos,
                    format_number(damage_value),
                    fontsize=18,
                    fontweight="normal",
                    color="white",
                    ha="left",
                    va="center",
                )

    def _draw_totals_row(
        self,
        ax: plt.Axes,
        columns: list[ColumnConfig],
        col_positions: list[float],
        row_height: float,
    ) -> None:
        """Draw totals row with secondary value total."""
        super()._draw_totals_row(ax, columns, col_positions, row_height)

        # Add total damage if secondary column exists
        value2_idx = self._get_column_index_by_type(columns, "value2")
        if value2_idx is not None and self.column_key_2:
            totals_y_pos = self._calculate_totals_position(row_height)
            total_damage = self.df[self.column_key_2].sum()

            ax.text(
                col_positions[value2_idx] + MARGIN_COLUMN,
                totals_y_pos,
                format_number(total_damage),
                fontsize=18,
                fontweight="bold",
                color=PlotColors.TEXT_PRIMARY,
                ha="left",
                va="center",
            )
