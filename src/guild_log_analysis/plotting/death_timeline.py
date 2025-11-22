"""
Death List Visualization module for Guild Log Analysis.

This module provides visualization classes for death list analysis,
creating death list visualizations similar to Warcraft Logs deaths view.
"""

import logging
from datetime import datetime
from typing import Any, Optional

import matplotlib.patches as patches
import matplotlib.pyplot as plt

from .styles import PlotColors, PlotStyleManager

logger = logging.getLogger(__name__)


class DeathTimelinePlot:
    """
    Death list visualization for death analysis.

    Creates a death list showing player deaths with damage spell information,
    formatted similar to Warcraft Logs deaths view for easy analysis.
    """

    def __init__(
        self,
        title: str,
        date: str,
        timeline_data: list[dict[str, Any]],
        figsize: tuple[int, int] = (16, 10),
    ) -> None:
        """
        Initialize death timeline plot.

        :param title: Plot title
        :param date: Date string for the plot
        :param timeline_data: List of fight timeline data
        :param figsize: Figure size tuple
        """
        self.title = title
        self.date = date
        self.timeline_data = timeline_data
        self.figsize = figsize

        # Styling constants
        self.colors = {
            "death_instant": "#FF0000",  # Red for instant deaths
            "death_normal": "#FF6B6B",  # Light red for normal deaths
            "damage_high": "#FF8C00",  # Orange for high damage
            "damage_medium": "#FFD700",  # Gold for medium damage
            "damage_low": "#FFFF99",  # Light yellow for low damage
            "timeline_bg": "#F5F5F5",  # Light gray background
            "grid_lines": "#E0E0E0",  # Grid lines
            "text_primary": PlotColors.TEXT_PRIMARY,
            "text_secondary": PlotColors.TEXT_SECONDARY,
        }

    def create_plot(self) -> plt.Figure:
        """
        Create the death timeline visualization.

        :return: Matplotlib figure object
        """
        if not self.timeline_data:
            return self._create_empty_plot()

        # Setup figure and styling
        PlotStyleManager.setup_plot_style()
        fig, axes = plt.subplots(len(self.timeline_data), 1, figsize=self.figsize, squeeze=False)

        # Handle single fight case
        if len(self.timeline_data) == 1:
            axes = [axes[0, 0]]
        else:
            axes = axes[:, 0]

        # For single fight, use simple title like "Fight 1"
        if len(self.timeline_data) == 1:
            fight_id = self.timeline_data[0]["fight_id"]
            title = f"Fight {fight_id}"
        else:
            title = self.title

        fig.suptitle(title, fontsize=20, fontweight="bold", color=self.colors["text_primary"], y=0.95)

        # Create timeline for each fight
        for i, fight_data in enumerate(self.timeline_data):
            self._draw_fight_timeline(axes[i], fight_data, i + 1)

        # Adjust layout
        plt.tight_layout()
        plt.subplots_adjust(top=0.9)

        return fig

    def _create_empty_plot(self) -> plt.Figure:
        """Create empty plot when no data is available."""
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(
            0.5,
            0.5,
            "No death timeline data available",
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

    def _draw_fight_timeline(self, ax: plt.Axes, fight_data: dict[str, Any], fight_number: int) -> None:
        """
        Draw death list for a single fight (like Warcraft Logs deaths view).

        :param ax: Matplotlib axes object
        :param fight_data: Fight timeline data
        :param fight_number: Fight number for labeling
        """
        deaths = fight_data["deaths"]

        if not deaths:
            ax.text(
                0.5,
                0.5,
                f"Fight {fight_number}: No deaths to display",
                ha="center",
                va="center",
                transform=ax.transAxes,
            )
            ax.set_xlim(0, 1)
            ax.set_ylim(0, 1)
            ax.axis("off")
            return

        # Calculate required height based on max damage sources per death
        max_damage_sources = max(len(death.get("damage_spells", [])) for death in deaths)
        max_damage_sources = min(max_damage_sources, 3)  # Limit to top 3 for space

        # Each death needs space for player info + damage sources vertically
        row_height = max(1.0, max_damage_sources * 0.3 + 0.4)  # Base height + damage sources
        total_height = len(deaths) * row_height + 2  # Extra space for header

        # Setup for list-style layout with header space
        ax.set_xlim(0, 10)
        ax.set_ylim(0, total_height)

        # Remove axes decorations for clean list appearance
        ax.set_xticks([])
        ax.set_yticks([])
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_visible(False)

        # Add table headers
        header_y = total_height - 1.2
        ax.text(
            0.5,
            header_y,
            "#",
            fontsize=12,
            fontweight="bold",
            color=self.colors["text_primary"],
            ha="center",
            va="center",
        )
        ax.text(
            2.5,
            header_y,
            "Player",
            fontsize=12,
            fontweight="bold",
            color=self.colors["text_primary"],
            ha="center",
            va="center",
        )
        ax.text(
            4.0,
            header_y,
            "Time",
            fontsize=12,
            fontweight="bold",
            color=self.colors["text_primary"],
            ha="center",
            va="center",
        )
        ax.text(
            6.5,
            header_y,
            "Damage Sources",
            fontsize=12,
            fontweight="bold",
            color=self.colors["text_primary"],
            ha="center",
            va="center",
        )

        # Add header separator line
        ax.plot([0.1, 9.9], [header_y - 0.2, header_y - 0.2], color=self.colors["grid_lines"], linewidth=1)

        # Draw death list entries with proper spacing
        for i, death in enumerate(deaths):
            y_pos = total_height - 2 - (i * row_height) - (row_height / 2)  # Center of row
            self._draw_death_list_entry(ax, death, y_pos, i + 1, row_height)

    def _draw_death_list_entry(
        self,
        ax: plt.Axes,
        death: dict[str, Any],
        y_pos: float,
        death_number: int,
        row_height: float,
    ) -> None:
        """
        Draw a single death entry in list format with vertical damage sources.

        :param ax: Matplotlib axes object
        :param death: Death event data
        :param y_pos: Y position for this death entry (center of row)
        :param death_number: Death number (1, 2, 3, etc.)
        :param row_height: Height of this row
        """
        player_name = death["player_name"]
        is_instant = death["is_instant_death"]
        damage_spells = death["damage_spells"]
        timestamp = death["timestamp"]

        # Get fight time (already calculated in analysis)
        fight_time = death.get("fight_time_seconds", timestamp / 1000.0)

        # Background rectangle for each entry
        ax.add_patch(
            patches.Rectangle(
                (0.1, y_pos - row_height / 2),
                9.8,
                row_height,
                facecolor=self.colors["timeline_bg"],
                alpha=0.3,
                edgecolor=self.colors["grid_lines"],
                linewidth=0.5,
            )
        )

        # Death number
        ax.text(
            0.5,
            y_pos,
            f"{death_number}.",
            fontsize=12,
            fontweight="bold",
            color=self.colors["text_primary"],
            ha="center",
            va="center",
        )

        # Player name with death type indicator
        player_text = player_name
        if is_instant:
            player_text += " (INSTANT)"
            name_color = self.colors["death_instant"]
        else:
            # Don't show health percentage as it's always 0.0% after death
            name_color = self.colors["death_normal"]

        ax.text(1.5, y_pos, player_text, fontsize=11, fontweight="bold", color=name_color, ha="left", va="center")

        # Fight time
        ax.text(
            4.0, y_pos, f"{fight_time:.1f}s", fontsize=10, color=self.colors["text_secondary"], ha="center", va="center"
        )

        # Top damage spells displayed vertically
        if damage_spells:
            self._draw_damage_spells_vertical(ax, damage_spells[:3], y_pos, row_height)

    def _draw_damage_spells_vertical(
        self,
        ax: plt.Axes,
        damage_spells: list[dict[str, Any]],
        y_pos: float,
        row_height: float,
    ) -> None:
        """
        Draw damage spells vertically in the damage sources column.

        :param ax: Matplotlib axes object
        :param damage_spells: List of damage spells
        :param y_pos: Y position for this death entry (center of row)
        :param row_height: Height of this row
        """
        if not damage_spells:
            ax.text(
                5.2, y_pos, "No damage data", fontsize=9, color=self.colors["text_secondary"], ha="left", va="center"
            )
            return

        # Calculate vertical spacing for damage spells
        spell_count = len(damage_spells)
        if spell_count == 1:
            # Single spell centered
            spell_positions = [y_pos]
        else:
            # Multiple spells distributed vertically within the row
            spell_spacing = min(0.25, (row_height - 0.2) / spell_count)
            start_y = y_pos + (spell_count - 1) * spell_spacing / 2
            spell_positions = [start_y - i * spell_spacing for i in range(spell_count)]

        # Draw each damage spell
        for i, spell in enumerate(damage_spells):
            damage = spell["damage"]
            ability_name = spell["ability_name"]
            health_percentage = spell.get("health_percentage", 0)

            # Format damage and create display text with health percentage
            formatted_damage = self._format_damage(damage)
            spell_text = f"{ability_name}: {formatted_damage} ({health_percentage:.0f}%)"

            # Draw the spell text
            ax.text(
                5.2,
                spell_positions[i],
                spell_text,
                fontsize=9,
                color=self.colors["text_secondary"],
                ha="left",
                va="center",
            )

    def _format_damage_spells_list(self, damage_spells: list[dict[str, Any]]) -> str:
        """
        Format damage spells list for display (concise version).

        :param damage_spells: List of damage spells
        :return: Formatted string showing main damage sources
        """
        if not damage_spells:
            return "No damage data"

        # Show top damage sources with spell names (concise format)
        spell_summaries = []
        for spell in damage_spells:
            damage = spell["damage"]
            ability_name = spell["ability_name"]

            # Shorten long ability names
            if len(ability_name) > 20:
                ability_name = ability_name[:17] + "..."

            formatted_damage = self._format_damage(damage)
            spell_summaries.append(f"{ability_name}: {formatted_damage}")

        return " | ".join(spell_summaries)

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
        fig.savefig(file_path, dpi=300, bbox_inches="tight", facecolor="white", edgecolor="none")
        plt.close(fig)

        logger.info(f"Death timeline plot saved to {file_path}")
        return str(file_path)

    def show(self) -> None:
        """Display the plot."""
        fig = self.create_plot()
        plt.show()
        plt.close(fig)
