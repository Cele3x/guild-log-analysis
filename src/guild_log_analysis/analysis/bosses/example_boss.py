"""
Example boss analysis demonstrating the new configuration-based system.

This file shows how simple it is to create a new boss analysis using
the registry-based configuration system with the unified table_data approach.
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

    # Configuration demonstrating all analysis and plot types
    CONFIG = [
        {
            "name": "Boss Interrupts",
            "roles": [PlayerRoles.DPS],  # Only DPS players interrupt this ability
            "analysis": {
                "type": "interrupts",
                "ability_id": 12345,  # Replace with actual ability ID
            },
            "plot": {
                "type": "NumberPlot",
                "title": "Boss Interrupts (DPS Only)",  # Optional title override
                "column_key_1": "interrupts",
                "column_header_2": "Interrupts",
                "description": "DPS players successfully interrupting the boss ability",  # Optional description
            },
        },
        {
            "name": "Debuff Uptime",
            # No roles specified = all roles (tanks, healers, DPS)
            "analysis": {
                "type": "table_data",
                "ability_id": 67890,  # Replace with actual debuff ID
                "data_type": "Debuffs",
            },
            "plot": {
                "type": "PercentagePlot",
                "title": "Debuff Uptime (All Roles)",
                "column_key_1": "uptime_percentage",
                "column_header_2": "Uptime %",
                # No description specified - will use date instead
            },
        },
        {
            "name": "Add Damage",
            "roles": [PlayerRoles.TANK, PlayerRoles.DPS],  # Tanks and DPS handle adds
            "analysis": {
                "type": "damage_to_actor",
                "target_game_id": 11111,  # Replace with actual game ID
            },
            "plot": {
                "type": "NumberPlot",
                "title": "Damage to Adds (Tanks + DPS)",
                "column_key_1": "add_damage",
                "column_header_2": "Damage",
            },
        },
        {
            "name": "Healing Done",
            "roles": [PlayerRoles.HEALER],  # Only healers
            "analysis": {
                "type": "damage_to_actor",  # Can be used for healing with appropriate target
                "target_game_id": 22222,  # Replace with actual healing target
            },
            "plot": {
                "type": "NumberPlot",
                "title": "Healing Done (Healers Only)",
                "column_key_1": "healing_done",
                "column_header_2": "Healing",
            },
        },
        {
            "name": "Damage Taken from Fire",
            "analysis": {
                "type": "table_data",
                "ability_id": 33333,  # Replace with actual ability ID
                "data_type": "DamageTaken",
            },
            "plot": {
                "type": "HitCountPlot",
                "title": "Fire Damage Taken",
                "column_key_1": "hit_count",
                "column_header_2": "Hits",
                "column_key_2": "damage_taken",
                "column_header_3": "Damage Taken",
                "invert_change_colors": True,  # Less damage taken is better
            },
        },
        {
            "name": "Absorbed Damage",
            "roles": [PlayerRoles.TANK],  # Tanks typically absorb damage
            "analysis": {
                "type": "damage_to_actor",
                "target_game_id": 44444,  # Replace with actual target
                "filter_expression": "absorbedDamage > 0",
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "absorbed_damage",
                "column_header_2": "Absorbed",
            },
        },
        {
            "name": "High Tolerance Interrupts",
            "roles": [PlayerRoles.DPS],
            "analysis": {
                "type": "interrupts",
                "ability_id": 12345,  # Replace with actual ability ID
                "wipe_cutoff": 10,  # Skip events after 10 people died
            },
            "plot": {
                "type": "NumberPlot",
                "title": "Interrupts (High Death Tolerance)",
                "column_key_1": "interrupts",
                "column_header_2": "Interrupts",
            },
        },
        {
            "name": "Low Tolerance Debuff",
            "analysis": {
                "type": "table_data",
                "ability_id": 67890,  # Replace with actual debuff ID
                "data_type": "Debuffs",
                "wipe_cutoff": 2,  # Stop counting after 2 people died
            },
            "plot": {
                "type": "PercentagePlot",
                "title": "Debuff Uptime (Low Death Tolerance)",
                "column_key_1": "uptime_percentage",
                "column_header_2": "Uptime %",
            },
        },
        {
            "name": "Deaths from Fire Mechanic",
            "analysis": {
                "type": "table_data",
                "ability_id": 33333,  # Only deaths from specific ability
                "data_type": "Deaths",
                "wipe_cutoff": 5,  # Count deaths before wipe threshold
            },
            "plot": {
                "type": "NumberPlot",
                "title": "Deaths from Fire Mechanic",
                "column_key_1": "deaths",
                "column_header_2": "Deaths",
            },
        },
        {
            "name": "All Deaths",
            "analysis": {
                "type": "table_data",
                "data_type": "Deaths",
                # No ability_id = all deaths
                "wipe_cutoff": 3,
            },
            "plot": {
                "type": "NumberPlot",
                "title": "All Deaths (Wipe Cutoff 3)",
                "column_key_1": "deaths",
                "column_header_2": "Deaths",
            },
        },
        {
            "name": "Player Survivability",
            "analysis": {
                "type": "table_data",
                "data_type": "Survivability",
                "ability_id": 0,  # Not used for survivability, but required by table query
                "wipe_cutoff": 4,  # Standard wipe cutoff
            },
            "plot": {
                "type": "SurvivabilityPlot",
                "title": "Average Survivability",
                "column_key_1": "survivability_percentage",
                "column_header_2": "Survivability %",
                "description": "Average percentage of fight time survived across all attempts",
            },
        },
    ]
