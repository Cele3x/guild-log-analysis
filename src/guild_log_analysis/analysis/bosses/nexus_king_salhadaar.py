"""Nexus-King Salhadaar boss analysis."""

from ..base import BossAnalysisBase
from ..registry import register_boss


@register_boss("nexus_king_salhadaar")
class NexusKingSalhadaarAnalysis(BossAnalysisBase):
    """Analysis for Nexus-King Salhadaar encounters."""

    def __init__(self, api_client):
        """
        Initialize Nexus-King Salhadaar analysis with API client.

        :param api_client: WarcraftLogsAPIClient instance
        """
        super().__init__(api_client)
        self.boss_name = "Nexus-King Salhadaar"
        self.encounter_id = 3134
        self.difficulty = 5

    CONFIG = [
        {
            "name": "Deaths from Besiege",
            "analysis": {
                "type": "table_data",
                "data_type": "Deaths",
                "ability_id": 1227472,
                "wipe_cutoff": 5,
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "deaths",
                "column_header_2": "Deaths",
                "invert_change_colors": True,  # Fewer deaths is better
            },
        },
        {
            "name": "Missed Ghosts",
            "analysis": {
                "type": "events",
                "data_type": "Debuffs",
                "ability_id": 1224737,  # Oath-Bound debuff
                "event_types": ["applydebuff", "applydebuffstack"],
                "pull_ignore_time_ms": 15000,  # Ignore first 15 seconds
                "wipe_cutoff": 0,
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "hit_count",
                "column_header_2": "Missed Ghosts",
                "invert_change_colors": True,  # Fewer missed ghosts is better
            },
        },
        {
            "name": "Death Timeline Analysis",
            "analysis": {
                "type": "death_timeline",
                "player_names": None,  # None = all players, or list like ["Ylea", "PlayerName"]
                "damage_window_ms": 10000,
                "wipe_cutoff": 0,
            },
            "plot": {
                "type": "DeathTimelinePlot",
                "description": "Death timeline showing all deaths for each player across all fights",
                "figsize": [18, 12],
            },
        },
    ]
