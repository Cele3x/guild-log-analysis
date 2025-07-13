"""Sprocketmonger Lockenstock boss analysis for Liberation of Undermine."""

from ..base import BossAnalysisBase
from ..registry import register_boss


@register_boss("sprocketmonger_lockenstock")
class SprocketmongerLockenstockAnalysis(BossAnalysisBase):
    """Analysis for Sprocketmonger Lockenstock encounters in Liberation of Undermine."""

    def __init__(self, api_client):
        """Initialize Sprocketmonger Lockenstock analysis with API client."""
        super().__init__(api_client)
        self.boss_name = "Sprocketmonger Lockenstock"
        self.encounter_id = 3013
        self.difficulty = 5

    CONFIG = [
        {
            "name": "Blazing Beam Deaths",
            "analysis": {
                "type": "player_deaths",
                "ability_id": 1216415,
            },
            "plot": {
                "type": "NumberPlot",
                "title": "Blazing Beam Deaths",
                "column_key_1": "blazing_beam_deaths",
                "column_header_2": "Deaths",
            },
        },
        {
            "name": "Jumbo Void Beam Deaths",
            "analysis": {
                "type": "player_deaths",
                "ability_id": 1216674,
            },
            "plot": {
                "type": "NumberPlot",
                "title": "Jumbo Void Beam Deaths",
                "column_key_1": "jumbo_void_beam_deaths",
                "column_header_2": "Deaths",
            },
        },
        {
            "name": "Screw Up's",
            "analysis": {
                "type": "table_data",
                "ability_id": 1216509,
                "data_type": "Debuffs",
            },
            "plot": {
                "type": "HitCountPlot",
                "title": "Screw Up's",
                "column_key_1": "hit_count",
                "column_header_1": "Hits",
            },
        },
        {
            "name": "Fire Traps Triggered",
            "analysis": {
                "type": "table_data",
                "ability_id": 471308,
                "data_type": "Debuffs",
            },
            "plot": {
                "type": "HitCountPlot",
                "title": "Fire Traps Triggered",
                "column_key_1": "hit_count",
                "column_header_1": "Hits",
            },
        },
        {
            "name": "Electrified",
            "analysis": {
                "type": "table_data",
                "ability_id": 466235,
                "data_type": "DamageTaken",
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "damage_taken",
                "column_header_1": "Damage",
            },
        },
        {
            "name": "Wrong Mine Triggers",
            "analysis": {
                "type": "wrong_mine_analysis",
                "debuff_ability_id": 1218342,  # Unstable Shrapnel
                "damage_ability_id": 1219047,  # Polarized Catastro-Blast
                "correlation_window_ms": 1000,
                "min_victims_threshold": 3,
                "wipe_cutoff": 4,
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "wrong_mine_triggers",
                "column_header_1": "Triggers",
            },
        },
        {
            "name": "Polarization Blast Hits",
            "analysis": {
                "type": "table_data",
                "ability_id": 1216989,
                "data_type": "DamageTaken",
            },
            "plot": {
                "type": "NumberPlot",
                "column_key_1": "damage_taken",
                "column_header_1": "Damage",
            },
        },
    ]
