"""Test example boss analysis with unified CONFIG."""

import pytest

from src.guild_log_analysis.analysis.bosses.example_boss import ExampleBossAnalysis
from src.guild_log_analysis.config.constants import PlayerRoles


class TestExampleBossAnalysis:
    """Test suite for ExampleBossAnalysis."""

    @pytest.fixture
    def analysis(self, mock_api_client):
        """Create ExampleBossAnalysis instance for testing."""
        return ExampleBossAnalysis(mock_api_client)

    def test_init(self, analysis):
        """Test initialization."""
        assert analysis.boss_name == "Example Boss"
        assert analysis.encounter_id == 1234
        assert analysis.difficulty == 5

    def test_config_structure(self, analysis):
        """Test CONFIG structure."""
        assert len(analysis.CONFIG) == 8

        # Check that all configs have required structure
        for config in analysis.CONFIG:
            assert "name" in config
            assert "analysis" in config
            assert "plot" in config
            assert "type" in config["analysis"]
            assert "type" in config["plot"]

    def test_interrupts_config(self, analysis):
        """Test interrupts analysis configuration."""
        config = next((c for c in analysis.CONFIG if c["name"] == "Boss Interrupts"), None)
        assert config is not None
        assert config["analysis"]["type"] == "interrupts"
        assert config["analysis"]["ability_id"] == 12345
        assert config["roles"] == [PlayerRoles.DPS]
        assert config["plot"]["type"] == "NumberPlot"
        assert config["plot"]["column_header_2"] == "Interrupts"

    def test_debuff_uptime_config(self, analysis):
        """Test debuff uptime configuration."""
        config = next((c for c in analysis.CONFIG if c["name"] == "Debuff Uptime"), None)
        assert config is not None
        assert config["analysis"]["type"] == "debuff_uptime"
        assert config["analysis"]["ability_id"] == 67890.0
        assert "roles" not in config  # All roles
        assert config["plot"]["type"] == "PercentagePlot"
        assert config["plot"]["column_header_2"] == "Uptime %"

    def test_damage_to_actor_config(self, analysis):
        """Test damage to actor configuration."""
        config = next((c for c in analysis.CONFIG if c["name"] == "Add Damage"), None)
        assert config is not None
        assert config["analysis"]["type"] == "damage_to_actor"
        assert config["analysis"]["target_game_id"] == 11111
        assert config["roles"] == [PlayerRoles.TANK, PlayerRoles.DPS]
        assert config["plot"]["type"] == "NumberPlot"
        assert config["plot"]["column_header_2"] == "Damage"

    def test_hit_count_plot_config(self, analysis):
        """Test HitCountPlot configuration."""
        config = next((c for c in analysis.CONFIG if c["name"] == "Damage Taken from Fire"), None)
        assert config is not None
        assert config["analysis"]["type"] == "damage_taken_from_ability"
        assert config["analysis"]["ability_id"] == 33333.0
        assert config["plot"]["type"] == "HitCountPlot"
        assert config["plot"]["column_header_2"] == "Hits"
        assert config["plot"]["column_header_3"] == "Damage Taken"

    def test_role_filtering(self, analysis):
        """Test role filtering in configurations."""
        # DPS only
        dps_configs = [c for c in analysis.CONFIG if c.get("roles") == [PlayerRoles.DPS]]
        assert len(dps_configs) == 2
        dps_names = [c["name"] for c in dps_configs]
        assert "Boss Interrupts" in dps_names
        assert "High Tolerance Interrupts" in dps_names

        # Healer only
        healer_configs = [c for c in analysis.CONFIG if c.get("roles") == [PlayerRoles.HEALER]]
        assert len(healer_configs) == 1
        assert healer_configs[0]["name"] == "Healing Done"

        # Tank only
        tank_configs = [c for c in analysis.CONFIG if c.get("roles") == [PlayerRoles.TANK]]
        assert len(tank_configs) == 1
        assert tank_configs[0]["name"] == "Absorbed Damage"

        # All roles (no role restriction)
        all_roles_configs = [c for c in analysis.CONFIG if "roles" not in c]
        assert len(all_roles_configs) == 3
        names = [c["name"] for c in all_roles_configs]
        assert "Debuff Uptime" in names
        assert "Damage Taken from Fire" in names
        assert "Low Tolerance Debuff" in names

    def test_filter_expressions(self, analysis):
        """Test filter expressions in configurations."""
        config = next((c for c in analysis.CONFIG if c["name"] == "Absorbed Damage"), None)
        assert config is not None
        assert config["analysis"]["filter_expression"] == "absorbedDamage > 0"

    def test_wipe_cutoff_overrides(self, analysis):
        """Test wipe cutoff override configurations."""
        # Test high tolerance interrupts (wipe cutoff = 10 deaths)
        high_tolerance_config = next((c for c in analysis.CONFIG if c["name"] == "High Tolerance Interrupts"), None)
        assert high_tolerance_config is not None
        assert high_tolerance_config["analysis"]["wipe_cutoff"] == 10
        assert high_tolerance_config["analysis"]["type"] == "interrupts"

        # Test low tolerance debuff (wipe cutoff = 2 deaths)
        low_tolerance_config = next((c for c in analysis.CONFIG if c["name"] == "Low Tolerance Debuff"), None)
        assert low_tolerance_config is not None
        assert low_tolerance_config["analysis"]["wipe_cutoff"] == 2
        assert low_tolerance_config["analysis"]["type"] == "debuff_uptime"

        # Ensure some configs don't have explicit wipe cutoff (will use default)
        default_configs = [c for c in analysis.CONFIG if "wipe_cutoff" not in c["analysis"]]
        assert len(default_configs) > 0  # Should have configs using default wipe cutoff

    def test_custom_titles(self, analysis):
        """Test custom plot titles."""
        # Test custom title
        config = next((c for c in analysis.CONFIG if c["name"] == "Boss Interrupts"), None)
        assert config is not None
        assert config["plot"]["title"] == "Boss Interrupts (DPS Only)"

        # Test default title (should use name)
        config = next((c for c in analysis.CONFIG if c["name"] == "Absorbed Damage"), None)
        assert config is not None
        # Should not have custom title, will default to name
        assert "title" not in config["plot"] or config["plot"].get("title") == config["name"]
