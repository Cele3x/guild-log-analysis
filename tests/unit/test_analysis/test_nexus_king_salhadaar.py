"""Test Nexus-King Salhadaar boss analysis."""

import pytest

from src.guild_log_analysis.analysis.bosses.nexus_king_salhadaar import (
    NexusKingSalhadaarAnalysis,
)


class TestNexusKingSalhadaarAnalysis:
    """Test suite for NexusKingSalhadaarAnalysis."""

    @pytest.fixture
    def analysis(self, mock_api_client):
        """
        Create NexusKingSalhadaarAnalysis instance for testing.

        :param mock_api_client: Mock API client fixture
        :returns: NexusKingSalhadaarAnalysis instance
        """
        return NexusKingSalhadaarAnalysis(mock_api_client)

    def test_init(self, analysis):
        """Test initialization."""
        assert analysis.boss_name == "Nexus-King Salhadaar"
        assert analysis.encounter_id == 3134
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

    def test_besiege_deaths_config(self, analysis):
        """Test Besiege deaths analysis configuration."""
        config = next(
            (c for c in analysis.CONFIG if c["name"] == "Deaths from Besiege"),
            None,
        )
        assert config is not None
        assert config["analysis"]["type"] == "table_data"
        assert config["analysis"]["data_type"] == "Deaths"
        assert config["analysis"]["ability_id"] == 1227472
        assert config["analysis"]["wipe_cutoff"] == 5
        assert config["plot"]["type"] == "NumberPlot"
        assert config["plot"]["column_key_1"] == "deaths"
        assert config["plot"]["column_header_2"] == "Deaths"

    def test_missed_ghosts_config(self, analysis):
        """Test Missed Ghosts analysis configuration."""
        config = next(
            (c for c in analysis.CONFIG if c["name"] == "Missed Ghosts"),
            None,
        )
        assert config is not None
        assert config["analysis"]["type"] == "events"
        assert config["analysis"]["data_type"] == "Debuffs"
        assert config["analysis"]["ability_id"] == 1224737
        assert config["analysis"]["event_types"] == ["applydebuff", "applydebuffstack"]
        assert config["analysis"]["pull_ignore_time_ms"] == 15000
        assert config["analysis"]["wipe_cutoff"] == 0
        assert config["plot"]["type"] == "NumberPlot"
        assert config["plot"]["column_key_1"] == "hit_count"
        assert config["plot"]["column_header_2"] == "Missed Ghosts"
