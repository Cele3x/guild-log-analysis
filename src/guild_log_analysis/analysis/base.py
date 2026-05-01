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
from ..config.constants import DEFAULT_WIPE_CUTOFF, PlotColors
from ..plotting.base import HitCountPlot, NumberPlot, PercentagePlot, SurvivabilityPlot
from ..plotting.multi_line import MultiLinePlot
from ..plotting.player_deaths import PlayerDeathsPlot
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

                data = self._execute_analysis(report_code, analysis_config, fight_ids, report_players)
                report_results["analysis"].append({"name": analysis_config["name"], "data": data})
            except Exception as e:
                logger.error(f"Error executing analysis {config['name']}: {e}")
                continue

        self.results.append(report_results)
        logger.info(f"Successfully processed report {report_code} with {len(report_results['analysis'])} analyses")

    def _execute_analysis(
        self,
        report_code: str,
        config: dict[str, Any],
        fight_ids: set[int],
        report_players: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Execute a single analysis based on configuration.

        :param report_code: The WarcraftLogs report code
        :param config: Analysis configuration dictionary
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
        elif analysis_type == "table_data":
            data = self.analyze_table_data(
                report_code=report_code,
                config=config,
                fight_ids=fight_ids,
                report_players=filtered_players,
            )
        elif analysis_type == "player_deaths":
            data = self.analyze_player_deaths(
                report_code=report_code,
                config=config,
                fight_ids=fight_ids,
                report_players=filtered_players,
            )
        elif analysis_type == "events":
            data = self.analyze_events(
                report_code=report_code,
                config=config,
                fight_ids=fight_ids,
                report_players=filtered_players,
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
                # Extract most-played spec. WCL returns specs either as a list
                # of strings or a list of objects with a "spec" key.
                specs_field = player.get("specs") or []
                spec_name: Optional[str] = None
                if specs_field:
                    first = specs_field[0]
                    if isinstance(first, dict):
                        spec_name = first.get("spec")
                    else:
                        spec_name = first
                player_info = {
                    "id": player["id"],
                    "name": player["name"],
                    "type": player["type"].lower(),
                    "role": role_name,
                    "spec": spec_name,
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
        seen = set()
        deduplicated_players = []
        for player in players:
            if "name" in player:
                player_name = player["name"]
                if player_name not in seen:
                    seen.add(player_name)
                    deduplicated_players.append(player)

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

    def analyze_table_data(
        self,
        report_code: str,
        config: dict[str, Any],
        fight_ids: Optional[set[int]] = None,
        report_players: Optional[list[dict[str, Any]]] = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze data using the table query for flexible data retrieval.

        :param report_code: The WarcraftLogs report code
        :param config: Configuration dictionary containing table query parameters
        :param fight_ids: Optional set of fight IDs to filter
        :param report_players: List of players who participated in the fights
        :return: List of player data processed from table response
        """
        # For Deaths data type, use events query instead of table query
        if config.get("data_type") == "Deaths":
            return self.analyze_deaths_events(
                report_code=report_code,
                config=config,
                fight_ids=fight_ids,
                report_players=report_players,
            )

        ability_ids = config.get("ability_ids")
        if not ability_ids:
            ability_ids = [config.get("ability_id")]

        if not report_players:
            logger.warning("No report players provided for table data analysis")
            return []

        # Create lookup dictionary for aggregated table data metrics by player name
        aggregated_metrics = defaultdict(lambda: defaultdict(float))
        
        # Track which players have any data
        players_with_data = set()

        for ability_id in ability_ids:
            # Get table data using the new method
            table_data = self.get_table_data(
                report_code=report_code,
                encounter_id=config.get("encounter_id", self.encounter_id),
                difficulty=config.get("difficulty", self.difficulty),
                ability_id=ability_id,
                data_type=config.get("data_type", "Debuffs"),
                kill_type=config.get("kill_type", "Wipes"),
                fight_ids=fight_ids,
                wipe_cutoff=config.get("wipe_cutoff", DEFAULT_WIPE_CUTOFF),
            )

            if not table_data:
                logger.warning(f"No table data returned for ability {ability_id} in report {report_code}")
                continue

            # Parse the table data to extract metrics by player name
            try:
                # Table data is typically JSON with player entries
                import json

                if isinstance(table_data, str):
                    parsed_data = json.loads(table_data)
                else:
                    parsed_data = table_data

                # Handle WarcraftLogs table data format
                if isinstance(parsed_data, dict) and "data" in parsed_data:
                    # Check for specific data types and extract entries
                    if config.get("data_type") == "Debuffs" and "auras" in parsed_data["data"]:
                        entries = parsed_data["data"]["auras"]
                    elif config.get("data_type") == "DamageTaken" and "entries" in parsed_data["data"]:
                        entries = parsed_data["data"]["entries"]
                    elif config.get("data_type") == "Survivability" and "players" in parsed_data["data"]:
                        entries = parsed_data["data"]["players"]
                    else:
                        entries = parsed_data["data"]

                    # Process entries from table data
                    for entry in entries:
                        if isinstance(entry, dict) and "name" in entry:
                            player_name = entry["name"]
                            players_with_data.add(player_name)

                            # Extract metrics based on data type
                            if config.get("data_type") == "Debuffs":
                                uptime = (entry.get("totalUptime", 0) / parsed_data["data"].get("totalTime", 1)) * 100
                                aggregated_metrics[player_name]["uptime_percentage"] += uptime
                                aggregated_metrics[player_name]["hit_count"] += entry.get("totalUses", 0)
                            elif config.get("data_type") == "DamageTaken":
                                aggregated_metrics[player_name]["damage_taken"] += entry.get("total", 0)
                                aggregated_metrics[player_name]["total_reduced"] += entry.get("totalReduced", 0)
                                aggregated_metrics[player_name]["overheal"] += entry.get("overheal", 0)
                                hit_count = entry.get(
                                    "hitCount",
                                    entry.get(
                                        "tickCount",
                                        1 if entry.get("total", 0) > 0 else 0,
                                    ),
                                )
                                aggregated_metrics[player_name]["hit_count"] += hit_count
                            elif config.get("data_type") == "Survivability":
                                # Survivability is tricky to aggregate, we'll take the average if multiple IDs
                                # but usually ability_id=0 is used for survivability.
                                fights = entry.get("fights", {})
                                if fights:
                                    survivability_values = [float(value) for value in fights.values() if value is not None]
                                    if survivability_values:
                                        avg = (sum(survivability_values) / len(survivability_values)) * 100
                                        # For survivability, we'll just keep the max if multiple IDs (unlikely use case)
                                        aggregated_metrics[player_name]["survivability_percentage"] = max(
                                            aggregated_metrics[player_name]["survivability_percentage"], 
                                            avg
                                        )
                                        aggregated_metrics[player_name]["hit_count"] = max(
                                            aggregated_metrics[player_name]["hit_count"],
                                            len([v for v in fights.values() if v is not None])
                                        )
                            else:
                                # For other data types, sum all numeric fields
                                for key, value in entry.items():
                                    if isinstance(value, (int, float)) and key not in [
                                        "id",
                                        "type",
                                        "name",
                                    ]:
                                        aggregated_metrics[player_name][key] += value

            except Exception as e:
                logger.error(f"Error parsing table data for ability {ability_id} in report {report_code}: {e}")
                continue

        # Post-process Debuffs uptime if multiple IDs were used (average or sum? Usually sum for combined debuffs)
        # But uptime percentage can't exceed 100% technically, but here we might want combined uptime.
        # WarcraftLogs doesn't easily give combined uptime of multiple debuffs via table query.
        # For simplicity, we'll just round the percentages.
        for player_name in aggregated_metrics:
            for key in aggregated_metrics[player_name]:
                if "percentage" in key:
                    aggregated_metrics[player_name][key] = round(aggregated_metrics[player_name][key], 2)

        # Create result based on report_players to ensure consistency and avoid duplicates
        unique_players = {}
        for player in report_players:
            player_name = player["name"]
            if player_name not in unique_players:
                # Start with participant data
                player_entry = {
                    "player_name": player_name,
                    "class": player["type"],
                    "role": player["role"],
                }

                # Add metrics from aggregated data if available
                if player_name in aggregated_metrics:
                    player_entry.update(aggregated_metrics[player_name])
                else:
                    # Add default values for missing players
                    if config.get("data_type") == "Debuffs":
                        player_entry.update({"uptime_percentage": 0.0, "hit_count": 0})
                    elif config.get("data_type") == "DamageTaken":
                        player_entry.update(
                            {
                                "damage_taken": 0,
                                "total_reduced": 0,
                                "overheal": 0,
                                "hit_count": 0,
                            }
                        )
                    elif config.get("data_type") == "Survivability":
                        player_entry.update({"survivability_percentage": 0.0, "hit_count": 0})

                unique_players[player_name] = player_entry
            else:
                # Update with higher values if player appears multiple times
                if player_name in aggregated_metrics:
                    existing_entry = unique_players[player_name]
                    new_metrics = aggregated_metrics[player_name]
                    for key, value in new_metrics.items():
                        if isinstance(value, (int, float)):
                            if key not in existing_entry or value > existing_entry[key]:
                                existing_entry[key] = value

        player_data = list(unique_players.values())
        logger.info(f"Processed {len(player_data)} players from table data for report {report_code}")
        return player_data

    def analyze_deaths_events(
        self,
        report_code: str,
        config: dict[str, Any],
        fight_ids: Optional[set[int]] = None,
        report_players: Optional[list[dict[str, Any]]] = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze player deaths using the Death events query with ability information.

        :param report_code: The WarcraftLogs report code
        :param config: Configuration dictionary containing death analysis parameters
        :param fight_ids: Optional set of fight IDs to filter
        :param report_players: List of players who participated in the fights
        :return: List of player data with death counts and ability information
        """
        if not fight_ids:
            logger.warning("No fight IDs provided for deaths analysis")
            return []

        if not report_players:
            logger.warning("No report players provided for deaths analysis")
            return []

        wipe_cutoff = config.get("wipe_cutoff", DEFAULT_WIPE_CUTOFF)
        ability_ids = config.get("ability_ids")
        if not ability_ids:
            ability_ids = [config.get("ability_id")] if config.get("ability_id") else [None]

        # Create player lookup by ID
        player_lookup = {player["id"]: player for player in report_players}

        # Initialize death tracking for each player
        death_counts = defaultdict(int)
        death_details = defaultdict(lambda: {"abilities": defaultdict(int), "total_deaths": 0})

        try:
            # Query for death events with ability information
            death_query = """
            query GetDeathEvents(
                $reportCode: String!, $fightIDs: [Int]!, $wipeCutoff: Int!, $abilityID: Float
            ) {
              reportData {
                report(code: $reportCode) {
                  events(
                    fightIDs: $fightIDs,
                    dataType: Deaths,
                    hostilityType: Friendlies,
                    wipeCutoff: $wipeCutoff,
                    abilityID: $abilityID,
                    limit: 1000,
                    useAbilityIDs: true
                  ) {
                    data
                  }
                  masterData {
                    abilities {
                      gameID
                      name
                      icon
                      type
                    }
                  }
                }
              }
            }
            """

            for ability_id in ability_ids:
                death_variables = {
                    "reportCode": report_code,
                    "fightIDs": list(fight_ids),
                    "wipeCutoff": wipe_cutoff,
                }

                # Add ability filter if specified
                if ability_id:
                    death_variables["abilityID"] = float(ability_id)

                death_result = self.api_client.make_request(death_query, death_variables)

                if not death_result or "data" not in death_result:
                    logger.warning(f"No death events returned for ability {ability_id} in report {report_code}")
                    continue

                death_events = death_result["data"]["reportData"]["report"]["events"]["data"]
                abilities = death_result["data"]["reportData"]["report"]["masterData"]["abilities"]

                # Create ability lookup
                ability_lookup = {ability["gameID"]: ability for ability in abilities}

                # Process death events
                for event in death_events:
                    if event.get("type") == "death":
                        target_id = event.get("targetID")
                        killing_ability_id = event.get("killingAbilityGameID", 0)

                        # Find the player this death belongs to
                        if target_id in player_lookup:
                            player = player_lookup[target_id]
                            player_name = player["name"]

                            # Count the death
                            death_counts[player_name] += 1
                            death_details[player_name]["total_deaths"] += 1

                            # Track killing ability
                            if killing_ability_id in ability_lookup:
                                ability_name = ability_lookup[killing_ability_id]["name"]
                                death_details[player_name]["abilities"][ability_name] += 1
                            else:
                                death_details[player_name]["abilities"]["Unknown Ability"] += 1

            # Create result data
            unique_players = {}
            for player in report_players:
                player_name = player["name"]
                if player_name not in unique_players:
                    # Start with participant data
                    player_entry = {
                        "player_name": player_name,
                        "class": player["type"],
                        "role": player["role"],
                        "deaths": death_counts[player_name],
                        "hit_count": death_counts[player_name],  # For consistency with other analyses
                    }

                    # Add ability details if available
                    if player_name in death_details:
                        player_entry["death_abilities"] = dict(death_details[player_name]["abilities"])

                    unique_players[player_name] = player_entry

            # Convert to list and log results
            player_data = list(unique_players.values())
            total_deaths = sum(death_counts.values())
            logger.info(f"Processed {total_deaths} deaths for {len(player_data)} players in report {report_code}")

            return player_data

        except Exception as e:
            logger.error(f"Error analyzing death events for report {report_code}: {e}")
            return []

    def analyze_events(
        self,
        report_code: str,
        config: dict[str, Any],
        fight_ids: Optional[set[int]] = None,
        report_players: Optional[list[dict[str, Any]]] = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze generic events with simple filtering.

        This method fetches events of a specific type and counts occurrences
        per player. It applies minimal filtering:
        1. Server-side: ability ID, data type, wipe cutoff
        2. Client-side: event types, pull ignore time

        :param report_code: The WarcraftLogs report code
        :param config: Configuration dictionary containing:
            - data_type: Required. Event data type (e.g., "Debuffs", "Casts")
            - ability_id: Required. The ability ID to track
            - event_types: Optional. List of event types to count
            - pull_ignore_time_ms: Optional. Time in ms to ignore after pull
            - wipe_cutoff: Optional. Wipe cutoff (default: DEFAULT_WIPE_CUTOFF)
        :param fight_ids: Optional set of fight IDs to filter
        :param report_players: List of players who participated in the fights
        :return: List of player data with event counts
        """
        if not fight_ids:
            logger.warning("No fight IDs provided for event analysis")
            return []

        if not report_players:
            logger.warning("No report players provided for event analysis")
            return []

        # Extract required parameters
        data_type = config.get("data_type")
        ability_id = config.get("ability_id")
        ability_ids = config.get("ability_ids")

        if not data_type:
            logger.error("data_type is required for event analysis")
            return []

        if ability_ids:
            ids_to_query = list(ability_ids)
        elif ability_id:
            ids_to_query = [ability_id]
        else:
            logger.error("ability_id or ability_ids is required for event analysis")
            return []

        # Optional parameters
        event_types = config.get("event_types", [])
        pull_ignore_time_ms = config.get("pull_ignore_time_ms", 0)
        wipe_cutoff = config.get("wipe_cutoff", DEFAULT_WIPE_CUTOFF)

        # Create player lookup by ID
        player_lookup = {player["id"]: player for player in report_players}

        try:
            # Query for events
            events_query = """
            query GetEvents(
                $reportCode: String!, $fightIDs: [Int]!, $wipeCutoff: Int!,
                $abilityID: Float, $dataType: EventDataType!
            ) {
              reportData {
                report(code: $reportCode) {
                  events(
                    fightIDs: $fightIDs,
                    dataType: $dataType,
                    hostilityType: Friendlies,
                    wipeCutoff: $wipeCutoff,
                    abilityID: $abilityID,
                    limit: 10000,
                    useAbilityIDs: true
                  ) {
                    data
                  }
                  fights(fightIDs: $fightIDs) {
                    id
                    startTime
                    endTime
                  }
                }
              }
            }
            """

            event_counts: dict[str, int] = defaultdict(int)
            total_events = 0

            for current_ability_id in ids_to_query:
                events_variables = {
                    "reportCode": report_code,
                    "fightIDs": list(fight_ids),
                    "wipeCutoff": wipe_cutoff,
                    "abilityID": float(current_ability_id),
                    "dataType": data_type,
                }

                events_result = self.api_client.make_request(events_query, events_variables)

                if not events_result or "data" not in events_result:
                    logger.warning(
                        f"No {data_type} events returned for ability {current_ability_id} in report {report_code}"
                    )
                    continue

                events = events_result["data"]["reportData"]["report"]["events"]["data"]
                fights = events_result["data"]["reportData"]["report"]["fights"]

                fight_start_times = {fight["id"]: fight["startTime"] for fight in fights}

                for event in events:
                    if event_types:
                        event_type = event.get("type", "")
                        if event_type not in event_types:
                            continue

                    if pull_ignore_time_ms > 0:
                        fight_id = event.get("fight")
                        event_timestamp = event.get("timestamp", 0)
                        if fight_id in fight_start_times:
                            fight_start = fight_start_times[fight_id]
                            if (event_timestamp - fight_start) < pull_ignore_time_ms:
                                continue

                    target_id = event.get("targetID")
                    if target_id in player_lookup:
                        player = player_lookup[target_id]
                        player_name = player["name"]
                        event_counts[player_name] += 1
                        total_events += 1

            # Create result data
            unique_players = {}
            for player in report_players:
                player_name = player["name"]
                if player_name not in unique_players:
                    player_entry = {
                        "player_name": player_name,
                        "class": player["type"],
                        "role": player["role"],
                        "hit_count": event_counts[player_name],
                    }
                    unique_players[player_name] = player_entry

            # Convert to list and log results
            player_data = list(unique_players.values())
            logger.info(
                f"Processed {total_events} {data_type} events for {len(player_data)} players in report {report_code}"
            )

            return player_data

        except Exception as e:
            logger.error(f"Error analyzing events for report {report_code}: {e}")
            return []

    def analyze_player_deaths(
        self,
        report_code: str,
        config: dict[str, Any],
        fight_ids: Optional[set[int]] = None,
        report_players: Optional[list[dict[str, Any]]] = None,
    ) -> list[dict[str, Any]]:
        """
        Analyze player deaths across all fights for a specific player.

        This method analyzes player deaths by:
        1. Using the Deaths dataType to get actual death events
        2. Collecting ALL deaths for the specified player (no filtering)
        3. Tracking top 3 damage sources with % of max HP for each death
        4. Supporting multiple deaths per fight (resurrections)
        5. Organizing data by player for visualization

        :param report_code: The WarcraftLogs report code
        :param config: Analysis configuration dictionary
        :param fight_ids: Set of fight IDs to analyze
        :param report_players: List of players who participated in the fights
        :return: List of player death data
        """
        if not fight_ids:
            fight_ids = self.get_fight_ids(report_code)
        if not report_players:
            report_players = self.get_participants(report_code, fight_ids)

        wipe_cutoff = config.get("wipe_cutoff", DEFAULT_WIPE_CUTOFF)
        damage_window_ms = config.get("damage_window_ms", 10000)  # 10 seconds before death

        # Use CLI override if provided, otherwise use config value
        player_names_filter = getattr(self, "cli_player_names_filter", None) or config.get("player_names")

        # Create player name and class mappings
        player_names = {player.get("id"): player.get("name") for player in report_players}
        player_classes = {player.get("id"): player.get("type", "").upper() for player in report_players}

        try:
            # First get fight details to get start times
            fight_details_query = """
            query GetFightDetails(
                $reportCode: String!, $fightIDs: [Int]!
            ) {
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

            # Query for death events using proper Deaths API with resources
            death_query = """
            query GetDeathEvents(
                $reportCode: String!, $fightIDs: [Int]!, $wipeCutoff: Int!
            ) {
              reportData {
                report(code: $reportCode) {
                  events(
                    fightIDs: $fightIDs,
                    dataType: Deaths,
                    hostilityType: Friendlies,
                    wipeCutoff: $wipeCutoff,
                    limit: 1000,
                    includeResources: true
                  ) {
                    data
                  }
                }
              }
            }
            """

            # Query for damage events to track spells before death (per fight to avoid limits)
            damage_query = """
            query GetDamageEvents(
                $reportCode: String!, $fightID: Int!, $wipeCutoff: Int!
            ) {
              reportData {
                report(code: $reportCode) {
                  events(
                    fightIDs: [$fightID],
                    dataType: DamageTaken,
                    hostilityType: Friendlies,
                    wipeCutoff: $wipeCutoff,
                    limit: 10000,
                    includeResources: true
                  ) {
                    data
                  }
                  masterData {
                    abilities {
                      gameID
                      name
                      icon
                      type
                    }
                  }
                }
              }
            }
            """

            # Execute queries
            base_variables = {
                "reportCode": report_code,
                "fightIDs": list(fight_ids),
            }

            death_variables = {
                **base_variables,
                "wipeCutoff": wipe_cutoff,
            }

            # Get fight details first
            fight_details_result = self.api_client.make_request(fight_details_query, base_variables)
            death_result = self.api_client.make_request(death_query, death_variables)

            if not death_result or "data" not in death_result:
                logger.warning(f"No death events returned for report {report_code}")
                return []

            # Query damage events per fight to avoid API limits
            all_damage_events = []
            all_cast_events: list[dict[str, Any]] = []
            abilities_data = None

            cast_query = """
            query GetCastEvents(
                $reportCode: String!, $fightID: Int!, $wipeCutoff: Int!
            ) {
              reportData {
                report(code: $reportCode) {
                  events(
                    fightIDs: [$fightID],
                    dataType: Casts,
                    hostilityType: Friendlies,
                    wipeCutoff: $wipeCutoff,
                    limit: 10000
                  ) {
                    data
                  }
                }
              }
            }
            """

            for fight_id in fight_ids:
                damage_variables = {
                    "reportCode": report_code,
                    "fightID": fight_id,
                    "wipeCutoff": wipe_cutoff,
                }

                damage_result = self.api_client.make_request(damage_query, damage_variables)

                if damage_result and "data" in damage_result:
                    fight_damage_events = damage_result["data"]["reportData"]["report"]["events"]["data"]
                    all_damage_events.extend(fight_damage_events)

                    # Get abilities data from the first successful query
                    if abilities_data is None:
                        abilities_data = damage_result["data"]["reportData"]["report"]["masterData"]["abilities"]

                    logger.debug(f"Retrieved {len(fight_damage_events)} damage events for fight {fight_id}")
                else:
                    logger.warning(f"No damage events returned for fight {fight_id}")

                cast_result = self.api_client.make_request(cast_query, damage_variables)
                if cast_result and "data" in cast_result:
                    fight_casts = cast_result["data"]["reportData"]["report"]["events"]["data"]
                    all_cast_events.extend(fight_casts)
                    logger.debug(f"Retrieved {len(fight_casts)} cast events for fight {fight_id}")

            logger.info(f"Retrieved total {len(all_damage_events)} damage events across all fights")

            if not all_damage_events:
                logger.warning(f"No damage events returned for any fight in report {report_code}")
                return []

            # Extract fight start times and durations
            fight_start_times = {}
            fight_durations = {}
            if fight_details_result and "data" in fight_details_result:
                fights = fight_details_result["data"]["reportData"]["report"]["fights"]
                for fight in fights:
                    fight_start_times[fight["id"]] = fight["startTime"]
                    fight_durations[fight["id"]] = (fight["endTime"] - fight["startTime"]) / 1000.0

            death_events = death_result["data"]["reportData"]["report"]["events"]["data"]
            damage_events = all_damage_events

            # Extract ability lookup from abilities data
            abilities = abilities_data or []
            ability_lookup = {ability["gameID"]: ability["name"] for ability in abilities}

            # Extract maxHitPoints from death events and damage events
            player_max_hp = self._extract_max_hp_from_events(death_events, damage_events, player_names)

            # Build per-player cast timeline keyed by ability ID for defensive availability
            player_cast_timeline: dict[int, dict[int, list[int]]] = {}
            for evt in all_cast_events:
                source_id = evt.get("sourceID")
                ability_id = evt.get("abilityGameID")
                ts = evt.get("timestamp")
                if source_id is None or ability_id is None or ts is None:
                    continue
                player_cast_timeline.setdefault(source_id, {}).setdefault(ability_id, []).append(ts)

            # Process player deaths data organized by player
            player_death_data = self._process_player_deaths(
                death_events,
                damage_events,
                player_names,
                player_classes,
                fight_start_times,
                fight_durations,
                damage_window_ms,
                ability_lookup,
                player_max_hp,
                player_names_filter,
                report_code=report_code,
            )

            # Annotate each death with available defensives at death time
            self._annotate_available_defensives(player_death_data, player_cast_timeline, report_players)

            # Attach spec from participants for downstream display.
            name_to_spec = {p["name"]: p.get("spec") for p in report_players if p.get("name")}
            for player_info in player_death_data:
                player_info["player_spec"] = name_to_spec.get(player_info.get("player_name"))

            logger.info(f"Analyzed death events for report {report_code}: {len(player_death_data)} players with deaths")
            return player_death_data

        except Exception as e:
            logger.error(f"Error analyzing player deaths for report {report_code}: {e}")
            return []

    def _annotate_available_defensives(
        self,
        player_death_data: list[dict[str, Any]],
        player_cast_timeline: dict[int, dict[int, list[int]]],
        report_players: list[dict[str, Any]],
    ) -> None:
        """
        For each death, attach a list of defensives that were off cooldown.

        An ability is "available" if the player either never cast it before
        the death, or its last cast was longer ago than its cooldown.
        Abilities with cooldown <= 0 (passives / resource-driven) are skipped.

        :param player_death_data: List of per-player death records (mutated in place).
        :param player_cast_timeline: source_id -> ability_id -> [timestamps_ms]
        :param report_players: Player participation data to resolve player_name -> id.
        """
        from ..config.defensives import cast_ids_for, load_defensives

        defensives_by_class = load_defensives()
        if not defensives_by_class:
            logger.debug("No defensives data loaded; skipping availability annotation")
            return

        name_to_id = {p["name"]: p["id"] for p in report_players if p.get("name") and p.get("id") is not None}
        name_to_spec = {p["name"]: p.get("spec") for p in report_players if p.get("name")}

        for player_info in player_death_data:
            player_name = player_info.get("player_name")
            player_class = (player_info.get("player_class") or "").upper()
            player_spec = name_to_spec.get(player_name) or ""
            # Restrict per-spec abilities: only keep abilities where the listed
            # spec is "All" (class-wide) or matches the player's actual spec.
            class_defensives = [
                a for a in defensives_by_class.get(player_class, [])
                if a["cooldown"] > 0
                and (a.get("spec", "All") == "All" or a.get("spec", "") == player_spec)
            ]
            if not class_defensives:
                for death in player_info.get("deaths", []):
                    death["available_defensives"] = []
                continue

            source_id = name_to_id.get(player_name)
            casts = player_cast_timeline.get(source_id, {}) if source_id is not None else {}

            for death in player_info.get("deaths", []):
                death_ts = death.get("death_timestamp")
                if death_ts is None:
                    death["available_defensives"] = []
                    continue
                fight_start_ts = death.get("fight_start_timestamp")

                available: list[dict[str, Any]] = []
                for ability in class_defensives:
                    # Aggregate timestamps across all WCL cast IDs that
                    # represent a use of this ability (handles e.g. Demonic
                    # Healthstone being logged as a cast of 6262).
                    timestamps: list[int] = []
                    for cid in cast_ids_for(ability["spell_id"]):
                        timestamps.extend(casts.get(cid, []))

                    # Consumables (healthstones, potions) reset on combat
                    # leave, so they're effectively once-per-fight regardless
                    # of their listed cooldown — only casts within the
                    # current fight should block availability.
                    if ability.get("single_use_per_fight"):
                        if fight_start_ts is None:
                            is_available = not any(ts <= death_ts for ts in timestamps)
                        else:
                            is_available = not any(
                                fight_start_ts <= ts <= death_ts for ts in timestamps
                            )
                    else:
                        last_cast = None
                        for ts in timestamps:
                            if ts <= death_ts and (last_cast is None or ts > last_cast):
                                last_cast = ts
                        cooldown_ms = ability["cooldown"] * 1000
                        is_available = last_cast is None or (death_ts - last_cast) >= cooldown_ms

                    if is_available:
                        available.append({
                            "spell_id": ability["spell_id"],
                            "name": ability["name"],
                            "type": ability["type"],
                            "cooldown": ability["cooldown"],
                        })

                death["available_defensives"] = available

    def _extract_max_hp_from_events(
        self,
        death_events: list[dict[str, Any]],
        damage_events: list[dict[str, Any]],
        player_names: dict[int, str],
    ) -> dict[int, int]:
        """
        Extract maxHitPoints for each player from death events and damage events.

        Both death events and damage events with includeResources=true include maxHitPoints.

        :param death_events: List of death events (includes damage events with resources)
        :param damage_events: List of damage events (includes resources)
        :param player_names: Dictionary mapping player IDs to names
        :return: Dictionary mapping player IDs to their maxHitPoints
        """
        player_max_hp = {}

        # Extract from death events (includes damage events with resources)
        for event in death_events:
            # Look for damage events that have maxHitPoints
            if event.get("type") == "damage" and "maxHitPoints" in event:
                target_id = event.get("targetID")
                max_hit_points = event.get("maxHitPoints")

                if target_id in player_names and max_hit_points and max_hit_points > 0:
                    # Use the highest maxHitPoints found for this player
                    if target_id not in player_max_hp or max_hit_points > player_max_hp[target_id]:
                        player_max_hp[target_id] = max_hit_points
                        player_name = player_names[target_id]
                        logger.debug(
                            f"Found maxHitPoints {max_hit_points:,} for player " f"{player_name} from death events"
                        )

        # Extract from damage events (now includes resources)
        for event in damage_events:
            # Look for damage events that have maxHitPoints
            if event.get("type") == "damage" and "maxHitPoints" in event:
                target_id = event.get("targetID")
                max_hit_points = event.get("maxHitPoints")

                if target_id in player_names and max_hit_points and max_hit_points > 0:
                    # Use the highest maxHitPoints found for this player
                    if target_id not in player_max_hp or max_hit_points > player_max_hp[target_id]:
                        player_max_hp[target_id] = max_hit_points
                        player_name = player_names[target_id]
                        logger.debug(
                            f"Found maxHitPoints {max_hit_points:,} for player " f"{player_name} from damage events"
                        )

        return player_max_hp

    def _process_player_deaths(
        self,
        death_events: list[dict[str, Any]],
        damage_events: list[dict[str, Any]],
        player_names: dict[int, str],
        player_classes: dict[int, str],
        fight_start_times: dict[int, int],
        fight_durations: dict[int, float],
        damage_window_ms: int,
        ability_lookup: dict[int, str],
        player_max_hp: dict[int, int],
        player_names_filter: Optional[list[str]] = None,
        report_code: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Process death events organized by player across all fights.

        :param death_events: List of death events from API
        :param damage_events: List of damage events from API
        :param player_names: Dictionary mapping player IDs to names
        :param player_classes: Dictionary mapping player IDs to class names
        :param fight_start_times: Dictionary mapping fight IDs to start times
        :param fight_durations: Dictionary mapping fight IDs to durations in seconds
        :param damage_window_ms: Time window to look back for damage events
        :param ability_lookup: Dictionary mapping ability IDs to names
        :param player_max_hp: Dictionary mapping player IDs to their maxHitPoints
        :param player_names_filter: Optional list of player names to filter deaths for
        :return: List of player death data
        """
        # Group events by fight for efficient lookups
        damage_by_fight = defaultdict(list)
        for event in damage_events:
            if event.get("type") == "damage":
                damage_by_fight[event["fight"]].append(event)

        # Collect all deaths organized by player
        deaths_by_player = defaultdict(list)
        total_death_events = sum(1 for event in death_events if event.get("type") == "death")
        logger.info(f"Processing {total_death_events} total death events across all fights")

        # Death cut-off: per fight, only keep raid-wide deaths that occurred
        # before the 4th death. Once 4+ players are dead the wipe is decided
        # and remaining deaths aren't actionable.
        DEATH_CUTOFF = 4
        ordered_by_fight: dict[int, list[tuple[int, int]]] = defaultdict(list)
        for event in death_events:
            if event.get("type") == "death":
                ordered_by_fight[event["fight"]].append((event["timestamp"], event["targetID"]))
        kept_death_keys: set[tuple[int, int, int]] = set()
        # death_index_in_fight: 1-indexed rank of each death within its fight,
        # matching WCL's `&death=N` URL parameter.
        death_index_in_fight: dict[tuple[int, int, int], int] = {}
        for fight_id, lst in ordered_by_fight.items():
            lst.sort()
            for idx, (ts, tgt) in enumerate(lst, start=1):
                death_index_in_fight[(fight_id, ts, tgt)] = idx
                if idx <= DEATH_CUTOFF:
                    kept_death_keys.add((fight_id, ts, tgt))

        for event in death_events:
            if event.get("type") == "death":
                player_id = event["targetID"]
                player_name = player_names.get(player_id, f"Player {player_id}")

                # Apply player names filter if specified
                if player_names_filter and player_name not in player_names_filter:
                    continue

                fight_id = event["fight"]
                if (fight_id, event["timestamp"], player_id) not in kept_death_keys:
                    continue
                death_timestamp = event["timestamp"]
                fight_start_time = fight_start_times.get(fight_id, 0)
                fight_time_seconds = (death_timestamp - fight_start_time) / 1000.0
                fight_length_seconds = fight_durations.get(fight_id, 0.0)

                # Get damage events for this fight
                fight_damage = damage_by_fight.get(fight_id, [])

                # Find top damage sources before death
                max_hit_points = player_max_hp.get(player_id)
                damage_spells = self._get_damage_before_death(
                    fight_damage,
                    player_id,
                    death_timestamp,
                    damage_window_ms,
                    ability_lookup,
                    max_hit_points,
                )

                # Get top 3 damage sources
                top_damage_sources = damage_spells[:3] if damage_spells else []

                # Identify the killing blow (most recent damage among top 3)
                killing_blow_timestamp = -1
                if top_damage_sources:
                    killing_blow_timestamp = max(spell.get("last_hit_timestamp", 0) for spell in top_damage_sources)

                death_idx = death_index_in_fight.get((fight_id, death_timestamp, player_id))
                wcl_url = None
                if report_code and death_idx is not None:
                    wcl_url = (
                        f"https://www.warcraftlogs.com/reports/{report_code}"
                        f"?fight={fight_id}&type=deaths&death={death_idx}"
                    )

                death_data = {
                    "fight_id": fight_id,
                    "death_timestamp": death_timestamp,
                    "fight_start_timestamp": fight_start_time,
                    "death_index_in_fight": death_idx,
                    "wcl_url": wcl_url,
                    "fight_time_seconds": fight_time_seconds,
                    "fight_length_seconds": fight_length_seconds,
                    "damage_sources": [
                        {
                            "ability_id": spell.get("ability_id"),
                            "name": spell["ability_name"],
                            "damage": spell["damage"],
                            "hp_percentage": spell.get("health_percentage", 0),
                            "is_killing_blow": spell.get("last_hit_timestamp", 0) == killing_blow_timestamp,
                        }
                        for spell in top_damage_sources
                    ],
                }

                deaths_by_player[player_id].append(death_data)

        # Convert to list format and sort deaths by fight number
        result = []
        for player_id, deaths in deaths_by_player.items():
            player_name = player_names.get(player_id, f"Player {player_id}")
            player_class = player_classes.get(player_id, "Unknown")

            # Sort deaths by fight_id
            deaths.sort(key=lambda x: x["fight_id"])

            # Log player death counts
            fight_ids = sorted(set(d["fight_id"] for d in deaths))
            logger.info(
                f"Player {player_name}: {len(deaths)} deaths across {len(fight_ids)} fights (fights: {fight_ids})"
            )

            result.append(
                {
                    "player_id": player_id,
                    "player_name": player_name,
                    "player_class": player_class,
                    "deaths": deaths,
                }
            )

        # Sort by player name
        result.sort(key=lambda x: x["player_name"])

        return result

    def _process_death_events(
        self,
        death_events: list[dict[str, Any]],
        damage_events: list[dict[str, Any]],
        player_names: dict[int, str],
        player_classes: dict[int, str],
        fight_start_times: dict[int, int],
        health_threshold: int,
        damage_window_ms: int,
        death_grouping_window_ms: int,
        ability_lookup: dict[int, str],
        player_max_hp: dict[int, int],
    ) -> list[dict[str, Any]]:
        """
        Process death events into timeline data with intelligent grouping.

        :param death_events: List of death events from API
        :param damage_events: List of damage events from API
        :param player_names: Dictionary mapping player IDs to names
        :param player_classes: Dictionary mapping player IDs to class names
        :param fight_start_times: Dictionary mapping fight IDs to start times
        :param health_threshold: Health percentage threshold for non-instant deaths
        :param damage_window_ms: Time window to look back for damage events
        :param death_grouping_window_ms: Time window for death grouping logic
        :param ability_lookup: Dictionary mapping ability IDs to names
        :param player_max_hp: Dictionary mapping player IDs to their maxHitPoints
        :return: List of timeline data per fight
        """
        # Group events by fight
        deaths_by_fight = defaultdict(list)
        damage_by_fight = defaultdict(list)

        for event in death_events:
            if event.get("type") == "death":
                deaths_by_fight[event["fight"]].append(event)

        for event in damage_events:
            if event.get("type") == "damage":
                damage_by_fight[event["fight"]].append(event)

        timeline_results = []

        for fight_id, fight_deaths in deaths_by_fight.items():
            # Sort deaths by timestamp
            fight_deaths.sort(key=lambda x: x["timestamp"])
            fight_damage = damage_by_fight.get(fight_id, [])

            # Filter deaths based on health threshold and instant death logic
            valid_deaths = self._filter_valid_deaths(fight_deaths, health_threshold)

            # Apply death grouping logic (4 deaths + 10-second window)
            analyzed_deaths = self._apply_death_grouping_logic(valid_deaths, death_grouping_window_ms)

            if not analyzed_deaths:
                continue

            # Build timeline data for this fight
            fight_timeline = {
                "fight_id": fight_id,
                "deaths": [],
                "death_count": len(analyzed_deaths),
                "timeline_duration_ms": analyzed_deaths[-1]["timestamp"] - analyzed_deaths[0]["timestamp"],
            }

            for death in analyzed_deaths:
                player_id = death["targetID"]
                player_name = player_names.get(player_id, f"Player {player_id}")
                player_class = player_classes.get(player_id, "Unknown")
                death_timestamp = death["timestamp"]

                # Calculate health percentage before death (not after, since after death = 0%)
                hit_points_before_death = death.get("hitPoints", 0)
                # Use maxHitPoints from damage events for reliable health percentage calculation
                max_hit_points = player_max_hp.get(player_id, 0)
                overkill = death.get("overkill", 0)

                # Debug logging for health percentage calculation
                logger.debug(
                    f"Player {player_name} max HP from damage events: "
                    f"{max_hit_points}, hit points: {hit_points_before_death}, "
                    f"overkill: {overkill}"
                )

                # If maxHitPoints is 0 or missing, we can't calculate meaningful percentages
                if max_hit_points <= 0:
                    logger.warning(
                        f"No maxHitPoints found for player {player_name} in damage "
                        f"events, skipping health percentage calculation"
                    )
                    max_hit_points = None

                # Find damage events leading to this death
                damage_spells = self._get_damage_before_death(
                    fight_damage,
                    player_id,
                    death_timestamp,
                    damage_window_ms,
                    ability_lookup,
                    max_hit_points,
                )

                # Health percentage before taking the killing blow
                health_before_death = (
                    (hit_points_before_death + overkill) / max_hit_points * 100
                    if max_hit_points and max_hit_points > 0
                    else 0
                )

                # Convert timestamp to fight time (relative to fight start)
                fight_start_time = fight_start_times.get(fight_id, 0)
                fight_time_seconds = (death_timestamp - fight_start_time) / 1000.0

                death_data = {
                    "player_id": player_id,
                    "player_name": player_name,
                    "player_class": player_class,
                    "timestamp": death_timestamp,
                    "fight_time_seconds": fight_time_seconds,
                    "health_percentage": health_before_death,
                    "is_instant_death": self._is_instant_death(death),
                    "damage_spells": damage_spells,
                    "total_damage_taken": sum(spell["damage"] for spell in damage_spells),
                    "overkill": overkill,
                }

                fight_timeline["deaths"].append(death_data)

            timeline_results.append(fight_timeline)

        return timeline_results

    def _filter_valid_deaths(self, deaths: list[dict[str, Any]], health_threshold: int) -> list[dict[str, Any]]:
        """
        Filter deaths based on health threshold and instant death criteria.

        :param deaths: List of death events
        :param health_threshold: Health percentage threshold
        :return: List of valid death events
        """
        valid_deaths = []

        for death in deaths:
            max_hit_points = death.get("maxHitPoints", 0)
            hit_points = death.get("hitPoints", 0)

            # Calculate health percentage safely
            if max_hit_points > 0:
                health_percentage = hit_points / max_hit_points * 100
            else:
                health_percentage = 0

            # Include deaths where health was below threshold OR instant deaths
            if health_percentage < health_threshold or self._is_instant_death(death):
                valid_deaths.append(death)

        return valid_deaths

    def _is_instant_death(self, death: dict[str, Any]) -> bool:
        """
        Determine if a death was instant (100% -> 0% health).

        :param death: Death event
        :return: True if instant death, False otherwise
        """
        # Check if death was from full health (assuming overkill indicates instant death)
        overkill = death.get("overkill", 0)
        hit_points = death.get("hitPoints", 0)
        max_hit_points = death.get("maxHitPoints", 0)

        # If we don't have valid max hit points data, we can't determine instant death
        if max_hit_points <= 0:
            return False

        # If overkill is significant compared to max health, it's likely instant
        return overkill > (max_hit_points * 0.5) or hit_points == max_hit_points

    def _apply_death_grouping_logic(
        self, deaths: list[dict[str, Any]], grouping_window_ms: int
    ) -> list[dict[str, Any]]:
        """
        Apply death grouping logic: 4 deaths + 10-second window rule.

        :param deaths: List of death events
        :param grouping_window_ms: Time window for grouping logic
        :return: List of deaths to analyze
        """
        if len(deaths) <= 4:
            return deaths

        # Take first 4 deaths
        first_four = deaths[:4]
        fourth_death_time = first_four[3]["timestamp"]

        # Check deaths in next 10 seconds
        next_deaths = []
        for death in deaths[4:]:
            if death["timestamp"] <= fourth_death_time + grouping_window_ms:
                next_deaths.append(death)
            else:
                break

        # Apply rule: if more than 2 deaths in next 10 seconds, exclude 4th death
        if len(next_deaths) > 2:
            return first_four[:3]  # Return only first 3 deaths
        else:
            return first_four + next_deaths[:2]  # Return first 4 + up to 2 more

    def _get_damage_before_death(
        self,
        damage_events: list[dict[str, Any]],
        player_id: int,
        death_timestamp: int,
        damage_window_ms: int,
        ability_lookup: dict[int, str],
        max_hit_points: Optional[int],
    ) -> list[dict[str, Any]]:
        """
        Get damage spells that hit a player before their death.

        :param damage_events: List of damage events
        :param player_id: Player ID
        :param death_timestamp: Timestamp of death
        :param damage_window_ms: Time window to look back
        :param ability_lookup: Dictionary mapping ability IDs to names
        :param max_hit_points: Player's maximum hit points for health percentage calculation (None if unavailable)
        :return: List of damage spells with details including health percentage
        """
        damage_spells = []
        start_time = death_timestamp - damage_window_ms

        for event in damage_events:
            if event.get("targetID") == player_id and start_time <= event["timestamp"] <= death_timestamp:
                ability_id = event.get("abilityGameID", 0)
                ability_name = ability_lookup.get(ability_id, "Unknown Ability")
                damage_amount = event.get("amount", 0)

                # Calculate health percentage for this damage
                health_percentage = (
                    (damage_amount / max_hit_points * 100) if max_hit_points and max_hit_points > 0 else 0
                )

                damage_spells.append(
                    {
                        "ability_id": ability_id,
                        "ability_name": ability_name,
                        "damage": damage_amount,
                        "health_percentage": health_percentage,
                        "timestamp": event["timestamp"],
                        "source_id": event.get("sourceID"),
                        "time_before_death_ms": death_timestamp - event["timestamp"],
                    }
                )

        # Sort by timestamp (most recent first)
        damage_spells.sort(key=lambda x: x["timestamp"], reverse=True)

        # Group by ability and sum damage
        ability_damage = defaultdict(lambda: {"damage": 0, "count": 0, "last_hit": 0})
        for spell in damage_spells:
            ability_id = spell["ability_id"]
            ability_damage[ability_id]["damage"] += spell["damage"]
            ability_damage[ability_id]["count"] += 1
            ability_damage[ability_id]["ability_name"] = spell["ability_name"]
            ability_damage[ability_id]["last_hit"] = max(ability_damage[ability_id]["last_hit"], spell["timestamp"])

        # Convert to list and sort by damage
        result = []
        for ability_id, data in ability_damage.items():
            # Calculate health percentage for the total damage from this ability
            total_damage = data["damage"]
            health_percentage = (total_damage / max_hit_points * 100) if max_hit_points and max_hit_points > 0 else 0

            result.append(
                {
                    "ability_id": ability_id,
                    "ability_name": data["ability_name"],
                    "damage": total_damage,
                    "health_percentage": health_percentage,
                    "hit_count": data["count"],
                    "last_hit_timestamp": data["last_hit"],
                    "time_before_death_ms": death_timestamp - data["last_hit"],
                }
            )

        # Sort by damage (highest first)
        result.sort(key=lambda x: x["damage"], reverse=True)

        return result[:10]  # Return top 10 damage sources

    def generate_plots(self, include_progress_plots: bool = True, include_player_deaths: bool = False) -> None:
        """
        Generate plots using configuration.

        :param include_progress_plots: Whether to generate progress plots (default: True)
        :param include_player_deaths: Whether to generate player deaths plots (default: False)
        """
        if self.CONFIG:
            self._generate_plots_generic(include_player_deaths=include_player_deaths)
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

    def _generate_plots_generic(self, include_player_deaths: bool = False) -> None:
        """Generate plots using configuration.

        :param include_player_deaths: Whether to generate player deaths plots (default: False)
        """
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
                    include_player_deaths=include_player_deaths,
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
        include_player_deaths: bool = False,
    ) -> None:
        """
        Generate a single plot based on configuration.

        :param include_player_deaths: Whether to generate player deaths plots (default: False)

        :param plot_config: Plot configuration dictionary
        :param report_date: Date string for the report
        :param current_fight_duration: Total duration of current fights in milliseconds
        :param previous_fight_duration: Total duration of previous fights in milliseconds
        """
        analysis_name = plot_config["analysis_name"]
        plot_type = plot_config["type"]
        title = plot_config["title"]

        # Handle player deaths plots separately (they don't use column configuration)
        if plot_type == "PlayerDeathsPlot":
            if include_player_deaths:
                self._generate_player_deaths_plot(analysis_name, title, report_date, plot_config)
                logger.debug(f"Generated individual {plot_type} plots for {title}")
            else:
                logger.debug(f"Skipping player deaths plot for {title} (flag disabled)")
            return

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
        description = plot_config.get("description")
        invert_change_colors = plot_config.get("invert_change_colors", False)

        # Get analysis data
        current_data, previous_dict = self.find_analysis_data(analysis_name, column_key_1, name_column)

        # Get the current result to access fight duration for normalization
        current_result = None
        if self.results:
            # Find the result that contains the current analysis data
            sorted_reports = sorted(self.results, key=lambda x: x["starttime"], reverse=True)
            for report in sorted_reports:
                for analysis in report.get("analysis", []):
                    if analysis.get("name") == analysis_name:
                        current_result = report
                        break
                if current_result:
                    break

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

        # Check if we have data to plot
        if not current_data:
            logger.warning(f"No data found for analysis {analysis_name}, skipping plot generation")
            return

        df = pd.DataFrame(current_data)

        # Apply duration normalization only to previous data for change calculations
        if current_result and current_result.get("total_duration"):
            # Only normalize previous data using its own fight duration for accurate change calculations
            if previous_dict and previous_fight_duration:
                normalized_previous_dict = {}
                duration_30min = previous_fight_duration / (1000 * 60 * 30)

                # Only normalize if it's not a percentage
                if column_key_1 != "uptime_percentage" and not column_key_1.endswith("_percentage"):
                    for player_name, value in previous_dict.items():
                        normalized_previous_dict[player_name] = value / duration_30min
                    previous_dict = normalized_previous_dict
                    logger.debug(f"Applied duration normalization to previous data for change calculations for {title}")

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
                description=description,
                invert_change_colors=invert_change_colors,
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
                description=description,
                invert_change_colors=invert_change_colors,
            )
        elif plot_type == "SurvivabilityPlot":
            plot = SurvivabilityPlot(
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
                description=description,
                invert_change_colors=invert_change_colors,
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
                description=description,
                invert_change_colors=invert_change_colors,
            )
        else:
            raise ValueError(f"Unknown plot type: {plot_type}")

        if plot:
            plot.save()
            logger.debug(f"Generated {plot_type} for {title}")

    def _generate_player_deaths_plot(
        self,
        analysis_name: str,
        title: str,
        report_date: str,
        plot_config: dict[str, Any],
    ) -> Optional[PlayerDeathsPlot]:
        """
        Generate player deaths plot for player deaths across all fights.

        :param analysis_name: Name of the analysis
        :param title: Plot title
        :param report_date: Date string for the report
        :param plot_config: Plot configuration
        :return: None (saves plot directly)
        """
        # Find the player deaths data
        player_data = None
        if self.results:
            sorted_reports = sorted(self.results, key=lambda x: x["starttime"], reverse=True)
            for report in sorted_reports:
                for analysis in report.get("analysis", []):
                    if analysis.get("name") == analysis_name:
                        player_data = analysis.get("data", [])
                        break
                if player_data:
                    break

        if not player_data:
            logger.warning(f"No player deaths data found for analysis {analysis_name}")
            return None

        # Generate plot for player deaths
        if player_data:
            self._save_player_death_plots(player_data, title, report_date, plot_config)

        return None  # We handle saving directly, so return None

    def _save_player_death_plots(
        self,
        player_data: list[dict[str, Any]],
        title: str,
        report_date: str,
        plot_config: dict[str, Any],
    ) -> None:
        """
        Save all player deaths into a single multi-page PDF (one player per page).

        WCL deep-links rendered in each row are clickable in the PDF output.

        :param player_data: List of player death data
        :param title: Plot title
        :param report_date: Date string for the report
        :param plot_config: Plot configuration
        """
        import re
        from datetime import datetime

        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_pdf import PdfPages

        from ..config.settings import Settings

        plots_dir = Settings().plots_directory
        try:
            date_obj = datetime.strptime(report_date, "%d.%m.%Y")
            date_stamp = date_obj.strftime("%Y-%m-%d")
        except (ValueError, AttributeError):
            date_stamp = datetime.now().strftime("%Y-%m-%d")

        deaths_dir = plots_dir / date_stamp
        deaths_dir.mkdir(parents=True, exist_ok=True)

        pdf_path = deaths_dir / f"{date_stamp}_player_deaths.pdf"

        # Sort players by name for stable page ordering.
        ordered = sorted(
            (p for p in player_data if p.get("deaths")),
            key=lambda p: p["player_name"].lower(),
        )
        if not ordered:
            logger.warning("No players with deaths to render")
            return

        plot = PlayerDeathsPlot(
            title=title,
            date=report_date,
            player_data=ordered,
            figsize=plot_config.get("figsize", (18, 12)),
        )
        figures = plot.create_player_figures()

        with PdfPages(str(pdf_path)) as pdf:
            for _player_info, fig in figures:
                pdf.savefig(
                    fig,
                    facecolor=PlotColors.BACKGROUND,
                    edgecolor="none",
                    bbox_inches="tight",
                )
                plt.close(fig)

            pdf_meta = pdf.infodict()
            pdf_meta["Title"] = f"{title} — Player Deaths"
            pdf_meta["Subject"] = "Per-player death timelines with available defensives"
            pdf_meta["CreationDate"] = datetime.now()

        logger.info(f"Player deaths PDF ({len(figures)} pages) saved to {pdf_path}")

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

                    # Duration normalization is not applied to progress plots
                    # as they display normal values, not changes

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

        # Convert duration to 30-minute units for normalization (more appropriate for raid encounters)
        duration_30min = total_duration_ms / (1000 * 60 * 30)

        # Universal normalization: normalize all numeric columns except percentage metrics
        if column_key == "uptime_percentage" or column_key.endswith("_percentage"):
            # Percentage metrics don't need duration normalization as they're already relative
            logger.debug(f"Skipping normalization for percentage metric '{column_key}'")
        elif column_key == "deaths":
            # Deaths are typically not normalized by duration as they represent discrete events
            logger.debug(f"Skipping normalization for death count metric '{column_key}'")
        else:
            # For all other numeric metrics, normalize to "per 30 minutes"
            logger.debug(f"Applying duration normalization to metric '{column_key}' (per 30 minutes)")
            df_normalized[column_key] = df_normalized[column_key] / duration_30min
            df_normalized[f"{column_key}_original"] = df[column_key]  # Keep original for reference

        return df_normalized
