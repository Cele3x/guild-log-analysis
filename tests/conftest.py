"""
Test configuration and fixtures for Guild Log Analysis.

This module provides common test fixtures and configuration
used across all test modules.
"""

import os
from unittest.mock import Mock

import pytest

from src.guild_log_analysis.api import WarcraftLogsAPIClient


@pytest.fixture(scope="session", autouse=True)
def configure_test_environment():
    """
    Configure test environment variables.

    Sets up test environment to use tests/output/ directory for all test outputs
    including plots, cache, and logs. This isolates test data from production data.
    """
    # Set output directory for tests to keep all test outputs in tests/output/
    os.environ["OUTPUT_DIRECTORY"] = "tests"

    # Ensure test output directories exist
    test_output_dirs = ["tests/output/plots", "tests/output/cache", "tests/output/logs"]

    for directory in test_output_dirs:
        os.makedirs(directory, exist_ok=True)


@pytest.fixture
def mock_api_client():
    """Create a mock API client for testing."""
    client = Mock(spec=WarcraftLogsAPIClient)
    return client


@pytest.fixture
def sample_player_data():
    """Sample player data for testing."""
    return [
        {"player_name": "TestPlayer1", "class": "warrior", "role": "tank"},
        {"player_name": "TestPlayer2", "class": "priest", "role": "healer"},
        {"player_name": "TestPlayer3", "class": "mage", "role": "dps"},
    ]


@pytest.fixture
def sample_fight_data():
    """Sample fight data for testing."""
    return {
        "data": {
            "reportData": {
                "report": {
                    "fights": [
                        {
                            "id": 1,
                            "encounterID": 2917,  # One-Armed Bandit
                            "difficulty": 5,  # Mythic
                            "kill": True,
                            "startTime": 1000,
                            "endTime": 300000,
                            "name": "One-Armed Bandit",
                        },
                        {
                            "id": 2,
                            "encounterID": 2917,
                            "difficulty": 5,
                            "kill": False,
                            "startTime": 400000,
                            "endTime": 600000,
                            "name": "One-Armed Bandit",
                        },
                    ]
                }
            }
        }
    }


