"""
Example boss analysis demonstrating the new configuration-based system.

This file shows how simple it is to create a new boss analysis using
the registry-based configuration system.
"""

from typing import Any

from ...config.constants import PlayerRoles
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
            "roles": [PlayerRoles.DPS],  # Only DPS players interrupt this ability
        },
        {
            "name": "Debuff Uptime",
            "type": "debuff_uptime",
            "ability_id": 67890.0,  # Replace with actual debuff ID
            # No roles specified = all roles (tanks, healers, DPS)
        },
        {
            "name": "Add Damage",
            "type": "damage_to_actor",
            "target_game_id": 11111,  # Replace with actual game ID
            "result_key": "damage_to_adds",
            "roles": [PlayerRoles.TANK, PlayerRoles.DPS],  # Tanks and DPS handle adds
        },
        {
            "name": "Healing Done",
            "type": "damage_to_actor",  # Can be used for healing with appropriate target
            "target_game_id": 22222,  # Replace with actual healing target
            "result_key": "healing_done",
            "roles": [PlayerRoles.HEALER],  # Only healers
        },
    ]

    # Plot configuration - defines how to visualize the data
    PLOT_CONFIG = [
        {
            "analysis_name": "Boss Interrupts",
            "plot_type": "NumberPlot",
            "title": "Boss Interrupts (DPS Only)",
            "value_column": "interrupts",
            "value_column_name": "Interrupts",
            "roles": [PlayerRoles.DPS],  # Match analysis role filter
        },
        {
            "analysis_name": "Debuff Uptime",
            "plot_type": "PercentagePlot",
            "title": "Debuff Uptime (All Roles)",
            "value_column": "uptime_percentage",
            "value_column_name": "Uptime %",
            # No roles = all roles
        },
        {
            "analysis_name": "Add Damage",
            "plot_type": "NumberPlot",
            "title": "Damage to Adds (Tanks + DPS)",
            "value_column": "damage_to_adds",
            "value_column_name": "Damage",
            "roles": [PlayerRoles.TANK, PlayerRoles.DPS],
        },
        {
            "analysis_name": "Healing Done",
            "plot_type": "NumberPlot",
            "title": "Healing Done (Healers Only)",
            "value_column": "healing_done",
            "value_column_name": "Healing",
            "roles": [PlayerRoles.HEALER],
        },
    ]
