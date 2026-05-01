"""Chimaerus boss analysis (The Dreamrift, Midnight)."""

from ..base import BossAnalysisBase
from ..registry import register_boss


@register_boss("chimaerus")
class ChimaerusAnalysis(BossAnalysisBase):
    """Analysis for Chimaerus encounters in The Dreamrift raid."""

    def __init__(self, api_client):
        """
        Initialize Chimaerus analysis with API client.

        :param api_client: WarcraftLogsAPIClient instance
        """
        super().__init__(api_client)
        self.boss_name = "Chimaerus"
        self.encounter_id = 3306
        self.difficulty = 5

    CONFIG = [
        {
            "name": "Dissonance Damage",
            "analysis": {
                "type": "table_data",
                "data_type": "DamageTaken",
                "ability_ids": [1267201, 1268666],
                "wipe_cutoff": 4,
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "damage_taken",
                "column_header_2": "Damage",
                "invert_change_colors": True,
            },
        },
        {
            "name": "All Deaths",
            "analysis": {
                "type": "table_data",
                "data_type": "Deaths",
                "wipe_cutoff": 4,
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "deaths",
                "column_header_2": "Deaths",
                "invert_change_colors": True,
            },
        },
        {
            "name": "Survivability",
            "analysis": {
                "type": "table_data",
                "data_type": "Survivability",
                "ability_id": 0,
                "wipe_cutoff": 4,
            },
            "plot": {
                "type": "SurvivabilityPlot",
                "column_key_1": "survivability_percentage",
                "column_header_2": "Survivability %",
                "description": "Average percentage of fight time survived across all attempts",
            },
        },
        {
            "name": "Healthstones and Potions Used",
            "analysis": {
                "type": "events",
                "data_type": "Healing",
                "ability_ids": [
                    6262,     # Healthstone
                    452930,   # Demonic Healthstone (Warlock)
                    1234768,  # Silvermoon Health Potion
                ],
                "event_types": ["heal"],
                "wipe_cutoff": 0,
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "hit_count",
                "column_header_2": "Healthstones + Potions",
            },
        },
        {
            "name": "Player Deaths",
            "analysis": {
                "type": "player_deaths",
                "player_names": None,
                "damage_window_ms": 10000,
                "wipe_cutoff": 0,
            },
            "plot": {
                "type": "PlayerDeathsPlot",
                "description": "Player deaths showing all deaths for each player across all fights",
                "figsize": [18, 12],
            },
        },
    ]