@pytest.fixture
def sample_damage_data():
    """Sample damage data for testing."""
    return {
        "data": {
            "reportData": {
                "report": {
                    "table": {
                        "data": {
                            "entries": [
                                {
                                    "name": "TestPlayer1",
                                    "total": 1000000,
                                    "type": "Player",
                                },
                                {
                                    "name": "TestPlayer2",
                                    "total": 800000,
                                    "type": "Player",
                                },
                            ]
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_events_data():
    """Sample events data for testing."""
    return {
        "data": {
            "reportData": {
                "report": {
                    "events": {
                        "data": [
                            {
                                "timestamp": 1500,
                                "type": "cast",
                                "sourceID": 1,
                                "targetID": 2,
                                "abilityGameID": 12345,
                            },
                            {
                                "timestamp": 2500,
                                "type": "damage",
                                "sourceID": 1,
                                "targetID": 3,
                                "amount": 50000,
                            },
                        ]
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_debuff_data():
    """Sample debuff data for testing."""
    return {
        "data": {
            "reportData": {
                "report": {
                    "table": {
                        "data": {
                            "auras": [
                                {
                                    "name": "High Roller",
                                    "guid": 123456,
                                    "totalUptime": 45000,  # 45 seconds
                                    "totalUses": 3,
                                }
                            ]
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_interrupts_data():
    """Sample interrupts data for testing."""
    return {
        "data": {
            "reportData": {
                "report": {
                    "events": {
                        "data": [
                            {
                                "timestamp": 1500,
                                "type": "interrupt",
                                "sourceID": 1,
                                "targetID": 2,
                                "abilityGameID": 12345,
                                "extraAbilityGameID": 67890,
                            },
                            {
                                "timestamp": 2500,
                                "type": "interrupt",
                                "sourceID": 2,
                                "targetID": 3,
                                "abilityGameID": 12345,
                                "extraAbilityGameID": 67890,
                            },
                        ]
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_analysis_results():
    """Mock analysis results for testing."""
    return {
        "overload_interrupts": {
            "results": [
                {
                    "name": "Overload! Interrupts",
                    "data": [
                        {
                            "player_name": "TestPlayer1",
                            "class": "warrior",
                            "role": "tank",
                            "interrupts": 5,
                        },
                        {
                            "player_name": "TestPlayer2",
                            "class": "priest",
                            "role": "healer",
                            "interrupts": 2,
                        },
                    ],
                }
            ]
        },
        "high_roller_uptime": {
            "results": [
                {
                    "name": "Overload! Interrupts",
                    "data": [
                        {
                            "player_name": "TestPlayer1",
                            "class": "warrior",
                            "role": "tank",
                            "interrupts": 3,
                        },
                        {
                            "player_name": "TestPlayer2",
                            "class": "priest",
                            "role": "healer",
                            "interrupts": 1,
                        },
                    ],
                }
            ]
        },
    }


@pytest.fixture
def mock_settings():
    """Mock settings for testing."""
    settings = Mock()
    settings.warcraft_logs_access_token = "test_token"
    settings.warcraft_logs_client_id = "test_client_id"
    settings.api_url = "https://www.warcraftlogs.com/api/v2/client"
    settings.auth_url = "https://www.warcraftlogs.com/oauth/authorize"
    settings.token_url = "https://www.warcraftlogs.com/oauth/token"
    settings.cache_directory = "/tmp/test_cache"
    return settings


@pytest.fixture
def sample_api_response():
    """Sample API response for analysis tests."""
    return {
        "data": {
            "reportData": {
                "report": {
                    "startTime": 1640995200000,
                    "fights": [
                        {
                            "id": 1,
                            "encounterID": 3014,  # One-Armed Bandit
                            "difficulty": 5,  # Mythic
                            "kill": True,
                            "startTime": 0,
                            "endTime": 300000,
                            "name": "One-Armed Bandit",
                        },
                        {
                            "id": 2,
                            "encounterID": 3014,
                            "difficulty": 5,
                            "kill": False,
                            "startTime": 400000,
                            "endTime": 700000,
                            "name": "One-Armed Bandit",
                        },
                    ],
                }
            }
        }
    }


@pytest.fixture
def sample_player_details_response():
    """Sample player details response for analysis tests."""
    return {
        "data": {
            "reportData": {
                "report": {
                    "playerDetails": {
                        "data": {
                            "playerDetails": {
                                "tanks": [
                                    {
                                        "name": "TestPlayer1",
                                        "id": 1,
                                        "type": "Warrior",
                                    }
                                ],
                                "healers": [
                                    {
                                        "name": "TestPlayer2",
                                        "id": 2,
                                        "type": "Priest",
                                    }
                                ],
                                "dps": [
                                    {
                                        "name": "TestPlayer3",
                                        "id": 3,
                                        "type": "Mage",
                                    }
                                ],
                            }
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_analysis_results():
    """Sample analysis results for testing."""
    return [
        {
            "starttime": 1640995200.0,
            "reportCode": "latest_report",
            "analysis": [
                {
                    "name": "Overload! Interrupts",
                    "data": [
                        {
                            "player_name": "TestPlayer1",
                            "class": "warrior",
                            "role": "tank",
                            "interrupts": 5,
                        },
                        {
                            "player_name": "TestPlayer2",
                            "class": "priest",
                            "role": "healer",
                            "interrupts": 2,
                        },
                    ],
                }
            ],
        },
        {
            "starttime": 1640995100.0,
            "reportCode": "previous_report",
            "analysis": [
                {
                    "name": "Overload! Interrupts",
                    "data": [
                        {
                            "player_name": "TestPlayer1",
                            "class": "warrior",
                            "role": "tank",
                            "interrupts": 3,
                        },
                        {
                            "player_name": "TestPlayer2",
                            "class": "priest",
                            "role": "healer",
                            "interrupts": 1,
                        },
                    ],
                }
            ],
        },
    ]


@pytest.fixture
def sample_actors_response():
    """Sample actors response for damage analysis tests."""
    return {
        "data": {
            "reportData": {
                "report": {
                    "masterData": {
                        "actors": [
                            {
                                "id": 100,
                                "name": "Premium Dynamite Booties",
                                "gameID": 231027,
                                "type": "NPC",
                                "subType": "Enemy",
                            }
                        ]
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_damage_response():
    """Sample damage response for damage analysis tests."""
    return {
        "data": {
            "reportData": {
                "report": {
                    "table": {
                        "data": {
                            "entries": [
                                {
                                    "name": "TestPlayer1",
                                    "total": 1000000,
                                    "type": "Player",
                                },
                                {
                                    "name": "TestPlayer2",
                                    "total": 800000,
                                    "type": "Player",
                                },
                                {
                                    "name": "TestPlayer3",
                                    "total": 600000,
                                    "type": "Player",
                                },
                            ]
                        }
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_players_data():
    """Sample players data for testing."""
    return [
        {"name": "TestPlayer1", "type": "warrior", "role": "tank", "id": 1},
        {"name": "TestPlayer2", "type": "priest", "role": "healer", "id": 2},
        {"name": "TestPlayer3", "type": "mage", "role": "dps", "id": 3},
    ]


@pytest.fixture
def sample_interrupt_events():
    """Sample interrupt events for testing."""
    return {
        "data": {
            "reportData": {
                "report": {
                    "events": {
                        "data": [
                            {
                                "timestamp": 1500,
                                "type": "interrupt",
                                "sourceID": 1,
                                "targetID": 2,
                                "abilityGameID": 460582,
                                "targetName": "TestPlayer1",
                            },
                            {
                                "timestamp": 2500,
                                "type": "interrupt",
                                "sourceID": 2,
                                "targetID": 3,
                                "abilityGameID": 460582,
                                "targetName": "TestPlayer2",
                            },
                        ]
                    }
                }
            }
        }
    }


@pytest.fixture
def sample_debuff_events():
    """Sample debuff events for testing."""
    return {
        "data": {
            "reportData": {
                "report": {
                    "events": {
                        "data": [
                            {
                                "timestamp": 1000,
                                "type": "applydebuff",
                                "targetID": 1,
                                "abilityGameID": 460444,
                                "targetName": "TestPlayer1",
                            },
                            {
                                "timestamp": 3000,
                                "type": "removedebuff",
                                "targetID": 1,
                                "abilityGameID": 460444,
                                "targetName": "TestPlayer1",
                            },
                            {
                                "timestamp": 2000,
                                "type": "applydebuff",
                                "targetID": 2,
                                "abilityGameID": 460444,
                                "targetName": "TestPlayer2",
                            },
                        ]
                    }
                }
            }
        }
    }


@pytest.fixture
def mock_registry_boss():
    """Create a mock boss for registry testing."""
    from src.guild_log_analysis.analysis.base import BossAnalysisBase

    class MockRegistryBoss(BossAnalysisBase):
        def __init__(self, api_client):
            super().__init__(api_client)
            self.boss_name = "Mock Boss"
            self.encounter_id = 9999
            self.difficulty = 5

        ANALYSIS_CONFIG = [{"name": "Mock Analysis", "type": "interrupts", "ability_id": 12345}]

        PLOT_CONFIG = [
            {
                "analysis_name": "Mock Analysis",
                "type": "NumberPlot",
                "title": "Mock Plot",
                "column_key_1": "test_value",
                "column_header_1": "Test",
            }
        ]

    return MockRegistryBoss


@pytest.fixture
def sample_configuration_analysis_results():
    """Sample analysis results for configuration-based testing."""
    return [
        {
            "starttime": 1640995200.0,
            "reportCode": "config_report",
            "analysis": [
                {
                    "name": "Test Interrupts",
                    "data": [
                        {"player_name": "Player1", "class": "warrior", "role": "tank", "interrupts": 3},
                        {"player_name": "Player2", "class": "priest", "role": "healer", "interrupts": 1},
                    ],
                },
                {
                    "name": "Test Damage",
                    "data": [
                        {"player_name": "Player1", "class": "warrior", "role": "tank", "test_damage": 750000},
                        {"player_name": "Player2", "class": "priest", "role": "healer", "test_damage": 450000},
                    ],
                },
            ],
            "fight_ids": {1, 2, 3},
        }
    ]
