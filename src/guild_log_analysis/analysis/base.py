"""
Base analysis module for Guild Log Analysis.

This module provides the base class for all boss-specific analyses,
containing common functionality and abstract methods.
"""

import logging
from abc import ABC
from collections import defaultdict
from datetime import datetime
from typing import Any, Optional

import pandas as pd

from ..api.client import WarcraftLogsAPIClient
from ..config.constants import DEFAULT_WIPE_CUTOFF
from ..plotting.base import HitCountPlot, NumberPlot, PercentagePlot
from ..plotting.multi_line import MultiLinePlot
from ..utils.helpers import deduplicate_players, filter_players_by_roles

logger = logging.getLogger(__name__)


class BossAnalysisBase(ABC):
    """
    Abstract base class for boss-specific analysis implementations.

    This class provides common functionality for analyzing Warcraft Logs data
    and defines the interface that all boss analyzes must implement.
    """

    def __init__(self, api_client: WarcraftLogsAPIClient) -> None:
        """
        Initialize the boss analysis.

        :param api_client: The Warcraft Logs API client instance
        """
        self.api_client = api_client
        self.boss_id: Optional[int] = None
        self.boss_name: Optional[str] = None
        self.encounter_id: Optional[int] = None
        self.difficulty: int = 5  # Default to Mythic difficulty
        self.results: list[dict[str, Any]] = []

        # Configuration attributes for registry-based system
        self.CONFIG: list[dict[str, Any]] = getattr(self, "CONFIG", [])

    @staticmethod
    def _name_to_key(name: str) -> str:
        """Convert analysis name to snake_case result key."""
        import re

        # Remove special characters and replace with spaces, then convert to snake_case
        cleaned = re.sub(r"[^\w\s]", " ", name)  # Replace non-alphanumeric with spaces
        cleaned = re.sub(r"\s+", "_", cleaned.strip())  # Replace multiple spaces with single underscore
        return cleaned.lower()

    def analyze(self, report_codes: list[str]) -> None:
        """
        Analyze reports for this specific boss using configuration.

        :param report_codes: List of Warcraft Logs report codes to analyze
        """
        if self.CONFIG:
            # Use unified configuration-based analysis
            self._analyze_generic(report_codes)
        else:
            # Fall back to legacy analyze method
            self._analyze_legacy(report_codes)

    def _analyze_legacy(self, report_codes: list[str]) -> None:
        """
        Legacy analyze method for backwards compatibility.

        Override this in subclasses that don't use configuration.

        :param report_codes: List of Warcraft Logs report codes to analyze
        """
        raise NotImplementedError("Either implement CONFIG or override _analyze_legacy")

    def _analyze_generic(self, report_codes: list[str]) -> None:
        """
        Analyze using configuration.

        :param report_codes: List of Warcraft Logs report codes to analyze
        """
        logger.info(f"Starting {self.boss_name} analysis for {len(report_codes)} reports")

        for report_code in report_codes:
            try:
                logger.info(f"Processing report {report_code}")
                self._process_report_generic(report_code)
            except Exception as e:
                logger.error(f"Error processing report {report_code}: {e}")
                continue

    def _process_report_generic(self, report_code: str) -> None:
        """
        Process a single report using configuration.

        :param report_code: The WarcraftLogs report code
        """
        logger.debug(f"Processing report {report_code} for {self.boss_name}")

        # Get fights for this report
        fight_ids = self.get_fight_ids(report_code)
        if not fight_ids:
            return

        # Get timestamp of first fight
        start_time = self.get_start_time(report_code, fight_ids)

        # Get total fight duration
        total_duration = self.get_total_fight_duration(report_code, fight_ids)

        report_results = {
            "starttime": start_time,
            "reportCode": report_code,
            "analysis": [],
            "fight_ids": fight_ids,
            "total_duration": total_duration,
        }

        # Get players who participated in these specific fights
        report_players = self.get_participants(report_code, fight_ids)
        if not report_players:
            return

        # Execute all configured analyses
        for config in self.CONFIG:
            try:
                # Extract analysis config from unified CONFIG
                analysis_config = {
                    "name": config["name"],
                    "result_key": self._name_to_key(config["name"]),
                    **config["analysis"],
                }
                if "roles" in config:
                    analysis_config["roles"] = config["roles"]

                data = self._execute_analysis(analysis_config, report_code, fight_ids, report_players)
                report_results["analysis"].append({"name": analysis_config["name"], "data": data})
            except Exception as e:
                logger.error(f"Error executing analysis {config['name']}: {e}")
                continue

        self.results.append(report_results)
        logger.info(f"Successfully processed report {report_code} with {len(report_results['analysis'])} analyses")

    def _execute_analysis(
        self,
        config: dict[str, Any],
        report_code: str,
        fight_ids: set[int],
        report_players: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Execute a single analysis based on configuration.

        :param config: Analysis configuration dictionary
        :param report_code: The WarcraftLogs report code
        :param fight_ids: Set of fight IDs to analyze
        :param report_players: List of players who participated in the fights
        :return: Analysis results data
        """
        # Apply role filtering if specified
        filtered_players = self._filter_players_by_roles(report_players, config.get("roles", []))

        analysis_type = config["type"]

        if analysis_type == "interrupts":
            data = self.analyze_interrupts(
                report_code=report_code,
                fight_ids=fight_ids,
                report_players=filtered_players,
                ability_id=config["ability_id"],
                wipe_cutoff=config.get("wipe_cutoff", DEFAULT_WIPE_CUTOFF),
            )
        elif analysis_type == "debuff_uptime":
            data = self.analyze_debuff_uptime(
                report_code=report_code,
                fight_ids=fight_ids,
                report_players=filtered_players,
                ability_id=config["ability_id"],
                wipe_cutoff=config.get("wipe_cutoff", DEFAULT_WIPE_CUTOFF),
                filter_expression=config.get("filter_expression"),
            )
        elif analysis_type == "damage_to_actor":
            data = self.get_damage_to_actor(
                report_code=report_code,
                fight_ids=fight_ids,
                target_game_id=config["target_game_id"],
                report_players=filtered_players,
                filter_expression=config.get("filter_expression"),
                wipe_cutoff=config.get("wipe_cutoff", DEFAULT_WIPE_CUTOFF),
            )
            # Rename damage field if result_key is specified
            if "result_key" in config and config["result_key"] != "damage":
                for player_data in data:
                    player_data[config["result_key"]] = player_data.pop("damage")
        elif analysis_type == "damage_taken_from_ability":
            data = self.analyze_damage_taken_from_ability(
                report_code=report_code,
                fight_ids=fight_ids,
                report_players=filtered_players,
                ability_id=config["ability_id"],
                wipe_cutoff=config.get("wipe_cutoff", DEFAULT_WIPE_CUTOFF),
                filter_expression=config.get("filter_expression"),
            )
            # Rename damage field if result_key is specified
            if "result_key" in config and config["result_key"] != "damage_taken":
                for player_data in data:
                    player_data[config["result_key"]] = player_data.pop("damage_taken")
        elif analysis_type == "player_deaths":
            data = self.analyze_player_deaths(
                report_code=report_code,
                fight_ids=fight_ids,
                report_players=filtered_players,
                wipe_cutoff=config.get("wipe_cutoff", DEFAULT_WIPE_CUTOFF),
                filter_expression=config.get("filter_expression"),
                ability_id=config.get("ability_id"),
            )
            # Rename deaths field if result_key is specified
            if "result_key" in config and config["result_key"] != "deaths":
                for player_data in data:
                    player_data[config["result_key"]] = player_data.pop("deaths")
        elif analysis_type == "table_data":
            data = self.analyze_table_data(
                report_code=report_code,
                config=config,
                fight_ids=fight_ids,
            )
        elif analysis_type == "wrong_mine_analysis":
            data = self.analyze_wrong_mine_triggers(
                report_code=report_code,
                fight_ids=fight_ids,
                report_players=filtered_players,
                config=config,
                wipe_cutoff=config.get("wipe_cutoff"),  # Pass None if not specified
            )
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

        return data

    def _filter_players_by_roles(self, players: list[dict[str, Any]], roles: list[str]) -> list[dict[str, Any]]:
        """
        Filter players by specified roles.

        :param players: List of player dictionaries
        :param roles: List of role names to include (empty list means all roles)
        :return: Filtered list of players
        """
        return filter_players_by_roles(players, roles)

    def get_fight_ids(self, report_code: str) -> Optional[set[int]]:
        """
        Get unique fight IDs for this boss from a report.

        :param report_code: The WarcraftLogs report code to query
        :return: Set of fight IDs or None if not found
        """
        query = """
        query GetFights(
          $reportCode: String!, $encounterId: Int!, $difficulty: Int!
        ) {
          reportData {
            report(code: $reportCode) {
              fights(
                encounterID: $encounterId, difficulty: $difficulty
              ) {
                id
                name
                difficulty
                encounterID
              }
            }
          }
        }
        """

        variables = {
            "reportCode": report_code,
            "encounterId": self.encounter_id,
            "difficulty": self.difficulty,
        }

        try:
            result = self.api_client.make_request(query, variables)
        except Exception as e:
            logger.error(f"Error fetching fight IDs for report {report_code}: {e}")
            return None

        # Navigate to fights data
        report_data = result["data"]["reportData"]["report"]
        if not report_data:
            logger.warning(f"Report {report_code} not found")
            return None

        fights = report_data.get("fights", [])
        if not fights:
            logger.warning(
                f"No fights found for boss {self.encounter_id} "
                f"(difficulty {self.difficulty}) in report {report_code}"
            )
            return None

        # Extract unique fight IDs
        fight_ids = {fight["id"] for fight in fights if "id" in fight}

        if not fight_ids:
            logger.warning(f"No valid fight IDs found in report {report_code}")
            return None

        logger.info(f'Found {len(fight_ids)} fights for boss "{self.boss_name}" in report {report_code}')
        return fight_ids

    def get_start_time(self, report_code: str, fight_ids: set[int]) -> Optional[float]:
        """
        Get the start time for the fights.

        :param report_code: The WarcraftLogs report code
        :param fight_ids: Set of fight IDs
        :return: Unix timestamp in seconds or None if failed
        """
        query = """
        query GetFightStartTimes($reportCode: String!, $fightIDs: [Int]) {
          reportData {
            report(code: $reportCode) {
              startTime
              fights(fightIDs: $fightIDs) {
                id
                name
                startTime
                endTime
              }
            }
          }
        }
        """
        variables = {"reportCode": report_code, "fightIDs": list(fight_ids)}
        result = self.api_client.make_request(query, variables)
        report_data = result["data"]["reportData"]["report"]
        if not report_data:
            return None

        fights = report_data["fights"]
        if not fights:
            return None

        # Get report start time (absolute Unix timestamp in milliseconds)
        report_start_ms = report_data["startTime"]

        # Get the earliest fight relative start time
        earliest_fight_relative_ms = min(fight["startTime"] for fight in fights)

        # Calculate actual earliest start time in milliseconds
        earliest_absolute_ms = report_start_ms + earliest_fight_relative_ms

        # Convert to Unix timestamp in seconds for easy date conversion
        earliest_unix_seconds = earliest_absolute_ms / 1000

        return earliest_unix_seconds

    def get_total_fight_duration(self, report_code: str, fight_ids: set[int]) -> Optional[int]:
        """
        Get the total duration in milliseconds for specified fight IDs.

        :param report_code: The WarcraftLogs report code
        :param fight_ids: Set of fight IDs to calculate total duration for
        :return: Total duration in milliseconds or None if failed
        """
        query = """
        query GetFightDurations($reportCode: String!, $fightIDs: [Int]) {
          reportData {
            report(code: $reportCode) {
              fights(fightIDs: $fightIDs) {
                id
                startTime
                endTime
              }
            }
          }
        }
        """

        variables = {"reportCode": report_code, "fightIDs": list(fight_ids)}

        try:
            result = self.api_client.make_request(query, variables)
            report_data = result["data"]["reportData"]["report"]

            if not report_data:
                logger.warning(f"No report found for code: {report_code}")
                return None

            fights = report_data["fights"]
            if not fights:
                logger.warning(f"No fights found for fight IDs: {fight_ids}")
                return None

            # Calculate total duration by summing individual fight durations
            total_duration_ms = 0
            for fight in fights:
                fight_duration = fight["endTime"] - fight["startTime"]
                total_duration_ms += fight_duration
                logger.debug(f"Fight {fight['id']}: {fight_duration}ms")

            logger.info(f"Total duration for {len(fights)} fights: {total_duration_ms}ms")
            return total_duration_ms

        except Exception as e:
            logger.error(f"Error getting fight durations: {e}")
            return None

    def get_participants(self, report_code: str, fight_ids: set[int]) -> Optional[list[dict[str, Any]]]:
        """
        Get player details for specific fights in a report.

        :param report_code: The WarcraftLogs report code
        :param fight_ids: Set of fight IDs to get player details for
        :return: Player details data or None if failed
        """
        query = """
        query GetPlayerDetails($reportCode: String!, $fightIds: [Int!]!) {
          reportData {
            report(code: $reportCode) {
              playerDetails(fightIDs: $fightIds)
            }
          }
        }
        """

        variables = {"reportCode": report_code, "fightIds": list(fight_ids)}

        result = self.api_client.make_request(query, variables)

        player_details = result.get("data", {}).get("reportData", {}).get("report", {}).get("playerDetails", {})

        if not player_details:
            logger.warning(
                f"No players found for report code \"{report_code}\" and fight IDs {', '.join(map(str, fight_ids))}"
            )
            return None

        players = []

        # Process each role
        role_mappings = [
            ("tanks", "tank"),
            ("healers", "healer"),
            ("dps", "dps"),
        ]

        # Access the nested playerDetails data
        player_data = player_details["data"]["playerDetails"]

        for role_key, role_name in role_mappings:
            for player in player_data.get(role_key, []):
                player_info = {
                    "id": player["id"],
                    "name": player["name"],
                    "type": player["type"].lower(),
                    "role": role_name,
                }
                players.append(player_info)
                logger.debug(
                    f"ID: {player_info['id']}, "
                    f"Name: {player_info['name']}, "
                    f"Class: {player_info['type']}, "
                    f"Role: {player_info['role']}"
                )

        logger.info(f"Found a total of {len(players)} players before deduplication.")

        # Deduplicate players who might appear in multiple roles
        deduplicated_players = deduplicate_players(players, key="name")
        logger.info(f"After deduplication: {len(deduplicated_players)} unique players.")

        return deduplicated_players if deduplicated_players else None

    def find_analysis_data(
        self, analysis_name: str, value_column: str, name_column: str
    ) -> tuple[Optional[list[dict]], Optional[dict[str, Any]]]:
        """
        Find current and previous analysis data by name and starttime.

        :param analysis_name: Name of the analysis to find
        :param value_column: Column name for the value to extract for previous data
        :param name_column: Column name for the player/item name
        :returns: Tuple of (current_data, previous_dict) or (None, None) if not found
        :raises ValueError: If analysis not found in data
        """
        # Filter reports that contain the specified analysis
        matching_reports = []
        for report in self.results:
            for analysis in report.get("analysis", []):
                if analysis.get("name") == analysis_name:
                    matching_reports.append(
                        {
                            "report": report,
                            "analysis": analysis,
                            "starttime": report.get("starttime", 0),
                        }
                    )
                    break

        if not matching_reports:
            raise ValueError(f"Analysis '{analysis_name}' is missing from data")

        # Sort by starttime (latest first)
        matching_reports.sort(key=lambda x: x["starttime"], reverse=True)

        current_data = matching_reports[0]["analysis"]["data"]

        # Create previous data dictionary by looking through all reports
        previous_dict = {}
        if len(matching_reports) > 1:
            # Start from the second report (index 1) and go through all reports
            for report_data in matching_reports[1:]:
                previous_data = report_data["analysis"]["data"]
                # For each player in the current data
                for player in current_data:
                    player_name = player[name_column]
                    # If we haven't found a previous value for this player yet
                    if player_name not in previous_dict:
                        # Look for the player in this report's data
                        matching_player = next(
                            (p for p in previous_data if p[name_column] == player_name),
                            None,
                        )
                        if matching_player and value_column in matching_player:
                            previous_dict[player_name] = matching_player[value_column]

        return current_data, previous_dict

    def get_damage_to_actor(
        self,
        report_code: str,
        fight_ids: set[int],
        target_game_id: int,
        report_players: list[dict[str, Any]],
        filter_expression: Optional[str] = None,
        wipe_cutoff: Optional[int] = DEFAULT_WIPE_CUTOFF,
    ) -> list[dict[str, Any]]:
        """
        Get damage done to a specific actor (e.g., add, boss mechanic) for a single report.

        :param report_code: The WarcraftLogs report code
        :param fight_ids: Set of fight IDs to analyze
        :param target_game_id: The game ID of the target actor (e.g., 231027 for Premium Dynamite Booty)
        :param report_players: List of players who participated in the fights
        :param filter_expression: Optional expression to filter the report data
        :param wipe_cutoff: Stop counting events after this many players have died
        :return: List of player data with damage values
        """
        # Step 1: Get all actors to find target IDs
        actors_query = """
        query GetActors($reportCode: String!) {
          reportData {
            report(code: $reportCode) {
              masterData(translate: true) {
                actors {
                  id
                  name
                  gameID
                  type
                  subType
                }
              }
            }
          }
        }
        """

        actors_variables = {"reportCode": report_code}

        actors_result = self.api_client.make_request(actors_query, actors_variables)
        try:
            if not actors_result or "data" not in actors_result or "reportData" not in actors_result["data"]:
                logger.warning(f"No actors data returned for report {report_code}")
                return []
        except (TypeError, AttributeError):
            # Handle case where actors_result is a Mock object or doesn't support 'in' operator
            logger.warning(f"Invalid actors data returned for report {report_code}")
            return []

        # Find all target IDs matching the game ID
        actors = actors_result["data"]["reportData"]["report"]["masterData"]["actors"]
        target_ids = []
        for actor in actors:
            if actor.get("gameID") == target_game_id:
                target_ids.append(actor["id"])

        if not target_ids:
            logger.warning(f"No targets found with game ID {target_game_id} in report {report_code}")
            return []

        logger.info(f"Found {len(target_ids)} targets with game ID {target_game_id}: {target_ids}")

        # Step 2: Get damage done data for each target and aggregate (viewOption 8192 for unfiltered data)
        damage_query = """
        query GetDamageDone(
            $reportCode: String!, $fightIDs: [Int]!, $targetID: Int!,
            $filterExpression: String, $encounterID: Int!, $difficulty: Int!, $wipeCutoff: Int!
        ) {
          reportData {
            report(code: $reportCode) {
              table(
                dataType: DamageDone
                fightIDs: $fightIDs
                encounterID: $encounterID
                difficulty: $difficulty
                targetID: $targetID
                killType: Wipes
                wipeCutoff: $wipeCutoff
                filterExpression: $filterExpression
                viewOptions: 8192
              )
            }
          }
        }
        """

        # Initialize damage tracking for each player
        damage_totals = defaultdict(int)
        for player in report_players:
            damage_totals[player["name"]] = 0

        # Query damage for each target ID and aggregate
        for target_id in target_ids:
            damage_variables = {
                "reportCode": report_code,
                "fightIDs": list(fight_ids),
                "targetID": target_id,
                "filterExpression": filter_expression,
                "encounterID": self.encounter_id,
                "difficulty": self.difficulty,
                "wipeCutoff": wipe_cutoff,
            }

            damage_result = self.api_client.make_request(damage_query, damage_variables)
            if not damage_result or "data" not in damage_result or "reportData" not in damage_result["data"]:
                logger.warning(f"No damage data returned for target {target_id}")
                continue

            table_data = damage_result["data"]["reportData"]["report"]["table"]
            if not table_data or "data" not in table_data:
                logger.warning(f"No table data found for target {target_id}")
                continue

            if len(table_data["data"]["entries"]) == 0:
                logger.warning(f"No entries found for target {target_id}")
                continue

            # Process damage entries for this target
            entries = table_data["data"].get("entries", [])
            for entry in entries:
                player_name = entry.get("name")
                total_damage = entry.get("total", 0)

                # Find matching player in report_players
                matching_player = next(
                    (player for player in report_players if player["name"] == player_name),
                    None,
                )
                if matching_player:
                    damage_totals[player_name] += total_damage
                else:
                    logger.debug(f"Player {player_name} is missing in report_players")

        # Create a dictionary to store unique player data
        unique_players = {}
        for player in report_players:
            player_name = player["name"]
            if player_name not in unique_players:
                unique_players[player_name] = {
                    "player_name": player_name,
                    "class": player["type"],
                    "role": player["role"],
                    "damage": damage_totals[player_name],
                }
            else:
                # If player exists, update damage if the new total is higher
                if damage_totals[player_name] > unique_players[player_name]["damage"]:
                    unique_players[player_name]["damage"] = damage_totals[player_name]

        # Convert dictionary to list for DataFrame
        return list(unique_players.values())

    def analyze_interrupts(
        self,
        report_code: str,
        fight_ids: set[int],
        report_players: list[dict[str, Any]],
        ability_id: float,
        wipe_cutoff: Optional[int] = DEFAULT_WIPE_CUTOFF,
    ) -> list[dict[str, Any]]:
        """
        Analyze interrupt events for a specific ability.

        :param report_code: The WarcraftLogs report code
        :param fight_ids: Set of fight IDs to analyze
        :param report_players: List of players who participated in the fights
        :param ability_id: The ability ID to track interrupts for
        :param wipe_cutoff: Stop counting events after this many players have died
        :return: List of player data with interrupt counts
        """
        events = []
        next_timestamp = None

        # Get interrupt events
        query = """
        query GetInterrupts(
            $reportCode: String!, $fightIds: [Int!]!, $abilityId: Float!,
            $startTime: Float, $wipeCutoff: Int
        ) {
          reportData {
            report(code: $reportCode) {
              events(
                dataType: Interrupts
                fightIDs: $fightIds
                abilityID: $abilityId
                startTime: $startTime
                killType: Wipes
                wipeCutoff: $wipeCutoff
              ) {
                data
                nextPageTimestamp
              }
            }
          }
        }
        """

        # Keep fetching until no more pages
        while True:
            variables = {
                "reportCode": report_code,
                "fightIds": list(fight_ids),
                "abilityId": float(ability_id),
                "startTime": next_timestamp,  # None for first page, timestamp for subsequent pages
                "wipeCutoff": wipe_cutoff,
            }

            result = self.api_client.make_request(query, variables)
            if not result or "data" not in result or "reportData" not in result["data"]:
                break

            report_data = result["data"]["reportData"]["report"]
            events_data = report_data["events"]

            # Add events from this page to our collection
            if events_data["data"]:
                events.extend(events_data["data"])

            # Check if there are more pages
            next_timestamp = events_data.get("nextPageTimestamp")
            if next_timestamp is None:
                break  # No more pages

        # Initialize interrupt counter for each player
        interrupt_counts = defaultdict(int)
        for player in report_players:
            interrupt_counts[player["name"]] = 0

        # Count interrupts
        for event in events:
            source_id = event.get("sourceID")
            matching_player = next(
                (player for player in report_players if player["id"] == source_id),
                None,
            )

            if matching_player:
                interrupt_counts[matching_player["name"]] += 1
            else:
                logger.debug(f"Source ID {source_id} is missing in report_players")

        # Create a dictionary to store unique player data
        unique_players = {}
        for player in report_players:
            player_name = player["name"]
            if player_name not in unique_players:
                unique_players[player_name] = {
                    "player_name": player_name,
                    "class": player["type"],
                    "role": player["role"],  # Keep the first role encountered
                    "interrupts": interrupt_counts[player_name],
                }
            else:
                # If player exists, update interrupts if the new count is higher
                if interrupt_counts[player_name] > unique_players[player_name]["interrupts"]:
                    unique_players[player_name]["interrupts"] = interrupt_counts[player_name]

        # Convert dictionary to list for DataFrame
        return list(unique_players.values())

    def analyze_debuff_uptime(
        self,
        report_code: str,
        fight_ids: set[int],
        report_players: list[dict[str, Any]],
        ability_id: float,
        wipe_cutoff: Optional[int] = DEFAULT_WIPE_CUTOFF,
        filter_expression: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze debuff uptime for a specific ability.

        :param report_code: The WarcraftLogs report code
        :param fight_ids: Set of fight IDs to analyze
        :param report_players: List of players who participated in the fights
        :param ability_id: The ability ID to track debuff uptime for
        :param wipe_cutoff: Stop counting events after this many players have died
        :param filter_expression: Optional expression to filter the report data
        :return: List of player data with debuff uptime percentages
        """
        # Get debuff uptime data
        query = """
        query DebuffUptime(
            $reportCode: String!, $fightIDs: [Int]!, $abilityID: Float!,
            $filterExpression: String, $encounterID: Int!, $difficulty: Int!, $wipeCutoff: Int!
        ) {
          reportData {
            report(code: $reportCode) {
              table(
                dataType: Debuffs
                fightIDs: $fightIDs
                encounterID: $encounterID
                difficulty: $difficulty
                abilityID: $abilityID
                killType: Wipes
                wipeCutoff: $wipeCutoff
                filterExpression: $filterExpression
              )
            }
          }
        }
        """

        variables = {
            "reportCode": report_code,
            "fightIDs": list(fight_ids),
            "abilityID": float(ability_id),
            "filterExpression": filter_expression,
            "encounterID": self.encounter_id,
            "difficulty": self.difficulty,
            "wipeCutoff": wipe_cutoff,
        }

        result = self.api_client.make_request(query, variables)
        if not result or "data" not in result or "reportData" not in result["data"]:
            logger.warning("No data returned for debuff uptime query")
            return []

        table_data = result["data"]["reportData"]["report"]["table"]
        if not table_data or "data" not in table_data:
            logger.warning("No table data found for debuff uptime")
            return []

        # Get total time from the response
        data = table_data["data"]
        total_time = data.get("totalTime", 0)  # Total time in milliseconds

        if not total_time:
            logger.warning("Could not get total time from debuff query response")
            return []

        # Initialize uptime tracking for each player
        uptime_data = defaultdict(lambda: {"total_uptime": 0, "uptime_percentage": 0.0})
        for player in report_players:
            uptime_data[player["name"]] = {
                "total_uptime": 0,
                "uptime_percentage": 0.0,
            }

        # Process auras data (debuff entries)
        auras = data.get("auras", [])
        for aura in auras:
            actor_name = aura.get("name")
            total_uptime_ms = aura.get("totalUptime", 0)  # Uptime in milliseconds

            # Find matching player
            matching_player = next(
                (player for player in report_players if player["name"] == actor_name),
                None,
            )
            if matching_player:
                uptime_percentage = (total_uptime_ms / total_time) * 100 if total_time > 0 else 0
                uptime_data[actor_name] = {
                    "total_uptime": total_uptime_ms,
                    "uptime_percentage": uptime_percentage,
                }
            else:
                logger.debug(f"Player {actor_name} is missing in report_players")

        # Create a dictionary to store unique player data
        unique_players = {}
        for player in report_players:
            player_name = player["name"]
            player_uptime = uptime_data[player_name]
            if player_name not in unique_players:
                unique_players[player_name] = {
                    "player_name": player_name,
                    "class": player["type"],
                    "role": player["role"],  # Keep the first role encountered
                    "uptime_percentage": round(player_uptime["uptime_percentage"], 2),
                }
            else:
                # If player exists, update uptime if the new percentage is higher
                if player_uptime["uptime_percentage"] > unique_players[player_name]["uptime_percentage"]:
                    unique_players[player_name]["uptime_percentage"] = round(player_uptime["uptime_percentage"], 2)

        # Convert dictionary to list for DataFrame
        return list(unique_players.values())

    def _calculate_debuff_uptime(
        self,
        events: list[dict[str, Any]],
        player_name: str,
        total_duration_ms: int,
    ) -> float:
        """
        Calculate debuff uptime percentage for a specific player.

        :param events: List of debuff events
        :param player_name: Name of the player to calculate uptime for
        :param total_duration_ms: Total fight duration in milliseconds
        :return: Uptime percentage
        """
        if not events or total_duration_ms <= 0:
            return 0.0

        # Track debuff periods for this player
        uptime_periods = []
        current_start = None

        for event in events:
            if event.get("targetName") != player_name:
                continue

            event_type = event.get("type")
            timestamp = event.get("timestamp", 0)

            if event_type == "applydebuff":
                if current_start is None:
                    current_start = timestamp
            elif event_type == "removedebuff":
                if current_start is not None:
                    uptime_periods.append((current_start, timestamp))
                    current_start = None

        # If debuff was still active at the end, add the final period
        if current_start is not None:
            uptime_periods.append((current_start, total_duration_ms))

        # Calculate total uptime
        total_uptime_ms = sum(end - start for start, end in uptime_periods)
        uptime_percentage = (total_uptime_ms / total_duration_ms) * 100

        return round(uptime_percentage, 2)

    def analyze_damage_taken_from_ability(
        self,
        report_code: str,
        fight_ids: set[int],
        report_players: list[dict[str, Any]],
        ability_id: float,
        wipe_cutoff: Optional[int] = DEFAULT_WIPE_CUTOFF,
        filter_expression: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze damage taken from a specific ability.

        :param report_code: The WarcraftLogs report code
        :param fight_ids: Set of fight IDs to analyze
        :param report_players: List of players who participated in the fights
        :param ability_id: The ability ID to track damage taken from (float)
        :param wipe_cutoff: Stop counting events after this many players have died
        :param filter_expression: Optional expression to filter the report data
        :return: List of player data with damage taken amounts
        """
        query = """
        query GetDamageTakenByAbility(
            $reportCode: String!, $fightIDs: [Int]!, $abilityID: Float!,
            $filterExpression: String, $encounterID: Int!, $difficulty: Int!, $wipeCutoff: Int!
        ) {
          reportData {
            report(code: $reportCode) {
              table(
                dataType: DamageTaken
                fightIDs: $fightIDs
                encounterID: $encounterID
                difficulty: $difficulty
                abilityID: $abilityID
                killType: Wipes
                wipeCutoff: $wipeCutoff
                filterExpression: $filterExpression
              )
            }
          }
        }
        """

        variables = {
            "reportCode": report_code,
            "fightIDs": list(fight_ids),
            "abilityID": float(ability_id),
            "filterExpression": filter_expression,
            "encounterID": self.encounter_id,
            "difficulty": self.difficulty,
            "wipeCutoff": wipe_cutoff,
        }

        response = self.api_client.make_request(query, variables)

        if not response or "data" not in response or "reportData" not in response["data"]:
            logger.warning(f"No damage taken data found for ability {ability_id} in report {report_code}")
            return []

        report_data = response["data"]["reportData"]["report"]
        if not report_data:
            logger.warning(f"No report found for code {report_code}")
            return []

        table_data = report_data["table"]
        if not table_data or "data" not in table_data:
            logger.warning(f"No damage taken table data for ability {ability_id} in report {report_code}")
            return []

        entries = table_data["data"]["entries"]
        if not entries:
            logger.info(f"No damage taken entries found for ability {ability_id} in report {report_code}")
            # Return all players with 0 damage taken and hit count instead of empty list
            return [
                {
                    "player_name": player["name"],
                    "class": player["type"],
                    "role": player["role"],
                    "damage_taken": 0,
                    "hit_count": 0,
                }
                for player in report_players
            ]

        # Process damage taken data
        damage_data = {}
        for entry in entries:
            actor_name = entry.get("name")
            total_damage = entry.get("total", 0)
            hit_count = entry.get("hitCount", 0)

            # Find matching player
            matching_player = next(
                (player for player in report_players if player["name"] == actor_name),
                None,
            )
            if matching_player:
                damage_data[actor_name] = {
                    "damage_taken": total_damage,
                    "hit_count": hit_count,
                }
            else:
                logger.debug(f"Player {actor_name} is missing in report_players")

        # Create a dictionary to store unique player data
        unique_players = {}
        for player in report_players:
            player_name = player["name"]
            player_damage = damage_data.get(player_name, {"damage_taken": 0, "hit_count": 0})
            if player_name not in unique_players:
                unique_players[player_name] = {
                    "player_name": player_name,
                    "class": player["type"],
                    "role": player["role"],
                    "damage_taken": player_damage["damage_taken"],
                    "hit_count": player_damage["hit_count"],
                }
            else:
                # If player exists, keep the higher values (should be the same from API)
                if player_damage["damage_taken"] > unique_players[player_name]["damage_taken"]:
                    unique_players[player_name]["damage_taken"] = player_damage["damage_taken"]
                if player_damage["hit_count"] > unique_players[player_name]["hit_count"]:
                    unique_players[player_name]["hit_count"] = player_damage["hit_count"]

        # Convert dictionary to list
        return list(unique_players.values())

    def analyze_player_deaths(
        self,
        report_code: str,
        fight_ids: set[int],
        report_players: list[dict[str, Any]],
        wipe_cutoff: Optional[int] = DEFAULT_WIPE_CUTOFF,
        filter_expression: Optional[str] = None,
        ability_id: Optional[float] = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze player deaths using table data for efficient querying.

        :param report_code: The WarcraftLogs report code
        :param fight_ids: Set of fight IDs to analyze
        :param report_players: List of players who participated in the fights
        :param wipe_cutoff: Stop counting events after this many players have died
        :param filter_expression: Optional expression to filter death events (deprecated, use ability_id instead)
        :param ability_id: Optional ability ID to filter deaths by specific ability (e.g., 1216415 for Blazing Beam)
        :return: List of player data with death counts
        """
        # Get deaths table data
        query = """
        query GetDeathsTable(
            $reportCode: String!, $fightIDs: [Int], $encounterID: Int!, $difficulty: Int!,
            $wipeCutoff: Int, $abilityID: Float
        ) {
          reportData {
            report(code: $reportCode) {
              table(
                dataType: Deaths
                fightIDs: $fightIDs
                encounterID: $encounterID
                difficulty: $difficulty
                abilityID: $abilityID
                wipeCutoff: $wipeCutoff
              )
            }
          }
        }
        """

        variables = {
            "reportCode": report_code,
            "fightIDs": list(fight_ids),
            "encounterID": self.encounter_id,
            "difficulty": self.difficulty,
            "wipeCutoff": wipe_cutoff,
            "abilityID": ability_id,
        }

        result = self.api_client.make_request(query, variables)
        if not result or "data" not in result or "reportData" not in result["data"]:
            logger.warning(f"No deaths data returned for report {report_code}")
            return []

        table_data = result["data"]["reportData"]["report"]["table"]
        if not table_data or "data" not in table_data:
            logger.warning(f"No deaths table data found for report {report_code}")
            return []

        entries = table_data["data"].get("entries", [])
        if not entries:
            logger.info(f"No death entries found in report {report_code}")
            # Return all players with 0 deaths instead of empty list
            return [
                {
                    "player_name": player["name"],
                    "class": player["type"],
                    "role": player["role"],
                    "deaths": 0,
                }
                for player in report_players
            ]

        # Initialize death counter for each player
        death_counts = defaultdict(int)
        for player in report_players:
            death_counts[player["name"]] = 0

        # Count deaths from table entries
        for entry in entries:
            player_name = entry.get("name")
            # Each entry represents one death for that player
            death_count = 1

            # Find matching player in report_players
            matching_player = next(
                (player for player in report_players if player["name"] == player_name),
                None,
            )
            if matching_player:
                death_counts[player_name] += death_count
            else:
                logger.debug(f"Player {player_name} is missing in report_players")

        # Create a dictionary to store unique player data
        unique_players = {}
        for player in report_players:
            player_name = player["name"]
            if player_name not in unique_players:
                unique_players[player_name] = {
                    "player_name": player_name,
                    "class": player["type"],
                    "role": player["role"],
                    "deaths": death_counts[player_name],
                }
            else:
                # If player exists, update deaths if the new count is higher
                if death_counts[player_name] > unique_players[player_name]["deaths"]:
                    unique_players[player_name]["deaths"] = death_counts[player_name]

        # Convert dictionary to list for DataFrame
        return list(unique_players.values())

    def analyze_table_data(
        self,
        report_code: str,
        config: dict[str, Any],
        fight_ids: Optional[set[int]] = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze data using the table query for flexible data retrieval.

        :param report_code: The WarcraftLogs report code
        :param config: Configuration dictionary containing table query parameters
        :return: List of player data processed from table response
        """
        # Get table data using the new method
        table_data = self.get_table_data(
            report_code=report_code,
            encounter_id=config.get("encounter_id", self.encounter_id),
            difficulty=config.get("difficulty", self.difficulty),
            ability_id=config["ability_id"],
            data_type=config.get("data_type", "Debuffs"),
            kill_type=config.get("kill_type", "Wipes"),
            fight_ids=fight_ids,
            wipe_cutoff=config.get("wipe_cutoff", DEFAULT_WIPE_CUTOFF),
        )

        if not table_data:
            logger.warning(f"No table data returned for report {report_code}")
            return []

        # Parse the table data and convert to player list format
        # The table data structure varies by data_type, so we need to handle it generically
        try:
            # Table data is typically JSON with player entries
            import json

            if isinstance(table_data, str):
                parsed_data = json.loads(table_data)
            else:
                parsed_data = table_data

            # Extract player data from table structure
            player_data = []

            # Handle WarcraftLogs table data format
            if isinstance(parsed_data, dict) and "data" in parsed_data:
                # Check for specific data types
                if config.get("data_type") == "Debuffs" and "auras" in parsed_data["data"]:
                    entries = parsed_data["data"]["auras"]
                elif config.get("data_type") == "DamageTaken" and "entries" in parsed_data["data"]:
                    entries = parsed_data["data"]["entries"]
                else:
                    entries = parsed_data["data"]
            elif isinstance(parsed_data, list):
                entries = parsed_data
            else:
                logger.warning(f"Unexpected table data format for report {report_code}")
                return []

            # Process each entry in the table
            for entry in entries:
                if isinstance(entry, dict) and "name" in entry:
                    player_entry = {
                        "player_name": entry["name"],
                        "class": entry.get("type", "Unknown"),
                        "role": entry.get("role", "Unknown"),
                    }

                    # Add metrics based on data type
                    if config.get("data_type") == "Debuffs":
                        # For debuffs, extract uptime and hit count from WarcraftLogs format
                        player_entry["uptime_percentage"] = round(
                            (entry.get("totalUptime", 0) / parsed_data["data"].get("totalTime", 1)) * 100, 2
                        )
                        player_entry["hit_count"] = entry.get("totalUses", 0)
                    elif config.get("data_type") == "DamageTaken":
                        # For damage taken, extract damage and available fields
                        player_entry["damage_taken"] = entry.get("total", 0)
                        player_entry["total_reduced"] = entry.get("totalReduced", 0)
                        player_entry["overheal"] = entry.get("overheal", 0)
                        # Extract any hit-related fields that might be available
                        player_entry["hit_count"] = entry.get(
                            "hitCount",
                            entry.get("tickCount", 1 if entry.get("total", 0) > 0 else 0),
                        )
                        # Debug: log available fields for the first entry
                        if config.get("debug_fields"):
                            logger.info(
                                f"DEBUG DamageTaken fields for " f"{entry.get('name', 'Unknown')}: {list(entry.keys())}"
                            )
                    else:
                        # For other data types, add all numeric fields
                        for key, value in entry.items():
                            if isinstance(value, (int, float)) and key not in ["id", "type"]:
                                player_entry[key] = value

                    player_data.append(player_entry)

            logger.info(f"Processed {len(player_data)} players from table data for report {report_code}")
            return player_data

        except Exception as e:
            logger.error(f"Error parsing table data for report {report_code}: {e}")
            return []

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

    def generate_plots(self, include_progress_plots: bool = True) -> None:
        """
        Generate plots using configuration.

        :param include_progress_plots: Whether to generate progress plots (default: True)
        """
        if self.CONFIG:
            self._generate_plots_generic()
            if include_progress_plots:
                self._generate_progress_plots()
        else:
            self._generate_plots_legacy()

    def _generate_plots_legacy(self) -> None:
        """
        Legacy plot generation method for backwards compatibility.

        Override this in subclasses that don't use configuration.
        """
        raise NotImplementedError("Either implement CONFIG or override _generate_plots_legacy")

    def _generate_plots_generic(self) -> None:
        """Generate plots using configuration."""
        logger.info(f"Generating plots for {self.boss_name} analysis")

        if not self.results:
            logger.warning("No reports available to generate plots")
            return

        # Sort reports by starttime (newest first)
        sorted_reports = sorted(self.results, key=lambda x: x["starttime"], reverse=True)
        latest_report = sorted_reports[0]

        report_date = datetime.fromtimestamp(latest_report["starttime"]).strftime("%d.%m.%Y")

        # Get fight durations for current and previous reports
        current_fight_duration = latest_report.get("total_duration")

        previous_fight_duration = None
        if len(sorted_reports) > 1:
            previous_fight_duration = sorted_reports[1].get("total_duration")

        # Generate plots based on configuration
        for config in self.CONFIG:
            try:
                # Extract plot config from unified CONFIG
                plot_config = {
                    "analysis_name": config["name"],
                    "title": config["plot"].get("title", config["name"]),
                    **{k: v for k, v in config["plot"].items() if k != "title"},
                }
                if "roles" in config:
                    plot_config["roles"] = config["roles"]

                self._generate_single_plot(
                    plot_config,
                    report_date,
                    current_fight_duration,
                    previous_fight_duration,
                )
            except Exception as e:
                title = config.get("title") or config.get("name", "Unknown")
                logger.error(f"Error generating plot {title}: {e}")
                continue

    def _generate_single_plot(
        self,
        plot_config: dict[str, Any],
        report_date: str,
        current_fight_duration: Optional[int],
        previous_fight_duration: Optional[int],
    ) -> None:
        """
        Generate a single plot based on configuration.

        :param plot_config: Plot configuration dictionary
        :param report_date: Date string for the report
        :param current_fight_duration: Total duration of current fights in milliseconds
        :param previous_fight_duration: Total duration of previous fights in milliseconds
        """
        analysis_name = plot_config["analysis_name"]
        plot_type = plot_config["type"]
        title = plot_config["title"]

        # Column configuration with support for up to 5 columns
        column_key_1 = plot_config["column_key_1"]
        column_header_1 = plot_config.get("column_header_1", "")
        column_key_2 = plot_config.get("column_key_2")
        column_header_2 = plot_config.get("column_header_2", "")
        column_key_3 = plot_config.get("column_key_3")
        column_header_3 = plot_config.get("column_header_3", "")
        column_header_4 = plot_config.get("column_header_4", "")
        column_header_5 = plot_config.get("column_header_5", "")

        name_column = plot_config.get("name_column", "player_name")
        class_column = plot_config.get("class_column", "class")

        # Get analysis data
        current_data, previous_dict = self.find_analysis_data(analysis_name, column_key_1, name_column)

        # Apply role filtering to plot data if specified
        plot_roles = plot_config.get("roles", [])
        if plot_roles:
            current_data = self._filter_players_by_roles(current_data, plot_roles)
            # Filter previous data dictionary to only include players from allowed roles
            filtered_previous_dict = {}
            for player_data in current_data:
                player_name = player_data.get(name_column)
                if player_name and player_name in previous_dict:
                    filtered_previous_dict[player_name] = previous_dict[player_name]
            previous_dict = filtered_previous_dict

        df = pd.DataFrame(current_data)

        # Create appropriate plot type
        if plot_type == "NumberPlot":
            plot = NumberPlot(
                title=title,
                date=report_date,
                df=df,
                previous_data=previous_dict,
                column_key_1=column_key_1,
                column_header_1=column_header_1,
                column_key_2=column_key_2,
                column_header_2=column_header_2,
                column_key_3=column_key_3,
                column_header_3=column_header_3,
                column_header_4=column_header_4,
                column_header_5=column_header_5,
                name_column=name_column,
                class_column=class_column,
                current_fight_duration=current_fight_duration,
                previous_fight_duration=previous_fight_duration,
            )
        elif plot_type == "PercentagePlot":
            plot = PercentagePlot(
                title=title,
                date=report_date,
                df=df,
                previous_data=previous_dict,
                column_key_1=column_key_1,
                column_header_1=column_header_1,
                column_key_2=column_key_2,
                column_header_2=column_header_2,
                column_key_3=column_key_3,
                column_header_3=column_header_3,
                column_header_4=column_header_4,
                column_header_5=column_header_5,
                name_column=name_column,
                class_column=class_column,
                current_fight_duration=current_fight_duration,
                previous_fight_duration=previous_fight_duration,
            )
        elif plot_type == "HitCountPlot":
            plot = HitCountPlot(
                title=title,
                date=report_date,
                df=df,
                previous_data=previous_dict,
                column_key_1=column_key_1,
                column_header_1=column_header_1,
                column_key_2=column_key_2,
                column_header_2=column_header_2,
                column_key_3=column_key_3,
                column_header_3=column_header_3,
                column_header_4=column_header_4,
                column_header_5=column_header_5,
                name_column=name_column,
                class_column=class_column,
                current_fight_duration=current_fight_duration,
                previous_fight_duration=previous_fight_duration,
            )
        else:
            raise ValueError(f"Unknown plot type: {plot_type}")

        plot.save()
        logger.debug(f"Generated {plot_type} for {title}")

    def _generate_progress_plots(self) -> None:
        """Generate multi-line progress plots for all enabled configurations."""
        logger.info(f"Generating multi-line plots for {self.boss_name} analysis")

        if not self.results:
            logger.warning("No reports available to generate multi-line plots")
            return

        # Generate multi-line plots for each configuration that has it enabled
        for config in self.CONFIG:
            multi_line_config = config.get("progress_plot")
            if not multi_line_config or not multi_line_config.get("enabled", False):
                continue

            try:
                self._generate_progress_plot(config["name"], multi_line_config, config.get("roles", []))
            except Exception as e:
                logger.error(f"Error generating multi-line plot for {config['name']}: {e}")
                continue

    def _generate_progress_plot(self, metric_name: str, multi_line_config: dict, roles: list = None) -> None:
        """
        Generate a multi-line progress plot for a specific metric.

        :param metric_name: Name of the metric to plot
        :param multi_line_config: Multi-line plot configuration
        :param roles: Optional role filtering for the metric
        """
        # Extract data from analysis results organized by date
        date_data = {}
        all_player_roles = {}

        # Get column key and y-axis label early
        column_key = multi_line_config["column_key"]
        y_axis_label = multi_line_config["y_axis_label"]

        for result in self.results:
            # Convert timestamp to formatted date string
            timestamp = result["starttime"]
            date = datetime.fromtimestamp(timestamp).strftime("%d.%m.%Y")

            # Get player role information for this report
            report_code = result.get("reportCode")
            fight_ids = set(result.get("fight_ids", []))

            if report_code and fight_ids:
                player_roles = self._get_player_details(report_code, fight_ids)
                all_player_roles.update(player_roles)
                logger.debug(f"Found {len(player_roles)} players with roles in report {report_code}")

            # Find results for this specific metric
            for analysis_item in result["analysis"]:
                if analysis_item["name"] == metric_name:
                    # Convert analysis data to DataFrame
                    df = pd.DataFrame(analysis_item["data"])

                    # Apply role filtering if specified
                    if roles:
                        df = pd.DataFrame(self._filter_players_by_roles(df.to_dict("records"), roles))

                    # Apply duration normalization if configured
                    if multi_line_config.get("normalize_by_duration", True):
                        df = self._normalize_data_by_duration(df, column_key, result.get("total_duration"))

                    date_data[date] = df
                    break

        if not date_data:
            logger.warning(f"No data found for metric '{metric_name}'")
            return

        # Check if role categories are specified for separate plots
        role_categories = multi_line_config.get("role_categories")
        if role_categories:
            self._generate_role_categorized_plots(
                metric_name,
                date_data,
                all_player_roles,
                column_key,
                y_axis_label,
                role_categories,
            )
        else:
            # Generate single multi-line plot
            plot_title = f"{metric_name} Progress Over Time"
            self._create_and_save_progress_plot(plot_title, date_data, column_key, y_axis_label)

    def _generate_role_categorized_plots(
        self,
        metric_name: str,
        date_data: dict,
        all_player_roles: dict,
        column_key: str,
        y_axis_label: str,
        role_categories: dict,
    ) -> None:
        """Generate separate multi-line plots for different role categories."""
        # Group data by role categories
        role_data = {category: {} for category in role_categories.keys()}

        for date, df in date_data.items():
            for category in role_data.keys():
                role_data[category][date] = pd.DataFrame()

            # Categorize players by role using API data
            for _, row in df.iterrows():
                player_name = row.get("player_name", "Unknown")
                category = self._get_player_role_category(player_name, all_player_roles)
                logger.debug(f"Player {player_name} categorized as {category}")

                # Add player to appropriate category
                if category in role_data:
                    if role_data[category][date].empty:
                        role_data[category][date] = pd.DataFrame([row])
                    else:
                        role_data[category][date] = pd.concat(
                            [role_data[category][date], pd.DataFrame([row])],
                            ignore_index=True,
                        )

        # Generate plots for each category that has data
        for category, category_data in role_data.items():
            # Check if this category has any data across all dates
            has_data = any(not df.empty for df in category_data.values())

            if has_data:
                # Filter out empty DataFrames from the category data
                filtered_data = {date: df for date, df in category_data.items() if not df.empty}

                if filtered_data:
                    plot_title = f"{metric_name} Progress - {role_categories[category]}"
                    self._create_and_save_progress_plot(plot_title, filtered_data, column_key, y_axis_label)
                else:
                    logger.debug(f"No data for category {category} after filtering empty DataFrames")
            else:
                logger.debug(f"No data for category {category}")

    def _create_and_save_progress_plot(
        self, plot_title: str, date_data: dict, column_key: str, y_axis_label: str
    ) -> str:
        """Create and save a multi-line plot."""
        # Get ignored players from settings
        from ..config.settings import Settings

        settings = Settings()
        ignored_players = settings.ignored_players

        progress_plot = MultiLinePlot(
            title=plot_title,
            data=date_data,
            column_key=column_key,
            y_axis_label=y_axis_label,
            ignored_players=ignored_players,
        )

        # Save the plot
        filename = progress_plot.save()
        logger.info(f"Multi-line progress plot saved to: {filename}")
        return filename

    def get_table_data(
        self,
        report_code: str,
        encounter_id: int,
        difficulty: int,
        ability_id: int,
        data_type: str = "Debuffs",
        kill_type: str = "Wipes",
        fight_ids: Optional[set[int]] = None,
        wipe_cutoff: Optional[int] = None,
    ) -> Optional[dict[str, Any]]:
        """
        Get table data from WarcraftLogs API using the table query.

        :param report_code: The WarcraftLogs report code
        :param encounter_id: The encounter ID to query
        :param difficulty: The difficulty level (e.g., 5 for Mythic)
        :param ability_id: The ability ID to query
        :param data_type: The type of data to query (default: "Debuffs")
        :param kill_type: The kill type to query (default: "Wipes")
        :param fight_ids: Optional set of fight IDs to filter
        :param wipe_cutoff: Optional number of deaths before stopping event counting
        :return: Table data response or None if error
        """
        query = """
        query GetTableData(
            $reportCode: String!, $encounterID: Int!, $difficulty: Int!,
            $abilityID: Float!, $dataType: TableDataType!, $killType: KillType!, $fightIDs: [Int], $wipeCutoff: Int
        ) {
          reportData {
            report(code: $reportCode) {
              table(
                encounterID: $encounterID,
                difficulty: $difficulty,
                abilityID: $abilityID,
                dataType: $dataType,
                killType: $killType,
                fightIDs: $fightIDs,
                wipeCutoff: $wipeCutoff
              )
            }
          }
        }
        """

        variables = {
            "reportCode": report_code,
            "encounterID": encounter_id,
            "difficulty": difficulty,
            "abilityID": ability_id,
            "dataType": data_type,
            "killType": kill_type,
            "fightIDs": list(fight_ids) if fight_ids else None,
            "wipeCutoff": wipe_cutoff,
        }

        try:
            result = self.api_client.make_request(query, variables)
            if not result or "data" not in result:
                logger.warning(f"No table data returned for report {report_code}")
                return None

            table_data = result["data"]["reportData"]["report"]["table"]
            logger.info(f"Retrieved table data for ability {ability_id} in report {report_code}")
            return table_data

        except Exception as e:
            logger.error(f"Error getting table data for report {report_code}: {e}")
            return None

    def _get_player_details(self, report_code: str, fight_ids: set[int]) -> dict[str, str]:
        """
        Get player role details from WarcraftLogs API.

        :param report_code: The WarcraftLogs report code
        :param fight_ids: Set of fight IDs to get player details for
        :returns: Dictionary mapping player names to their roles
        """
        query = """
        query GetPlayerDetails($reportCode: String!, $fightIDs: [Int]!) {
          reportData {
            report(code: $reportCode) {
              playerDetails(fightIDs: $fightIDs, includeCombatantInfo: true)
            }
          }
        }
        """

        variables = {"reportCode": report_code, "fightIDs": list(fight_ids)}

        result = self.api_client.make_request(query, variables)
        if not result or "data" not in result or "reportData" not in result["data"]:
            logger.warning(f"No player details data returned for report {report_code}")
            return {}

        player_details = result["data"]["reportData"]["report"]["playerDetails"]
        if not player_details or "data" not in player_details:
            logger.warning(f"No player details found for report {report_code}")
            return {}

        # Extract role information from player details
        player_roles = {}
        details_data = player_details["data"]["playerDetails"]

        # Process each role category
        for role_category in ["dps", "healers", "tanks"]:
            if role_category in details_data:
                for player in details_data[role_category]:
                    player_name = player.get("name")
                    if player_name:
                        if role_category in ["healers", "tanks"]:
                            player_roles[player_name] = "tanks_healers"
                        else:
                            player_roles[player_name] = "dps"

        return player_roles

    def _get_player_role_category(self, player_name: str, player_roles: dict[str, str]) -> str:
        """
        Get role category for a player based on API data.

        :param player_name: Player name
        :param player_roles: Dictionary mapping player names to roles
        :returns: Role category (tanks_healers, melee_dps, or ranged_dps)
        """
        # Get melee DPS players from settings
        from ..config.settings import Settings

        settings = Settings()
        melee_dps_players = settings.melee_dps_players

        # Get base role from API data
        base_role = player_roles.get(player_name, "dps")

        # If player is DPS, further categorize as melee or ranged
        if base_role == "dps":
            if player_name in melee_dps_players:
                return "melee_dps"
            else:
                return "ranged_dps"
        else:
            # Keep tanks and healers as they are
            return base_role

    def _normalize_data_by_duration(
        self, df: pd.DataFrame, column_key: str, total_duration_ms: Optional[int]
    ) -> pd.DataFrame:
        """
        Normalize data by fight duration to make it comparable across reports.

        :param df: DataFrame containing the data
        :param column_key: Column to normalize
        :param total_duration_ms: Total fight duration in milliseconds
        :return: DataFrame with normalized data
        """
        if total_duration_ms is None or total_duration_ms <= 0:
            logger.warning("Cannot normalize data: invalid or missing fight duration")
            return df

        # Create a copy to avoid modifying original data
        df_normalized = df.copy()

        if column_key not in df_normalized.columns:
            logger.warning(f"Column '{column_key}' not found in data, skipping normalization")
            return df

        # Convert duration to hours for normalization (more appropriate for 3-hour raid sessions)
        duration_hours = total_duration_ms / (1000 * 60 * 60)

        # Determine normalization approach based on metric type
        if column_key in ["interrupts", "hit_count"]:
            # For count-based metrics, normalize to "per hour"
            df_normalized[column_key] = df_normalized[column_key] / duration_hours
            df_normalized[f"{column_key}_original"] = df[column_key]  # Keep original for reference
        elif column_key in [
            "damage_to_small_packages",
            "damage_to_reel_assistants",
            "damage_to_boss",
            "absorbed_damage_to_reel_assistants",
            "hits_by_travelling_flames",
            "damage_taken_from_falling_coins",
        ]:
            # For damage-based metrics, normalize to "per hour"
            df_normalized[column_key] = df_normalized[column_key] / duration_hours
            df_normalized[f"{column_key}_original"] = df[column_key]  # Keep original for reference
        elif column_key == "uptime_percentage":
            # Percentage metrics don't need duration normalization as they're already relative
            pass
        else:
            # For unknown metrics, apply general per-hour normalization
            logger.debug(f"Applying general normalization to metric '{column_key}'")
            df_normalized[column_key] = df_normalized[column_key] / duration_hours
            df_normalized[f"{column_key}_original"] = df[column_key]  # Keep original for reference

        return df_normalized
