"""Test Chimaerus boss analysis."""

import pytest

from src.guild_log_analysis.analysis.bosses.chimaerus import (
    ChimaerusAnalysis,
)


class TestChimaerusAnalysis:
    """Test suite for ChimaerusAnalysis."""

    @pytest.fixture
    def analysis(self, mock_api_client):
        """
        Create ChimaerusAnalysis instance for testing.

        :param mock_api_client: Mock API client fixture
        :returns: ChimaerusAnalysis instance
        """
        return ChimaerusAnalysis(mock_api_client)

    def test_init(self, analysis):
        """Test initialization."""
        assert analysis.boss_name == "Chimaerus"
        assert analysis.encounter_id == 3306
        assert analysis.difficulty == 5

    def test_config_structure(self, analysis):
        """Test CONFIG structure."""
        assert len(analysis.CONFIG) > 0

        # Check that all configs have required structure
        for config in analysis.CONFIG:
            assert "name" in config
            assert "analysis" in config
            assert "plot" in config
            assert "type" in config["analysis"]
            assert "type" in config["plot"]

    def test_dissonance_damage_config(self, analysis):
        """Test Dissonance damage analysis configuration."""
        config = next(
            (c for c in analysis.CONFIG if c["name"] == "Dissonance Damage"),
            None,
        )
        assert config is not None
        assert config["analysis"]["type"] == "table_data"
        assert config["analysis"]["data_type"] == "DamageTaken"
        assert config["analysis"]["ability_ids"] == [1267201, 1268666]
        assert config["analysis"]["wipe_cutoff"] == 4
        assert config["plot"]["type"] == "NumberPlot"
        assert config["plot"]["column_key_1"] == "damage_taken"
        assert config["plot"]["column_header_2"] == "Damage"
