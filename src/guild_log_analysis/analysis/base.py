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
from ..utils.helpers import filter_players_by_roles

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
        self, config: dict[str, Any], report_code: str, fight_ids: set[int], report_players: list[dict[str, Any]]
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

        logger.info(f"Found a total of {len(players)} players.")

        return players if players else None

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
                        if matching_player:
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

    def generate_plots(self) -> None:
        """Generate plots using configuration."""
        if self.CONFIG:
            self._generate_plots_generic()
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

                self._generate_single_plot(plot_config, report_date, current_fight_duration, previous_fight_duration)
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
