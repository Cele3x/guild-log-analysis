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

    # Analysis configuration
    ANALYSIS_CONFIG = [
        {
            "name": "Overload! Interrupts",
            "type": "interrupts",
            "ability_id": 460582.0,
        },
        {
            "name": "High Roller Uptime",
            "type": "debuff_uptime",
            "ability_id": 460444.0,
        },
        {
            "name": "Premium Dynamite Booties Damage",
            "type": "damage_to_actor",
            "target_game_id": 231027,
            "result_key": "damage_to_dynamite_booties",
            "roles": [PlayerRoles.DPS],
        },
        {
            "name": "Reel Assistants Damage",
            "type": "damage_to_actor",
            "target_game_id": 228463,
            "result_key": "damage_to_reel_assistants",
            "roles": [PlayerRoles.DPS],
        },
        {
            "name": "Boss Damage",
            "type": "damage_to_actor",
            "target_game_id": 228458,
            "result_key": "damage_to_boss",
        },
        {
            "name": "Absorbed Damage to Reel Assistants",
            "type": "damage_to_actor",
            "target_game_id": 228463,
            "result_key": "absorbed_damage_to_reel_assistants",
            "filter_expression": "absorbedDamage > 0",
            "roles": [PlayerRoles.DPS],
        },
        {
            "name": "Damage Taken from Travelling Flames",
            "type": "damage_taken_from_ability",
            "ability_id": 1223999.0,
            "result_key": "damage_taken_from_travelling_flames",
        },
        {
            "name": "Damage Taken from Pay-Line",
            "type": "damage_taken_from_ability",
            "ability_id": 460424.0,
            "result_key": "damage_taken_from_payline",
        },
    ]

    # Plot configuration
    PLOT_CONFIG = [
        {
            "analysis_name": "Overload! Interrupts",
            "plot_type": "NumberPlot",
            "title": "Overload! Interrupts",
            "value_column": "interrupts",
            "value_column_name": "Interrupts",
        },
        {
            "analysis_name": "High Roller Uptime",
            "plot_type": "PercentagePlot",
            "title": "High Roller Uptime",
            "value_column": "uptime_percentage",
            "value_column_name": "Uptime",
        },
        {
            "analysis_name": "Premium Dynamite Booties Damage",
            "plot_type": "NumberPlot",
            "title": "Schaden auf Geschenke",
            "value_column": "damage_to_dynamite_booties",
            "value_column_name": "Schaden",
            "roles": [PlayerRoles.DPS],
        },
        {
            "analysis_name": "Reel Assistants Damage",
            "plot_type": "NumberPlot",
            "title": "Schaden auf Reel Assistants",
            "value_column": "damage_to_reel_assistants",
            "value_column_name": "Schaden",
            "roles": [PlayerRoles.DPS],
        },
        {
            "analysis_name": "Boss Damage",
            "plot_type": "NumberPlot",
            "title": "Schaden auf Boss",
            "value_column": "damage_to_boss",
            "value_column_name": "Schaden",
        },
        {
            "analysis_name": "Absorbed Damage to Reel Assistants",
            "plot_type": "NumberPlot",
            "title": "Absorbierter Schaden auf Reel Assistants",
            "value_column": "absorbed_damage_to_reel_assistants",
            "value_column_name": "Absorbierter Schaden",
            "roles": [PlayerRoles.DPS],
        },
        {
            "analysis_name": "Damage Taken from Travelling Flames",
            "plot_type": "HitCountPlot",
            "title": "Schaden durch Travelling Flames",
            "value_column": "hit_count",
            "value_column_name": "Anzahl",
            "damage_column": "damage_taken_from_travelling_flames",
        },
        {
            "analysis_name": "Damage Taken from Pay-Line",
            "plot_type": "HitCountPlot",
            "title": "Schaden durch Coins",
            "value_column": "hit_count",
            "value_column_name": "Anzahl",
            "damage_column": "damage_taken_from_payline",
        },
    ]
