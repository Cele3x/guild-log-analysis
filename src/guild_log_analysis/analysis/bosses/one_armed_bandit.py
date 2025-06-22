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
        },
        {
            "name": "High Roller! Buff Uptime",
            "analysis": {
                "type": "debuff_uptime",
                "ability_id": 460444,
            },
            "plot": {
                "type": "PercentagePlot",
                "column_key_1": "uptime_percentage",
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
        },
        {
            "name": "Hits by Travelling Flames",
            "analysis": {
                "type": "damage_taken_from_ability",
                "ability_id": 1223999,
            },
            "plot": {
                "type": "HitCountPlot",
                "column_key_1": "hit_count",
                "column_key_2": "hits_by_travelling_flames",
            },
        },
        {
            "name": "Damage Taken from Falling Coins",
            "analysis": {
                "type": "damage_taken_from_ability",
                "ability_id": 460424,
            },
            "plot": {
                "type": "HitCountPlot",
                "column_key_1": "hit_count",
                "column_key_2": "damage_taken_from_falling_coins",
            },
        },
    ]
