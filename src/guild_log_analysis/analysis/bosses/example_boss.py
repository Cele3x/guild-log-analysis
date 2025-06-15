"""
Example boss analysis demonstrating the new configuration-based system.

This file shows how simple it is to create a new boss analysis using
the registry-based configuration system.
"""

from typing import Any

from ..base import BossAnalysisBase
from ..registry import register_boss


@register_boss("example_boss")
class ExampleBossAnalysis(BossAnalysisBase):
    """Example boss analysis using configuration-based system."""

    def __init__(self, api_client: Any) -> None:
        """Initialize Example Boss analysis with API client."""
        super().__init__(api_client)
        self.boss_name = "Example Boss"
        self.encounter_id = 1234  # Replace with actual encounter ID
        self.difficulty = 5  # Mythic difficulty

    # Analysis configuration - defines what data to collect
    ANALYSIS_CONFIG = [
        {
            "name": "Boss Interrupts",
            "type": "interrupts",
            "ability_id": 12345,  # Replace with actual ability ID
        },
        {
            "name": "Debuff Uptime",
            "type": "debuff_uptime",
            "ability_id": 67890.0,  # Replace with actual debuff ID
        },
        {
            "name": "Add Damage",
            "type": "damage_to_actor",
            "target_game_id": 11111,  # Replace with actual game ID
            "result_key": "damage_to_adds",
        },
    ]

    # Plot configuration - defines how to visualize the data
    PLOT_CONFIG = [
        {
            "analysis_name": "Boss Interrupts",
            "plot_type": "NumberPlot",
            "title": "Boss Interrupts",
            "value_column": "interrupts",
            "value_column_name": "Interrupts",
        },
        {
            "analysis_name": "Debuff Uptime",
            "plot_type": "PercentagePlot",
            "title": "Debuff Uptime",
            "value_column": "uptime_percentage",
            "value_column_name": "Uptime %",
        },
        {
            "analysis_name": "Add Damage",
            "plot_type": "NumberPlot",
            "title": "Damage to Adds",
            "value_column": "damage_to_adds",
            "value_column_name": "Damage",
        },
    ]
