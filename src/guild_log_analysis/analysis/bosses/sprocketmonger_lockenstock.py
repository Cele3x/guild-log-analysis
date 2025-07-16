"""Sprocketmonger Lockenstock boss analysis for Liberation of Undermine."""

import logging
from collections import defaultdict
from typing import Any, Optional

from ..base import BossAnalysisBase
from ..registry import register_boss

logger = logging.getLogger(__name__)


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
            "name": "Wire Transfer",
            "analysis": {
                "type": "table_data",
                "ability_id": 466235,
                "data_type": "DamageTaken",
            },
            "plot": {
                "type": "NumberPlot",
                "description": "Elektrisierte Flächen",
                "column_key_1": "damage_taken",
                "column_header_2": "Damage",
                "invert_change_colors": True,
            },
        },
        {
            "name": "Blazing Beam Deaths",
            "analysis": {
                "type": "table_data",
                "ability_id": 1216415,
                "data_type": "Deaths",
            },
            "plot": {
                "type": "NumberPlot",
                "description": "Kleine Feuer-Beams",
                "column_key_1": "deaths",
                "column_header_2": "Deaths",
                "invert_change_colors": True,
            },
        },
        {
            "name": "Jumbo Void Beam Deaths",
            "analysis": {
                "type": "table_data",
                "ability_id": 1216674,
                "data_type": "Deaths",
            },
            "plot": {
                "type": "NumberPlot",
                "description": "Große Void-Beams",
                "column_key_1": "deaths",
                "column_header_2": "Deaths",
                "invert_change_colors": True,
            },
        },
        {
            "name": "Screwed!",
            "analysis": {
                "type": "table_data",
                "ability_id": 1217261,
                "data_type": "Debuffs",
            },
            "plot": {
                "type": "HitCountPlot",
                "description": "Bohrer",
                "column_key_1": "hit_count",
                "column_header_2": "Hits",
                "invert_change_colors": True,
            },
        },
        {
            "name": "Fire Traps",
            "analysis": {
                "type": "table_data",
                "ability_id": 471308,
                "data_type": "Debuffs",
            },
            "plot": {
                "type": "HitCountPlot",
                "description": "Fallen auf den Fließbändern",
                "column_key_1": "hit_count",
                "column_header_2": "Hits",
                "invert_change_colors": True,
            },
        },
        {
            "name": "Rocket Barrage",
            "analysis": {
                "type": "table_data",
                "ability_id": 1216661,
                "data_type": "DamageTaken",
            },
            "plot": {
                "type": "HitCountPlot",
                "description": "Große Raketen",
                "column_key_1": "hit_count",
                "column_header_2": "hits",
                "invert_change_colors": True,
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
            },
            "plot": {
                "type": "NumberPlot",
                "description": "Mine mit falscher Polarität ausgelöst",
                "column_key_1": "wrong_mine_triggers",
                "column_header_2": "Triggers",
                "invert_change_colors": True,
            },
        },
        {
            "name": "Polarization Blast Hits",
            "analysis": {
                "type": "polarization_blast_hits_analysis",
                "ability_id": 1216989,
                "grouping_window_ms": 10000,
            },
            "plot": {
                "type": "NumberPlot",
                "description": "Zusammenstoß mit Spieler anderer Polarität",
                "column_key_1": "polarization_blast_hits",
                "column_header_2": "Hits",
                "invert_change_colors": True,
            },
        },
        {
            "name": "Damage to Boss",
            "analysis": {
                "type": "damage_to_actor",
                "target_game_id": 230583,
            },
            "plot": {
                "type": "NumberPlot",
                "description": "Verursachter Schaden",
                "column_key_1": "damage_to_boss",
                "column_header_2": "Damage",
            },
        },
        {
            "name": "Survivability",
            "analysis": {
                "type": "table_data",
                "data_type": "Survivability",
                "ability_id": 0,
            },
            "plot": {
                "type": "SurvivabilityPlot",
                "description": "Durchschnittliche Überlebensdauer",
                "column_key_1": "survivability_percentage",
                "column_header_2": "Survivability",
            },
        },
    ]

    def _execute_analysis(
        self,
        report_code: str,
        config: dict[str, Any],
        fight_ids: set[int],
        report_players: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Execute analysis for a single configuration item.

        Overrides base implementation to handle custom analysis types.
        """
        analysis_type = config["type"]

        if analysis_type == "wrong_mine_analysis":
            # Apply role filtering if specified
            filtered_players = self._filter_players_by_roles(report_players, config.get("roles", []))
            return self.analyze_wrong_mine_triggers(
                report_code=report_code,
                fight_ids=fight_ids,
                report_players=filtered_players,
                config=config,
                wipe_cutoff=config.get("wipe_cutoff"),
            )
        elif analysis_type == "polarization_blast_hits_analysis":
            # Apply role filtering if specified
            filtered_players = self._filter_players_by_roles(report_players, config.get("roles", []))
            return self.analyze_polarization_blast_hits(
                report_code=report_code,
                fight_ids=fight_ids,
                report_players=filtered_players,
                config=config,
                wipe_cutoff=config.get("wipe_cutoff"),
            )
        else:
            # Delegate to parent implementation for all other types
            return super()._execute_analysis(report_code, config, fight_ids, report_players)

    def analyze_wrong_mine_triggers(
        self,
        report_code: str,
        fight_ids: set[int],
        report_players: list[dict[str, Any]],
        config: dict[str, Any],
        wipe_cutoff: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze wrong mine triggers by correlating Unstable Shrapnel debuffs.

        This method correlates Unstable Shrapnel debuffs with subsequent
        Polarized Catastro-Blast damage.

        :param report_code: The WarcraftLogs report code
        :param fight_ids: Set of fight IDs to analyze
        :param report_players: List of players who participated in the fights
        :param config: Configuration with debuff_ability_id, damage_ability_id,
                       correlation_window_ms, min_victims_threshold
        :param wipe_cutoff: Optional wipe cutoff - if None, tracks all events; if set, stops after N deaths
        :return: List of player data with wrong mine trigger counts
        """
        debuff_ability_id = config["debuff_ability_id"]  # 1218342 - Unstable Shrapnel
        damage_ability_id = config["damage_ability_id"]  # 1219047 - Polarized Catastro-Blast
        correlation_window_ms = config.get("correlation_window_ms", 1000)
        min_victims_threshold = config.get("min_victims_threshold", 3)

        # Use default wipe cutoff if not specified
        if wipe_cutoff is None:
            from ...config.constants import DEFAULT_WIPE_CUTOFF

            wipe_cutoff = DEFAULT_WIPE_CUTOFF

        # Query for debuff applications (applydebuff events)
        debuff_query = """
        query GetUnstableShrapnelEvents(
            $reportCode: String!, $fightIDs: [Int]!, $abilityID: Float!, $wipeCutoff: Int!
        ) {
          reportData {
            report(code: $reportCode) {
              events(
                fightIDs: $fightIDs,
                abilityID: $abilityID,
                dataType: Debuffs,
                hostilityType: Friendlies,
                wipeCutoff: $wipeCutoff,
                limit: 1000
              ) {
                data
                nextPageTimestamp
              }
            }
          }
        }
        """

        # Query for damage events
        damage_query = """
        query GetPolarizedDamageEvents(
            $reportCode: String!, $fightIDs: [Int]!, $abilityID: Float!, $wipeCutoff: Int!
        ) {
          reportData {
            report(code: $reportCode) {
              events(
                fightIDs: $fightIDs,
                abilityID: $abilityID,
                dataType: DamageDone,
                hostilityType: Enemies,
                wipeCutoff: $wipeCutoff,
                limit: 1000
              ) {
                data
                nextPageTimestamp
              }
            }
          }
        }
        """

        try:
            # Use base class method to get player names
            player_names = {}
            for player in report_players:
                player_names[player.get("id")] = player.get("name")

            # Get debuff events
            debuff_variables = {
                "reportCode": report_code,
                "fightIDs": list(fight_ids),
                "abilityID": float(debuff_ability_id),
                "wipeCutoff": wipe_cutoff,
            }

            debuff_result = self.api_client.make_request(debuff_query, debuff_variables)
            if not debuff_result or "data" not in debuff_result:
                logger.warning(f"No debuff events returned for report {report_code}")
                return []

            # Get damage events
            damage_variables = {
                "reportCode": report_code,
                "fightIDs": list(fight_ids),
                "abilityID": float(damage_ability_id),
                "wipeCutoff": wipe_cutoff,
            }

            damage_result = self.api_client.make_request(damage_query, damage_variables)
            if not damage_result or "data" not in damage_result:
                logger.warning(f"No damage events returned for report {report_code}")
                return []

            # Parse events
            debuff_events = debuff_result["data"]["reportData"]["report"]["events"]["data"]
            damage_events = damage_result["data"]["reportData"]["report"]["events"]["data"]

            # Track wrong mine triggers per player
            wrong_mine_triggers = defaultdict(int)
            incidents = []

            # Analyze each debuff application
            for debuff_event in debuff_events:
                if debuff_event.get("type") == "applydebuff":
                    debuff_timestamp = debuff_event["timestamp"]
                    culprit_id = debuff_event["targetID"]
                    fight_id = debuff_event["fight"]

                    # Find correlated damage events within the time window
                    victims = set()
                    for damage_event in damage_events:
                        if (
                            damage_event.get("type") == "damage"
                            and damage_event["fight"] == fight_id
                            and damage_event["timestamp"] >= debuff_timestamp
                            and damage_event["timestamp"] <= debuff_timestamp + correlation_window_ms
                        ):
                            victims.add(damage_event["targetID"])

                    # Check if this qualifies as a wrong mine trigger (enough victims)
                    if len(victims) >= min_victims_threshold:
                        wrong_mine_triggers[culprit_id] += 1
                        incidents.append(
                            {
                                "culprit_id": culprit_id,
                                "timestamp": debuff_timestamp,
                                "fight_id": fight_id,
                                "victim_count": len(victims),
                                "victim_ids": list(victims),
                            }
                        )

            # Log detailed incident information
            if incidents:
                logger.info(f"Found {len(incidents)} wrong mine triggers in report {report_code}:")
                for incident in incidents:
                    culprit_name = player_names.get(incident["culprit_id"], f"ID {incident['culprit_id']}")
                    victim_names = [player_names.get(vid, f"ID {vid}") for vid in incident["victim_ids"]]
                    logger.info(
                        f"  Fight {incident['fight_id']}: {culprit_name} triggered wrong mine "
                        f"at {incident['timestamp']}ms, affecting {incident['victim_count']} "
                        f"players: {', '.join(victim_names)}"
                    )
            else:
                logger.info(f"No wrong mine triggers detected in report {report_code}")
                # Debug: log what events we did find
                logger.info(f"  Found {len(debuff_events)} debuff events and {len(damage_events)} damage events")

                # Log sample events for debugging
                if debuff_events:
                    sample_debuff = debuff_events[0]
                    logger.info(f"  Sample debuff event: {sample_debuff}")
                if damage_events:
                    sample_damage = damage_events[0]
                    logger.info(f"  Sample damage event: {sample_damage}")

            # Create player data structure
            player_data = []
            for player in report_players:
                player_id = player.get("id")
                trigger_count = wrong_mine_triggers.get(player_id, 0)

                player_data.append(
                    {
                        "player_name": player["name"],
                        "class": player["type"],
                        "role": player["role"],
                        "wrong_mine_triggers": trigger_count,
                    }
                )

            wipe_cutoff_info = f" (wipe cutoff: {wipe_cutoff})"
            logger.info(
                f"Analyzed wrong mine triggers: {len(incidents)} total incidents across "
                f"{len([p for p in player_data if p['wrong_mine_triggers'] > 0])} players{wipe_cutoff_info}"
            )
            return player_data

        except Exception as e:
            logger.error(f"Error analyzing wrong mine triggers for report {report_code}: {e}")
            return []

    def analyze_polarization_blast_hits(
        self,
        report_code: str,
        fight_ids: set[int],
        report_players: list[dict[str, Any]],
        config: dict[str, Any],
        wipe_cutoff: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze polarization blast hits by counting damage events with 10-second grouping.

        Hits that occur within 10 seconds of each other are counted as a single hit
        to avoid double-counting rapid successive hits on the same player.

        :param report_code: The WarcraftLogs report code
        :param fight_ids: Set of fight IDs to analyze
        :param report_players: List of players who participated in the fights
        :param config: Configuration with ability_id and grouping_window_ms
        :param wipe_cutoff: Optional wipe cutoff - if None, tracks all events; if set, stops after N deaths
        :return: List of player data with polarization blast hit counts
        """
        ability_id = config["ability_id"]  # 1216989 - Polarization Blast
        grouping_window_ms = config.get("grouping_window_ms", 10000)  # 10 seconds default

        # Use default wipe cutoff if not specified
        if wipe_cutoff is None:
            from ...config.constants import DEFAULT_WIPE_CUTOFF

            wipe_cutoff = DEFAULT_WIPE_CUTOFF

        # Query for damage events
        damage_query = """
        query GetPolarizationBlastHits(
            $reportCode: String!, $fightIDs: [Int]!, $abilityID: Float!, $wipeCutoff: Int!
        ) {
          reportData {
            report(code: $reportCode) {
              events(
                fightIDs: $fightIDs,
                abilityID: $abilityID,
                dataType: DamageDone,
                hostilityType: Enemies,
                wipeCutoff: $wipeCutoff,
                limit: 1000
              ) {
                data
                nextPageTimestamp
              }
            }
          }
        }
        """

        try:
            # Get damage events
            damage_variables = {
                "reportCode": report_code,
                "fightIDs": list(fight_ids),
                "abilityID": float(ability_id),
                "wipeCutoff": wipe_cutoff,
            }

            damage_result = self.api_client.make_request(damage_query, damage_variables)
            if not damage_result or "data" not in damage_result:
                logger.warning(f"No damage events returned for report {report_code}")
                return []

            damage_events = damage_result["data"]["reportData"]["report"]["events"]["data"]

            # Group hits by player and apply 10-second grouping
            player_hit_counts = defaultdict(int)
            player_last_hit_time = defaultdict(dict)  # player_id -> {fight_id -> last_hit_timestamp}

            for event in damage_events:
                if event.get("type") == "damage":
                    player_id = event["targetID"]
                    timestamp = event["timestamp"]
                    fight_id = event["fight"]

                    # Check if this is a new hit (more than 10 seconds since last hit)
                    if player_id not in player_last_hit_time:
                        player_last_hit_time[player_id] = {}

                    last_hit_in_fight = player_last_hit_time[player_id].get(fight_id, 0)

                    # Count as new hit if it's been more than grouping_window_ms since last hit
                    if timestamp - last_hit_in_fight > grouping_window_ms:
                        player_hit_counts[player_id] += 1
                        player_last_hit_time[player_id][fight_id] = timestamp

            # Create player data structure
            player_data = []
            for player in report_players:
                player_id = player.get("id")
                hit_count = player_hit_counts.get(player_id, 0)

                player_data.append(
                    {
                        "player_name": player["name"],
                        "class": player["type"],
                        "role": player["role"],
                        "polarization_blast_hits": hit_count,
                    }
                )

            total_hits = sum(player_hit_counts.values())
            wipe_cutoff_info = f" (wipe cutoff: {wipe_cutoff})"
            logger.info(
                f"Analyzed polarization blast hits: {total_hits} total hits across "
                f"{len([p for p in player_data if p['polarization_blast_hits'] > 0])} players{wipe_cutoff_info}"
            )
            return player_data

        except Exception as e:
            logger.error(f"Error analyzing polarization blast hits for report {report_code}: {e}")
            return []
