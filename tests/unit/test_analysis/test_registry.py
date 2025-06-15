"""Tests for the analysis registry system."""

from src.guild_log_analysis.analysis.registry import (
    clear_registry,
    get_registered_bosses,
    register_boss,
)


class TestAnalysisRegistry:
    """Test cases for the analysis registry system."""

    def setup_method(self):
        """Clear registry before each test."""
        clear_registry()

    def teardown_method(self):
        """Clear registry after each test."""
        clear_registry()

    def test_register_boss_decorator(self):
        """Test boss registration with decorator."""

        @register_boss("test_boss")
        class TestBossAnalysis:
            pass

        registered = get_registered_bosses()
        assert "test_boss" in registered
        assert registered["test_boss"] == TestBossAnalysis

    def test_register_multiple_bosses(self):
        """Test registering multiple boss analyses."""

        @register_boss("boss_one")
        class BossOneAnalysis:
            pass

        @register_boss("boss_two")
        class BossTwoAnalysis:
            pass

        registered = get_registered_bosses()
        assert len(registered) == 2
        assert "boss_one" in registered
        assert "boss_two" in registered
        assert registered["boss_one"] == BossOneAnalysis
        assert registered["boss_two"] == BossTwoAnalysis

    def test_register_boss_overwrites(self):
        """Test that registering with same name overwrites previous registration."""

        @register_boss("duplicate_name")
        class FirstBossAnalysis:
            pass

        @register_boss("duplicate_name")
        class SecondBossAnalysis:
            pass

        registered = get_registered_bosses()
        assert len(registered) == 1
        assert registered["duplicate_name"] == SecondBossAnalysis

    def test_get_registered_bosses_returns_copy(self):
        """Test that get_registered_bosses returns a copy, not the original."""

        @register_boss("test_boss")
        class TestBossAnalysis:
            pass

        registered1 = get_registered_bosses()
        registered2 = get_registered_bosses()

        # Should be different objects but same content
        assert registered1 is not registered2
        assert registered1 == registered2

        # Modifying one shouldn't affect the other
        registered1["new_boss"] = "fake_class"
        assert "new_boss" not in registered2

    def test_clear_registry(self):
        """Test clearing the registry."""

        @register_boss("test_boss")
        class TestBossAnalysis:
            pass

        assert len(get_registered_bosses()) == 1

        clear_registry()

        assert len(get_registered_bosses()) == 0

    def test_register_boss_returns_original_class(self):
        """Test that the decorator returns the original class unchanged."""

        @register_boss("test_boss")
        class TestBossAnalysis:
            test_attribute = "test_value"

            def test_method(self):
                return "test_result"

        # Class should be unchanged
        assert hasattr(TestBossAnalysis, "test_attribute")
        assert TestBossAnalysis.test_attribute == "test_value"
        assert hasattr(TestBossAnalysis, "test_method")

        instance = TestBossAnalysis()
        assert instance.test_method() == "test_result"

    def test_empty_registry_initially(self):
        """Test that registry is empty initially."""
        registered = get_registered_bosses()
        assert len(registered) == 0
        assert registered == {}
