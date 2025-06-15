"""
Plot styling configuration.

This module provides styling constants and configuration for matplotlib plots.
"""

import matplotlib.pyplot as plt

from ..config import DEFAULT_FONT, FONT_FAMILIES, ClassColors, PlotColors


class PlotStyleManager:
    """Manages plot styling and configuration."""

    @classmethod
    def setup_plot_style(cls) -> None:
        """Configure matplotlib style settings."""
        plt.style.use("dark_background")

        plt.rcParams.update(
            {
                "figure.facecolor": PlotColors.BACKGROUND,
                "axes.facecolor": PlotColors.BACKGROUND,
                "text.color": PlotColors.TEXT_PRIMARY,
                "font.size": 12,
                "font.family": DEFAULT_FONT,
                "font.sans-serif": DEFAULT_FONT,
                "mathtext.fontset": "stixsans",  # For any math text
                "font.weight": "normal",
                "axes.labelweight": "normal",
                "axes.titleweight": "bold",
            }
        )

    @staticmethod
    def get_class_color(class_name: str) -> str:
        """
        Get color for WoW class name.

        :param class_name: Class name
        :returns: Color hex code
        """
        if not class_name:
            return PlotColors.TEXT_PRIMARY

        class_attr = class_name.upper().replace(" ", "_")
        return getattr(ClassColors, class_attr, PlotColors.TEXT_PRIMARY)

    @staticmethod
    def get_change_color(change_value: float) -> str:
        """
        Get color for change value (positive/negative/neutral).

        :param change_value: Change value
        :returns: Color hex code
        """
        if change_value > 0:
            return PlotColors.POSITIVE_CHANGE_COLOR
        elif change_value < 0:
            return PlotColors.NEGATIVE_CHANGE_COLOR
        else:
            return PlotColors.NEUTRAL_CHANGE_COLOR
