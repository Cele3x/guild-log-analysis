"""
Multi-line plot for tracking player progress over time.

This module provides a line plot visualization for tracking player metrics
across multiple dates/reports to show progression over time.
"""

import logging
import os
import re
from datetime import datetime
from typing import Optional

import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd

from ..config import DEFAULT_DPI, PlotColors
from .styles import PlotStyleManager

logger = logging.getLogger(__name__)


def _format_number(value: float) -> str:
    """
    Format numbers with human-readable suffixes (k, M, B).

    :param value: The number to format
    :return: Formatted string with appropriate suffix
    """
    if abs(value) >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f}B"
    elif abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.1f}M"
    elif abs(value) >= 1_000:
        return f"{value / 1_000:.1f}k"
    else:
        return f"{value:.0f}"


class MultiLinePlot:
    """
    Multi-line plot for tracking player progress over time.

    Creates a line plot with dates on X-axis and player values on Y-axis.
    Each player gets their own line with class-specific colors.
    """

    def __init__(
        self,
        title: str,
        data: dict[str, pd.DataFrame],
        column_key: str,
        name_column: str = "player_name",
        class_column: Optional[str] = "class",
        y_axis_label: str = "Value",
        ignored_players: Optional[set[str]] = None,
    ) -> None:
        """
        Initialize the multi-line plot.

        :param title: Plot title
        :param data: Dictionary mapping date strings to DataFrames
        :param column_key: Name of the column containing values to plot
        :param name_column: Name of the column containing player/item names
        :param class_column: Name of the column containing class information
        :param y_axis_label: Label for the Y-axis
        :param ignored_players: Set of player names to ignore/exclude from the plot
        """
        self.title = title
        self.data = data
        self.column_key = column_key
        self.name_column = name_column
        self.class_column = class_column
        self.y_axis_label = y_axis_label
        self.ignored_players = ignored_players or set()

        self._setup_plot_style()
        self._prepare_data()

    def _setup_plot_style(self) -> None:
        """Configure matplotlib style settings."""
        PlotStyleManager.setup_plot_style()

    def _prepare_data(self) -> None:
        """Prepare data for plotting by organizing by player across dates."""
        self.player_data = {}
        self.dates = sorted(self.data.keys())

        # Parse dates for proper sorting
        parsed_dates = []
        for date_str in self.dates:
            try:
                # Try to parse DD.MM.YYYY format
                if re.match(r"\d{2}\.\d{2}\.\d{4}", date_str):
                    day, month, year = date_str.split(".")
                    parsed_date = datetime(int(year), int(month), int(day))
                else:
                    # Fallback to current date if parsing fails
                    parsed_date = datetime.now()
                parsed_dates.append((parsed_date, date_str))
            except ValueError:
                parsed_dates.append((datetime.now(), date_str))

        # Sort by parsed date
        parsed_dates.sort(key=lambda x: x[0])
        self.dates = [date_str for _, date_str in parsed_dates]

        # Organize data by player
        all_players = set()
        for df in self.data.values():
            all_players.update(df[self.name_column].tolist())

        # Filter out ignored players
        all_players = all_players - self.ignored_players

        for player in all_players:
            self.player_data[player] = {
                "dates": [],
                "values": [],
                "class": None,
            }

            for date in self.dates:
                df = self.data[date]
                player_row = df[df[self.name_column] == player]

                if not player_row.empty:
                    self.player_data[player]["dates"].append(date)
                    self.player_data[player]["values"].append(player_row[self.column_key].iloc[0])

                    # Store class info (should be consistent across dates)
                    if (
                        self.class_column
                        and self.class_column in player_row.columns
                        and self.player_data[player]["class"] is None
                    ):
                        self.player_data[player]["class"] = player_row[self.class_column].iloc[0]

        # Assign line styles to differentiate players of the same class
        self._assign_line_styles()

    def _assign_line_styles(self) -> None:
        """Assign different line styles to players based on attendance and class."""
        # Available line styles (solid line first for highest attendance)
        line_styles = ["-", "--", "-.", ":", (0, (3, 5, 1, 5))]

        # Calculate attendance for each player (number of dates they appear in)
        for player, data in self.player_data.items():
            data["attendance"] = len(data["dates"])

        # Group players by class
        class_players = {}
        for player, data in self.player_data.items():
            player_class = data["class"] or "Unknown"
            if player_class not in class_players:
                class_players[player_class] = []
            class_players[player_class].append(player)

        # Assign line styles within each class, prioritizing by attendance
        for player_class, players in class_players.items():
            # Sort players by attendance (highest first) for line style assignment
            players_sorted_by_attendance = sorted(
                players, key=lambda p: self.player_data[p]["attendance"], reverse=True
            )

            for i, player in enumerate(players_sorted_by_attendance):
                style_index = i % len(line_styles)
                self.player_data[player]["line_style"] = line_styles[style_index]

    def create_plot(self, figsize: Optional[tuple[int, int]] = None) -> plt.Figure:
        """
        Create the multi-line plot.

        :param figsize: Optional figure size tuple
        :returns: Matplotlib figure object
        """
        if figsize is None:
            figsize = (12, 12)

        fig, ax = plt.subplots(figsize=figsize)
        fig.patch.set_facecolor(PlotColors.BACKGROUND)
        ax.set_facecolor(PlotColors.BACKGROUND)

        # Get all unique dates from the data and create evenly distributed positions
        all_dates = set()
        for player_data in self.player_data.values():
            if len(player_data["dates"]) > 0:
                for date_str in player_data["dates"]:
                    try:
                        if re.match(r"\d{2}\.\d{2}\.\d{4}", date_str):
                            day, month, year = date_str.split(".")
                            all_dates.add(datetime(int(year), int(month), int(day)))
                    except ValueError:
                        continue

        if not all_dates:
            return fig

        # Create evenly distributed positions for all dates
        sorted_dates = sorted(all_dates)
        date_to_position = {date: i for i, date in enumerate(sorted_dates)}

        # Sort players by attendance for consistent plotting and legend order
        players_by_attendance = sorted(self.player_data.items(), key=lambda item: item[1]["attendance"], reverse=True)

        # Plot each player's line
        for player, data in players_by_attendance:
            if len(data["dates"]) > 0:  # Only plot if player has data
                # Get class color
                class_color = PlotColors.TEXT_PRIMARY
                if data["class"] and self.class_column:
                    class_color = PlotStyleManager.get_class_color(data["class"])

                # Get line style
                line_style = data.get("line_style", "-")

                # Convert dates to positions and prepare plot data
                plot_positions = []
                plot_values = []

                for date_str, value in zip(data["dates"], data["values"]):
                    try:
                        if re.match(r"\d{2}\.\d{2}\.\d{4}", date_str):
                            day, month, year = date_str.split(".")
                            date_obj = datetime(int(year), int(month), int(day))
                            if date_obj in date_to_position:
                                plot_positions.append(date_to_position[date_obj])
                                plot_values.append(value)
                    except ValueError:
                        continue

                if plot_positions:
                    # Plot main line with markers
                    ax.plot(
                        plot_positions,
                        plot_values,
                        marker="o",
                        markersize=6,
                        linewidth=2,
                        linestyle=line_style,
                        color=class_color,
                        label=player,
                        alpha=0.8,
                    )

        # Customize plot
        ax.set_title(
            self.title,
            fontsize=20,
            fontweight="bold",
            color=PlotColors.TEXT_PRIMARY,
            pad=20,
        )

        # Set evenly distributed x-axis ticks and labels
        ax.set_xticks(range(len(sorted_dates)))
        ax.set_xticklabels([date.strftime("%d.%m.%Y") for date in sorted_dates])
        ax.set_xlim(-0.5, len(sorted_dates) - 0.5)

        # Rotate x-axis labels for better readability
        ax.tick_params(axis="x", rotation=45, colors=PlotColors.TEXT_PRIMARY)
        ax.tick_params(axis="y", colors=PlotColors.TEXT_PRIMARY)

        # Format Y-axis with human-readable numbers (k, M, B)
        ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: _format_number(x)))

        # Add grid
        ax.grid(True, alpha=0.3, color=PlotColors.TEXT_SECONDARY)

        # Add legend with longer lines for better line style visibility
        legend = ax.legend(
            bbox_to_anchor=(1.05, 1),
            loc="upper left",
            fontsize=10,
            frameon=True,
            facecolor=PlotColors.CHART_BG,
            edgecolor=PlotColors.BORDER,
            labelcolor=PlotColors.TEXT_PRIMARY,
            handlelength=5.0,  # Make legend lines longer
            handletextpad=0.8,  # Space between line and text
        )
        legend.get_frame().set_alpha(0.8)

        # Adjust layout to prevent legend cutoff
        plt.tight_layout()

        return fig

    def _generate_filename(self) -> str:
        """Generate filename from title with date range."""
        # Create date range string
        if len(self.dates) >= 2:
            first_date = self.dates[0]
            last_date = self.dates[-1]

            # Convert to YYYY-MM-DD format for filename
            try:
                if re.match(r"\d{2}\.\d{2}\.\d{4}", first_date):
                    day, month, year = first_date.split(".")
                    first_date_formatted = f"{year}-{month}-{day}"
                else:
                    first_date_formatted = first_date

                if re.match(r"\d{2}\.\d{2}\.\d{4}", last_date):
                    day, month, year = last_date.split(".")
                    last_date_formatted = f"{year}-{month}-{day}"
                else:
                    last_date_formatted = last_date

                date_range = f"{first_date_formatted}_to_{last_date_formatted}"
            except ValueError:
                date_range = f"{first_date}_to_{last_date}"
        else:
            date_range = datetime.now().strftime("%Y-%m-%d")

        # Clean the title for filename
        clean_title = re.sub(r"[^\w\s-]", "", self.title)
        clean_title = re.sub(r"[-\s]+", "_", clean_title)  # Replace spaces/hyphens with underscores
        clean_title = clean_title.strip("_").lower()  # Remove leading/trailing underscores, lowercase

        # Create filename
        filename = f"{date_range}_{clean_title}_progress.png"

        # Get plots directory from settings
        from ..config.settings import Settings

        plots_dir = Settings().plots_directory

        # Create subfolder for multi-line plots using date range
        multi_line_dir = os.path.join(plots_dir, f"multi_line_{date_range}")
        os.makedirs(multi_line_dir, exist_ok=True)

        return os.path.join(multi_line_dir, filename)

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
            logger.info(f"Multi-line plot saved to {filename}")
            return filename
        except Exception as e:
            logger.error(f"Failed to save multi-line plot to {filename}: {e}")
            raise
        finally:
            plt.close(fig)
