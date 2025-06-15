"""
Base analysis module for Guild Log Analysis.

This module provides the base class for all boss-specific analyses,
containing common functionality and abstract methods.
"""

import logging
from abc import ABC
from collections import defaultdict
from typing import Any, Optional

from ..api.client import WarcraftLogsAPIClient
from ..config.constants import DEFAULT_WIPE_CUTOFF

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
        self.ANALYSIS_CONFIG: list[dict[str, Any]] = getattr(self, "ANALYSIS_CONFIG", [])
        self.PLOT_CONFIG: list[dict[str, Any]] = getattr(self, "PLOT_CONFIG", [])

    def analyze(self, report_codes: list[str]) -> None:
        """
        Analyze reports for this specific boss using configuration.

        :param report_codes: List of Warcraft Logs report codes to analyze
        """
        if self.ANALYSIS_CONFIG:
            # Use configuration-based analysis
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
        raise NotImplementedError("Either implement ANALYSIS_CONFIG or override _analyze_legacy")

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

        report_results = {
            "starttime": start_time,
            "reportCode": report_code,
            "analysis": [],
            "fight_ids": fight_ids,
        }

        # Get players who participated in these specific fights
        report_players = self.get_participants(report_code, fight_ids)
        if not report_players:
            return

        # Execute all configured analyses
        for config in self.ANALYSIS_CONFIG:
            try:
                data = self._execute_analysis(config, report_code, fight_ids, report_players)
                report_results["analysis"].append({"name": config["name"], "data": data})
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
        analysis_type = config["type"]

        if analysis_type == "interrupts":
            data = self.analyze_interrupts(
                report_code=report_code,
                fight_ids=fight_ids,
                report_players=report_players,
                ability_id=config["ability_id"],
            )
        elif analysis_type == "debuff_uptime":
            data = self.analyze_debuff_uptime(
                report_code=report_code,
                fight_ids=fight_ids,
                report_players=report_players,
                ability_id=config["ability_id"],
                wipe_cutoff=config.get("wipe_cutoff", DEFAULT_WIPE_CUTOFF),
                filter_expression=config.get("filter_expression"),
            )
        elif analysis_type == "damage_to_actor":
            data = self.get_damage_to_actor(
                report_code=report_code,
                fight_ids=fight_ids,
                target_game_id=config["target_game_id"],
                report_players=report_players,
                filter_expression=config.get("filter_expression"),
                wipe_cutoff=config.get("wipe_cutoff", DEFAULT_WIPE_CUTOFF),
            )
            # Rename damage field if result_key is specified
            if "result_key" in config and config["result_key"] != "damage":
                for player_data in data:
                    player_data[config["result_key"]] = player_data.pop("damage")
        else:
            raise ValueError(f"Unknown analysis type: {analysis_type}")

        return data

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
        :param wipe_cutoff: Threshold for considering fights as wipes
        :return: List of player data with damage values
        """
        # Step 1: Get all actors to find target IDs
        actors_query = """
        query GetActors($reportCode: String!) {
          reportData {
            report(code: $reportCode) {
              masterData {
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

        # Step 2: Get damage done data for each target and aggregate
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
    ) -> list[dict[str, Any]]:
        """
        Analyze interrupt events for a specific ability.

        :param report_code: The WarcraftLogs report code
        :param fight_ids: Set of fight IDs to analyze
        :param report_players: List of players who participated in the fights
        :param ability_id: The ability ID to track interrupts for
        :return: List of player data with interrupt counts
        """
        events = []
        next_timestamp = None

        # Get interrupt events
        query = """
        query GetInterrupts($reportCode: String!, $fightIds: [Int!]!, $abilityId: Float!, $startTime: Float) {
          reportData {
            report(code: $reportCode) {
              events(
                dataType: Interrupts
                fightIDs: $fightIds
                abilityID: $abilityId
                startTime: $startTime
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
                "abilityId": ability_id,
                "startTime": next_timestamp,  # None for first page, timestamp for subsequent pages
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
        :param wipe_cutoff: Threshold for considering fights as wipes
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
            "abilityID": ability_id,
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

    def generate_plots(self) -> None:
        """Generate plots using configuration."""
        if self.PLOT_CONFIG:
            self._generate_plots_generic()
        else:
            self._generate_plots_legacy()

    def _generate_plots_legacy(self) -> None:
        """
        Legacy plot generation method for backwards compatibility.

        Override this in subclasses that don't use configuration.
        """
        raise NotImplementedError("Either implement PLOT_CONFIG or override _generate_plots_legacy")

    def _generate_plots_generic(self) -> None:
        """Generate plots using configuration."""
        logger.info(f"Generating plots for {self.boss_name} analysis")

        if not self.results:
            logger.warning("No reports available to generate plots")
            return

        # Sort reports by starttime (newest first)
        sorted_reports = sorted(self.results, key=lambda x: x["starttime"], reverse=True)
        latest_report = sorted_reports[0]

        from datetime import datetime

        report_date = datetime.fromtimestamp(latest_report["starttime"]).strftime("%d.%m.%Y")

        # Get fight counts for current and previous reports
        current_fight_count = len(latest_report.get("fight_ids", []))
        previous_fight_count = len(sorted_reports[1].get("fight_ids", [])) if len(sorted_reports) > 1 else None

        # Generate plots based on configuration
        for plot_config in self.PLOT_CONFIG:
            try:
                self._generate_single_plot(plot_config, report_date, current_fight_count, previous_fight_count)
            except Exception as e:
                logger.error(f"Error generating plot {plot_config.get('title', 'Unknown')}: {e}")
                continue

    def _generate_single_plot(
        self,
        plot_config: dict[str, Any],
        report_date: str,
        current_fight_count: int,
        previous_fight_count: Optional[int],
    ) -> None:
        """
        Generate a single plot based on configuration.

        :param plot_config: Plot configuration dictionary
        :param report_date: Date string for the report
        :param current_fight_count: Number of fights in current report
        :param previous_fight_count: Number of fights in previous report
        """
        import pandas as pd

        from ..plotting.base import NumberPlot, PercentagePlot

        analysis_name = plot_config["analysis_name"]
        plot_type = plot_config["plot_type"]
        title = plot_config["title"]
        value_column = plot_config["value_column"]
        value_column_name = plot_config["value_column_name"]
        name_column = plot_config.get("name_column", "player_name")
        class_column = plot_config.get("class_column", "class")

        # Get analysis data
        current_data, previous_dict = self.find_analysis_data(analysis_name, value_column, name_column)

        df = pd.DataFrame(current_data)

        # Create appropriate plot type
        if plot_type == "NumberPlot":
            plot = NumberPlot(
                title=title,
                date=report_date,
                df=df,
                previous_data=previous_dict,
                value_column=value_column,
                value_column_name=value_column_name,
                name_column=name_column,
                class_column=class_column,
                current_fight_count=current_fight_count,
                previous_fight_count=previous_fight_count,
            )
        elif plot_type == "PercentagePlot":
            plot = PercentagePlot(
                title=title,
                date=report_date,
                df=df,
                previous_data=previous_dict,
                value_column=value_column,
                value_column_name=value_column_name,
                name_column=name_column,
                class_column=class_column,
            )
        else:
            raise ValueError(f"Unknown plot type: {plot_type}")

        plot.save()
        logger.debug(f"Generated {plot_type} for {title}")
