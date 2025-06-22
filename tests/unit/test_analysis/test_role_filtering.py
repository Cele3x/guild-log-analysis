"""Tests for role-based filtering in analysis and plotting."""

from unittest.mock import Mock

from src.guild_log_analysis.analysis.base import BossAnalysisBase
from src.guild_log_analysis.config.constants import PlayerRoles
from src.guild_log_analysis.utils.helpers import filter_players_by_roles


class TestRoleFiltering:
    """Test cases for role-based filtering functionality."""

    def test_filter_players_by_roles_single_role(self):
        """Test filtering players by a single role."""
        players = [
            {"player_name": "Tank1", "role": "tank", "class": "warrior"},
            {"player_name": "Healer1", "role": "healer", "class": "priest"},
            {"player_name": "DPS1", "role": "dps", "class": "mage"},
            {"player_name": "DPS2", "role": "dps", "class": "rogue"},
        ]

        dps_only = filter_players_by_roles(players, [PlayerRoles.DPS])

        assert len(dps_only) == 2
        assert all(player["role"] == "dps" for player in dps_only)
        assert {player["player_name"] for player in dps_only} == {"DPS1", "DPS2"}

    def test_filter_players_by_roles_multiple_roles(self):
        """Test filtering players by multiple roles."""
        players = [
            {"player_name": "Tank1", "role": "tank", "class": "warrior"},
            {"player_name": "Healer1", "role": "healer", "class": "priest"},
            {"player_name": "DPS1", "role": "dps", "class": "mage"},
            {"player_name": "DPS2", "role": "dps", "class": "rogue"},
        ]

        tank_and_dps = filter_players_by_roles(players, [PlayerRoles.TANK, PlayerRoles.DPS])

        assert len(tank_and_dps) == 3
        assert all(player["role"] in ["tank", "dps"] for player in tank_and_dps)
        assert {player["player_name"] for player in tank_and_dps} == {"Tank1", "DPS1", "DPS2"}

    def test_filter_players_by_roles_empty_list_returns_all(self):
        """Test that empty role list returns all players."""
        players = [
            {"player_name": "Tank1", "role": "tank", "class": "warrior"},
            {"player_name": "Healer1", "role": "healer", "class": "priest"},
            {"player_name": "DPS1", "role": "dps", "class": "mage"},
        ]

        all_players = filter_players_by_roles(players, [])

        assert len(all_players) == 3
        assert all_players == players

    def test_filter_players_by_roles_default_role_assignment(self):
        """Test that players without role get assigned 'dps' by default."""
        players = [
            {"player_name": "Player1", "class": "mage"},  # No role specified
            {"player_name": "Player2", "role": "tank", "class": "warrior"},
        ]

        dps_filtered = filter_players_by_roles(players, [PlayerRoles.DPS])

        assert len(dps_filtered) == 1
        assert dps_filtered[0]["player_name"] == "Player1"

    def test_boss_analysis_filter_players_by_roles_method(self):
        """Test the BossAnalysisBase._filter_players_by_roles method."""
        # Create a mock API client
        mock_api_client = Mock()

        # Create analysis instance
        analysis = BossAnalysisBase(mock_api_client)

        players = [
            {"player_name": "Tank1", "role": "tank", "class": "warrior"},
            {"player_name": "Healer1", "role": "healer", "class": "priest"},
            {"player_name": "DPS1", "role": "dps", "class": "mage"},
        ]

        # Test filtering
        dps_only = analysis._filter_players_by_roles(players, [PlayerRoles.DPS])

        assert len(dps_only) == 1
        assert dps_only[0]["player_name"] == "DPS1"

    def test_analysis_config_role_filtering_structure(self):
        """Test that analysis config can include role filtering."""
        config = {
            "name": "Test Analysis",
            "type": "interrupts",
            "ability_id": 12345,
            "roles": [PlayerRoles.DPS, PlayerRoles.TANK],
        }

        # Verify structure is correct
        assert "roles" in config
        assert config["roles"] == ["dps", "tank"]
        assert PlayerRoles.HEALER not in config["roles"]

    def test_plot_config_role_filtering_structure(self):
        """Test that plot config can include role filtering."""
        config = {
            "analysis_name": "Test Analysis",
            "type": "NumberPlot",
            "title": "Test Plot",
            "column_key_1": "test_value",
            "column_header_1": "Test Value",
            "roles": [PlayerRoles.DPS],
        }

        # Verify structure is correct
        assert "roles" in config
        assert config["roles"] == ["dps"]

    def test_all_role_constants_defined(self):
        """Test that all role constants are properly defined."""
        assert PlayerRoles.TANK == "tank"
        assert PlayerRoles.HEALER == "healer"
        assert PlayerRoles.DPS == "dps"
        assert PlayerRoles.ALL_ROLES == ["tank", "healer", "dps"]

    def test_role_filtering_preserves_other_data(self):
        """Test that role filtering preserves all other player data."""
        players = [
            {
                "player_name": "Player1",
                "role": "dps",
                "class": "mage",
                "interrupts": 5,
                "damage": 1000000,
                "custom_field": "test_value",
            },
            {
                "player_name": "Player2",
                "role": "tank",
                "class": "warrior",
                "interrupts": 2,
                "damage": 500000,
                "custom_field": "another_value",
            },
        ]

        dps_filtered = filter_players_by_roles(players, [PlayerRoles.DPS])

        assert len(dps_filtered) == 1
        player = dps_filtered[0]
        assert player["player_name"] == "Player1"
        assert player["class"] == "mage"
        assert player["interrupts"] == 5
        assert player["damage"] == 1000000
        assert player["custom_field"] == "test_value"

    def test_role_filtering_with_missing_role_field(self):
        """Test role filtering when some players don't have role field."""
        players = [
            {"player_name": "Player1", "class": "mage"},  # No role
            {"player_name": "Player2", "role": "tank", "class": "warrior"},
            {"player_name": "Player3", "role": None, "class": "priest"},  # None role
        ]

        # Players without role or with None role should default to DPS
        dps_filtered = filter_players_by_roles(players, [PlayerRoles.DPS])

        assert len(dps_filtered) == 2
        names = {player["player_name"] for player in dps_filtered}
        assert names == {"Player1", "Player3"}
