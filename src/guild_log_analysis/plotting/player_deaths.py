"""
Player Deaths Visualization module for Guild Log Analysis.

This module provides visualization classes for player deaths analysis,
showing player deaths across all fights in a table format.
"""

import logging
from datetime import datetime
from typing import Any, Optional

import matplotlib.pyplot as plt

from ..config.constants import ClassColors
from .styles import PlotColors, PlotStyleManager

logger = logging.getLogger(__name__)


class PlayerDeathsPlot:
    """
    Player-centric deaths visualization.

    Creates a table showing all deaths for a specific player across all fights,
    including fight number, time of death, and top damage sources.
    """

    def __init__(
        self,
        title: str,
        date: str,
        player_data: list[dict[str, Any]],
        figsize: tuple[int, int] = (18, 12),
    ) -> None:
        """
        Initialize player deaths plot.

        :param title: Plot title
        :param date: Date string for the plot
        :param player_data: List of player death data
        :param figsize: Figure size tuple
        """
        self.title = title
        self.date = date
        self.player_data = player_data
        self.figsize = figsize

        # Styling constants - using standard plot colors
        self.colors = {
            "header_bg": PlotColors.CHART_BG,  # Dark gray for header
            "header_text": PlotColors.TEXT_PRIMARY,  # White for header text
            "row_even": PlotColors.ROW_ALT,  # Alternating row color
            "row_odd": PlotColors.BACKGROUND,  # Background color for rows
            "grid_lines": PlotColors.GRID,  # Grid lines
            "text_primary": PlotColors.TEXT_PRIMARY,
            "text_secondary": PlotColors.TEXT_SECONDARY,
        }

    def create_plot(self) -> plt.Figure:
        """
        Create the player deaths table visualization.

        :return: Matplotlib figure object
        """
        if not self.player_data:
            return self._create_empty_plot()

        # Setup figure and styling
        PlotStyleManager.setup_plot_style()

        # Create one plot per player
        num_players = len(self.player_data)
        fig, axes = plt.subplots(num_players, 1, figsize=self.figsize, squeeze=False)

        # Set dark background to match other plots
        fig.patch.set_facecolor(PlotColors.BACKGROUND)

        # Handle single player case
        if num_players == 1:
            axes = [axes[0, 0]]
        else:
            axes = axes[:, 0]

        # Draw table for each player
        for i, player_info in enumerate(self.player_data):
            self._draw_player_death_table(axes[i], player_info)

        # Adjust layout
        plt.tight_layout()

        return fig

    def _create_empty_plot(self) -> plt.Figure:
        """Create empty plot when no data is available."""
        PlotStyleManager.setup_plot_style()
        fig, ax = plt.subplots(figsize=(8, 4))

        ax.text(
            0.5,
            0.5,
            "No player deaths data available",
            ha="center",
            va="center",
            transform=ax.transAxes,
            fontsize=16,
            color=self.colors["text_secondary"],
        )
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis("off")
        return fig

    def _create_damage_source_colors(self, deaths: list[dict[str, Any]]) -> dict[str, str]:
        """
        Create color mapping for unique damage sources.

        :param deaths: List of death data
        :return: Dictionary mapping damage source names to colors
        """
        import matplotlib.colors as mcolors

        # Extract all unique damage source names (only meaningful damage > 0%)
        unique_sources = set()
        for death in deaths:
            for source in death.get("damage_sources", []):
                # Only include sources with meaningful damage
                if source.get("hp_percentage", 0) > 0.0:
                    unique_sources.add(source["name"])

        # Create color palette - using bright colors for visibility on dark background
        # tab20 provides 20 distinct colors
        colors = plt.cm.tab20(range(20))

        # Convert to hex and make brighter for dark background
        color_palette = [mcolors.rgb2hex(color[:3]) for color in colors]

        # Map each unique source to a color
        source_colors = {}
        for i, source_name in enumerate(sorted(unique_sources)):
            source_colors[source_name] = color_palette[i % len(color_palette)]

        return source_colors

    def _draw_player_death_table(self, ax: plt.Axes, player_info: dict[str, Any]) -> None:
        """
        Draw death table for a single player showing all deaths across all fights.

        :param ax: Matplotlib axes object
        :param player_info: Player death data including name, class, and deaths list
        """
        player_name = player_info["player_name"]
        player_class = player_info.get("player_class", "Unknown")
        deaths = player_info["deaths"]

        if not deaths:
            ax.text(
                0.5,
                0.5,
                f"{player_name}: No deaths",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            return

        # Get class color
        class_color = getattr(ClassColors, player_class, self.colors["text_primary"])

        # Create color mapping for damage sources
        damage_source_colors = self._create_damage_source_colors(deaths)

        # Calculate layout dimensions - use standard plot row heights
        num_deaths = len(deaths)
        row_height = 0.6  # Standard ROW_HEIGHT from base.py
        header_height = 0.6  # Standard HEADER_HEIGHT from base.py
        title_height = 0.7  # Increased for more space above table
        total_height = title_height + header_height + (num_deaths * row_height) + 0.3

        # Setup axes
        ax.set_xlim(0, 12)
        ax.set_ylim(0, total_height)
        ax.axis("off")

        # Draw player name as title (positioned higher)
        title_y = total_height - 0.2
        ax.text(
            0.2,
            title_y,
            f"Player: {player_name}",
            fontsize=14,
            fontweight="bold",
            color=class_color,
            ha="left",
            va="top",
        )

        # Draw table headers
        header_y = total_height - title_height - 0.1
        headers = [
            (0.3, "Fight #"),
            (1.2, "Time of Death (s)"),
            (2.5, "Fight Length (s)"),
            (4.2, "Damage Source 1"),
            (7.2, "Damage Source 2"),
            (10.2, "Damage Source 3"),
        ]

        # Draw header background
        from matplotlib.patches import Rectangle

        header_rect = Rectangle(
            (0.1, header_y - header_height),
            11.8,
            header_height,
            facecolor=self.colors["header_bg"],
            edgecolor=self.colors["grid_lines"],
            linewidth=1,
        )
        ax.add_patch(header_rect)

        # Draw header text
        for x_pos, header_text in headers:
            ax.text(
                x_pos,
                header_y - header_height / 2,
                header_text,
                fontsize=10,
                fontweight="bold",
                color=self.colors["header_text"],
                ha="left",
                va="center",
            )

        # Draw data rows
        data_start_y = header_y - header_height
        for i, death in enumerate(deaths):
            row_y = data_start_y - (i + 0.5) * row_height

            # Alternating row colors
            row_color = self.colors["row_even"] if i % 2 == 0 else self.colors["row_odd"]
            row_rect = Rectangle(
                (0.1, row_y - row_height / 2),
                11.8,
                row_height,
                facecolor=row_color,
                edgecolor=self.colors["grid_lines"],
                linewidth=0.5,
            )
            ax.add_patch(row_rect)

            # Fight number
            ax.text(
                0.3,
                row_y,
                str(death["fight_id"]),
                fontsize=10,
                color=self.colors["text_primary"],
                ha="left",
                va="center",
            )

            # Time of Death (as integer)
            ax.text(
                1.2,
                row_y,
                str(int(death["fight_time_seconds"])),
                fontsize=10,
                color=self.colors["text_primary"],
                ha="left",
                va="center",
            )

            # Fight Length (as integer)
            ax.text(
                2.5,
                row_y,
                str(int(death.get("fight_length_seconds", 0))),
                fontsize=10,
                color=self.colors["text_primary"],
                ha="left",
                va="center",
            )

            # Damage sources with color coding (filter out 0% damage)
            all_damage_sources = death.get("damage_sources", [])
            # Only include damage sources with meaningful damage (> 0.0%)
            damage_sources = [src for src in all_damage_sources if src.get("hp_percentage", 0) > 0.0]
            source_positions = [4.2, 7.2, 10.2]

            for j, source_x in enumerate(source_positions):
                if j < len(damage_sources):
                    source = damage_sources[j]
                    is_killing_blow = source.get("is_killing_blow", False)

                    # Prepare damage text
                    damage_text = f"{source['name']} ({source['hp_percentage']:.1f}%)"

                    # Use color mapping for this damage source
                    source_color = damage_source_colors.get(source["name"], self.colors["text_secondary"])

                    # Use bold weight for killing blow
                    font_weight = "bold" if is_killing_blow else "normal"

                    # Render sword marker separately with larger size if killing blow
                    text_x = source_x
                    if is_killing_blow:
                        ax.text(
                            source_x,
                            row_y,
                            "⚔",
                            fontsize=20,  # Much larger sword
                            color=source_color,
                            ha="left",
                            va="center",
                            weight="bold",
                        )
                        text_x = source_x + 0.15  # Offset damage text to the right

                    ax.text(
                        text_x,
                        row_y,
                        damage_text,
                        fontsize=9,
                        color=source_color,
                        ha="left",
                        va="center",
                        weight=font_weight,
                    )
                else:
                    ax.text(
                        source_x,
                        row_y,
                        "-",
                        fontsize=9,
                        color=self.colors["text_secondary"],
                        ha="left",
                        va="center",
                    )

    def _format_damage(self, damage: int) -> str:
        """Format damage number for display."""
        if damage >= 1000000:
            return f"{damage / 1000000:.1f}M"
        elif damage >= 1000:
            return f"{damage / 1000:.1f}K"
        else:
            return str(damage)

    def save(self, filename: Optional[str] = None) -> str:
        """
        Save the plot to file.

        :param filename: Optional filename override
        :return: Path to saved file
        """
        if filename is None:
            # Generate filename from title and date
            try:
                date_obj = datetime.strptime(self.date, "%d.%m.%Y")
                date_stamp = date_obj.strftime("%Y-%m-%d")
            except (ValueError, AttributeError):
                date_stamp = datetime.now().strftime("%Y-%m-%d")

            # Clean title for filename
            import re

            clean_title = re.sub(r"[^\w\s-]", "", self.title)
            clean_title = re.sub(r"[-\s]+", "_", clean_title)
            clean_title = clean_title.strip("_").lower()

            filename = f"{date_stamp}_{clean_title}_death_timeline.png"

        # Get plots directory
        from ..config.settings import Settings

        plots_dir = Settings().plots_directory
        file_path = plots_dir / filename

        # Create the plot and save
        fig = self.create_plot()
        # Ensure background color is preserved when saving
        fig.savefig(
            file_path,
            dpi=300,
            bbox_inches="tight",
            facecolor=fig.get_facecolor(),
            edgecolor="none",
            pad_inches=0.1,
        )
        plt.close(fig)

        logger.info(f"Player deaths plot saved to {file_path}")
        return str(file_path)

    def show(self) -> None:
        """Display the plot."""
        fig = self.create_plot()
        plt.show()
        plt.close(fig)
