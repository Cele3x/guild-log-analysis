"""One-Armed Bandit boss analysis for Liberation of Undermine."""

from ...config.constants import PlayerRoles
from ..base import BossAnalysisBase
from ..registry import register_boss


@register_boss("one_armed_bandit")
class OneArmedBanditAnalysis(BossAnalysisBase):
    """Analysis for One-Armed Bandit encounters in Liberation of Undermine."""

    def __init__(self, api_client):
        """Initialize One-Armed Bandit analysis with API client."""
        super().__init__(api_client)
        self.boss_name = "One-Armed Bandit"
        self.encounter_id = 3014
        self.difficulty = 5

    CONFIG = [
        {
            "name": "Overload! Interrupts",
            "analysis": {
                "type": "interrupts",
                "ability_id": 460582,
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "interrupts",
            },
            "progress_plot": {
                "enabled": True,
                "column_key": "interrupts",
                "y_axis_label": "Interrupts per Hour",
                "normalize_by_duration": True,
                "role_categories": {
                    "tanks_healers": "Tanks & Healers",
                    "melee_dps": "Melee DPS",
                    "ranged_dps": "Ranged DPS",
                },
            },
        },
        {
            "name": "High Roller! Buff Uptime",
            "analysis": {
                "type": "table_data",
                "ability_id": 460444,
                "data_type": "Debuffs",
            },
            "plot": {
                "type": "PercentagePlot",
                "column_key_1": "uptime_percentage",
            },
            "progress_plot": {
                "enabled": True,
                "column_key": "uptime_percentage",
                "y_axis_label": "High Roller! Buff Uptime (%)",
                "normalize_by_duration": False,
                "role_categories": {
                    "tanks_healers": "Tanks & Healers",
                    "melee_dps": "Melee DPS",
                    "ranged_dps": "Ranged DPS",
                },
            },
        },
        {
            "name": "Damage to Small Packages",
            "roles": [PlayerRoles.DPS],
            "analysis": {
                "type": "damage_to_actor",
                "target_game_id": 231027,
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "damage_to_small_packages",
            },
            "progress_plot": {
                "enabled": True,
                "column_key": "damage_to_small_packages",
                "y_axis_label": "Damage to Small Packages per Hour",
                "normalize_by_duration": True,
                "role_categories": {
                    "melee_dps": "Melee DPS",
                    "ranged_dps": "Ranged DPS",
                },
            },
        },
        {
            "name": "Damage to Reel Assistants",
            "roles": [PlayerRoles.DPS],
            "analysis": {
                "type": "damage_to_actor",
                "target_game_id": 228463,
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "damage_to_reel_assistants",
            },
            "progress_plot": {
                "enabled": True,
                "column_key": "damage_to_reel_assistants",
                "y_axis_label": "Damage to Reel Assistants per Hour",
                "normalize_by_duration": True,
                "role_categories": {
                    "melee_dps": "Melee DPS",
                    "ranged_dps": "Ranged DPS",
                },
            },
        },
        {
            "name": "Damage to Boss",
            "analysis": {
                "type": "damage_to_actor",
                "target_game_id": 228458,
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "damage_to_boss",
            },
            "progress_plot": {
                "enabled": True,
                "column_key": "damage_to_boss",
                "y_axis_label": "Damage to Boss per Hour",
                "normalize_by_duration": True,
                "role_categories": {
                    "tanks_healers": "Tanks & Healers",
                    "melee_dps": "Melee DPS",
                    "ranged_dps": "Ranged DPS",
                },
            },
        },
        {
            "name": "Absorbed Damage to Reel Assistants",
            "roles": [PlayerRoles.DPS],
            "analysis": {
                "type": "damage_to_actor",
                "target_game_id": 228463,
                "filter_expression": "absorbedDamage > 0",
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "absorbed_damage_to_reel_assistants",
            },
            "progress_plot": {
                "enabled": True,
                "column_key": "absorbed_damage_to_reel_assistants",
                "y_axis_label": "Absorbed Damage to Reel Assistants per Hour",
                "normalize_by_duration": True,
                "role_categories": {
                    "melee_dps": "Melee DPS",
                    "ranged_dps": "Ranged DPS",
                },
            },
        },
        {
            "name": "Hits by Travelling Flames",
            "analysis": {
                "type": "table_data",
                "ability_id": 1223999,
                "data_type": "DamageTaken",
            },
            "plot": {
                "type": "HitCountPlot",
                "column_key_1": "hit_count",
                "column_key_2": "damage_taken",
            },
            "progress_plot": {
                "enabled": True,
                "column_key": "hit_count",
                "y_axis_label": "Hits by Travelling Flames per Hour",
                "normalize_by_duration": True,
                "role_categories": {
                    "tanks_healers": "Tanks & Healers",
                    "melee_dps": "Melee DPS",
                    "ranged_dps": "Ranged DPS",
                },
            },
        },
        {
            "name": "Damage Taken from Falling Coins",
            "analysis": {
                "type": "table_data",
                "ability_id": 460424,
                "data_type": "DamageTaken",
            },
            "plot": {
                "type": "HitCountPlot",
                "column_key_1": "hit_count",
                "column_key_2": "damage_taken",
            },
            "progress_plot": {
                "enabled": True,
                "column_key": "hit_count",
                "y_axis_label": "Hits from Falling Coins per Hour",
                "normalize_by_duration": True,
                "role_categories": {
                    "tanks_healers": "Tanks & Healers",
                    "melee_dps": "Melee DPS",
                    "ranged_dps": "Ranged DPS",
                },
            },
        },
    ]
