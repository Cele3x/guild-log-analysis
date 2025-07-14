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
            "name": "Blazing Beam Deaths",
            "analysis": {
                "type": "table_data",
                "ability_id": 1216415,
                "data_type": "Deaths",
            },
            "plot": {
                "type": "NumberPlot",
                "title": "Blazing Beam Deaths",
                "column_key_1": "deaths",
                "column_header_2": "Deaths",
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
                "title": "Jumbo Void Beam Deaths",
                "column_key_1": "deaths",
                "column_header_2": "Deaths",
            },
        },
        {
            "name": "Screw Up's",
            "analysis": {
                "type": "table_data",
                "ability_id": 1217261,
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

    def _execute_analysis(
        self,
        report_code: str,
        config: dict[str, Any],
        fight_ids: set[int],
        report_players: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Execute analysis for a single configuration item.

        Overrides base implementation to handle wrong_mine_analysis type.
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

        # Query for player names (for readable results)
        players_query = """
        query GetPlayerNames($reportCode: String!) {
          reportData {
            report(code: $reportCode) {
              masterData {
                actors(type: "Player") {
                  id
                  name
                  server
                  type
                  subType
                }
              }
            }
          }
        }
        """

        # Query for debuff applications (applydebuff events)
        debuff_query = """
        query GetUnstableShrapnelEvents($reportCode: String!, $fightIDs: [Int]!, $abilityID: Float!) {
          reportData {
            report(code: $reportCode) {
              events(
                fightIDs: $fightIDs,
                abilityID: $abilityID,
                dataType: Debuffs,
                hostilityType: Friendlies,
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
        query GetPolarizedDamageEvents($reportCode: String!, $fightIDs: [Int]!, $abilityID: Float!) {
          reportData {
            report(code: $reportCode) {
              events(
                fightIDs: $fightIDs,
                abilityID: $abilityID,
                dataType: DamageDone,
                hostilityType: Enemies,
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
            # Get player names for readable results
            players_variables = {"reportCode": report_code}
            players_result = self.api_client.make_request(players_query, players_variables)

            player_names = {}
            if players_result and "data" in players_result:
                actors = players_result["data"]["reportData"]["report"]["masterData"]["actors"]
                for actor in actors:
                    player_names[actor["id"]] = actor["name"]

            # Get debuff events
            debuff_variables = {
                "reportCode": report_code,
                "fightIDs": list(fight_ids),
                "abilityID": float(debuff_ability_id),
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
            }

            damage_result = self.api_client.make_request(damage_query, damage_variables)
            if not damage_result or "data" not in damage_result:
                logger.warning(f"No damage events returned for report {report_code}")
                return []

            # Parse events
            debuff_events = debuff_result["data"]["reportData"]["report"]["events"]["data"]
            damage_events = damage_result["data"]["reportData"]["report"]["events"]["data"]

            # Get death events if wipe cutoff is specified
            wipe_cutoff_timestamps = {}  # fight_id -> timestamp when wipe cutoff reached
            if wipe_cutoff is not None:
                death_query = """
                query GetDeathEvents($reportCode: String!, $fightIDs: [Int]!) {
                  reportData {
                    report(code: $reportCode) {
                      events(
                        fightIDs: $fightIDs,
                        dataType: Deaths,
                        hostilityType: Friendlies,
                        limit: 1000
                      ) {
                        data
                      }
                    }
                  }
                }
                """

                death_variables = {
                    "reportCode": report_code,
                    "fightIDs": list(fight_ids),
                }

                death_result = self.api_client.make_request(death_query, death_variables)
                if death_result and "data" in death_result:
                    death_events = death_result["data"]["reportData"]["report"]["events"]["data"]

                    # Calculate wipe cutoff timestamp for each fight
                    death_counts = defaultdict(int)
                    for death_event in death_events:
                        if death_event.get("type") == "death":
                            fight_id = death_event["fight"]
                            death_counts[fight_id] += 1

                            # Record when wipe cutoff is reached
                            if death_counts[fight_id] == wipe_cutoff and fight_id not in wipe_cutoff_timestamps:
                                wipe_cutoff_timestamps[fight_id] = death_event["timestamp"]
                                logger.debug(f"Wipe cutoff reached in fight {fight_id} at {death_event['timestamp']}ms")

            # Track wrong mine triggers per player
            wrong_mine_triggers = defaultdict(int)
            incidents = []

            # Analyze each debuff application
            for debuff_event in debuff_events:
                if debuff_event.get("type") == "applydebuff":
                    debuff_timestamp = debuff_event["timestamp"]
                    culprit_id = debuff_event["targetID"]
                    fight_id = debuff_event["fight"]

                    # Skip events after wipe cutoff if specified
                    if wipe_cutoff is not None and fight_id in wipe_cutoff_timestamps:
                        if debuff_timestamp > wipe_cutoff_timestamps[fight_id]:
                            continue

                    # Find correlated damage events within the time window
                    victims = set()
                    for damage_event in damage_events:
                        if (
                            damage_event.get("type") == "damage"
                            and damage_event["fight"] == fight_id
                            and damage_event["timestamp"] >= debuff_timestamp
                            and damage_event["timestamp"] <= debuff_timestamp + correlation_window_ms
                        ):

                            # Skip damage events after wipe cutoff if specified
                            if wipe_cutoff is not None and fight_id in wipe_cutoff_timestamps:
                                if damage_event["timestamp"] > wipe_cutoff_timestamps[fight_id]:
                                    continue

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

            wipe_cutoff_info = f" (wipe cutoff: {wipe_cutoff})" if wipe_cutoff is not None else " (no wipe cutoff)"
            logger.info(
                f"Analyzed wrong mine triggers: {len(incidents)} total incidents across "
                f"{len([p for p in player_data if p['wrong_mine_triggers'] > 0])} players{wipe_cutoff_info}"
            )
            return player_data

        except Exception as e:
            logger.error(f"Error analyzing wrong mine triggers for report {report_code}: {e}")
            return []
