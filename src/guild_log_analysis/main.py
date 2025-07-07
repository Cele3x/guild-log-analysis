"""
Main application module for Guild Log Analysis.

This module provides a simple interface for analyzing guild logs
without complex logic implementation.
"""

import importlib
import logging
import pkgutil
from typing import Any

from . import analysis
from .analysis.registry import get_registered_bosses
from .api.auth import get_access_token
from .api.client import WarcraftLogsAPIClient
from .config.logging_config import setup_logging

logger = logging.getLogger(__name__)


class GuildLogAnalyzer:
    """
    Simple analyzer for guild log data.

    This class provides a basic interface for running boss analyses
    without implementing complex logic in the main module.
    """

    def __init__(self, access_token: str = None) -> None:
        """
        Initialize the guild log analyzer.

        :param access_token: Warcraft Logs API access token (optional, will use OAuth flow if not provided)
        """
        if access_token:
            # Use provided token
            token = access_token
            logger.info("Using provided access token")
        else:
            # Use OAuth flow to get token
            logger.info("No access token provided, getting token...")
            token = get_access_token()

        self.api_client = WarcraftLogsAPIClient(access_token=token)
        self.analyses: dict[str, Any] = {}
        logger.debug("API client initialized successfully")

        # Auto-register boss analysis methods
        self._register_boss_analyses()

    def _register_boss_analyses(self) -> None:
        """Automatically register all boss analysis classes from the registry."""
        # Import all boss modules to ensure they're registered
        self._import_boss_modules()

        registered_bosses = get_registered_bosses()
        logger.info(f"Registering {len(registered_bosses)} boss analyses")

        for boss_name, boss_class in registered_bosses.items():
            # Create analyze_<boss_name> method
            analyze_method_name = f"analyze_{boss_name}"
            if not hasattr(self, analyze_method_name):
                setattr(
                    self,
                    analyze_method_name,
                    self._create_analyze_method(boss_name, boss_class),
                )
                logger.debug(f"Created method: {analyze_method_name}")

            # Create generate_<boss_name>_plots method
            plots_method_name = f"generate_{boss_name}_plots"
            if not hasattr(self, plots_method_name):
                setattr(self, plots_method_name, self._create_plot_method(boss_name))
                logger.debug(f"Created method: {plots_method_name}")

    def _import_boss_modules(self) -> None:
        """Import all boss analysis modules to ensure they're registered."""
        # Import the bosses package
        bosses_package = f"{analysis.__name__}.bosses"

        try:
            bosses_module = importlib.import_module(bosses_package)

            # Import all modules in the bosses package
            for _, module_name, _ in pkgutil.iter_modules(bosses_module.__path__):
                if module_name != "__init__":
                    full_module_name = f"{bosses_package}.{module_name}"
                    try:
                        importlib.import_module(full_module_name)
                        logger.debug(f"Imported boss module: {full_module_name}")
                    except Exception as e:
                        logger.warning(f"Failed to import boss module {full_module_name}: {e}")
        except Exception as e:
            logger.warning(f"Failed to import bosses package: {e}")

    def _create_analyze_method(self, boss_name: str, boss_class):
        """
        Create an analyze method for a specific boss.

        :param boss_name: The name identifier for the boss
        :param boss_class: The boss analysis class
        :return: The analyze method function
        """

        def analyze_method(report_codes: list[str]) -> None:
            analysis = boss_class(self.api_client)
            logger.info(f"Initialized {boss_name} analysis for {len(report_codes)} reports")
            analysis.analyze(report_codes)
            self.analyses[boss_name] = analysis

        # Set proper method name and docstring
        analyze_method.__name__ = f"analyze_{boss_name}"
        analyze_method.__doc__ = (
            f"Analyze {boss_name} encounters.\n\n:param report_codes: List of Warcraft Logs report codes to analyze"
        )

        return analyze_method

    def _create_plot_method(self, boss_name: str):
        """
        Create a plot generation method for a specific boss.

        :param boss_name: The name identifier for the boss
        :return: The plot generation method function
        """

        def generate_plots_method(include_progress_plots: bool = True) -> None:
            if boss_name not in self.analyses:
                logger.warning(f"No {boss_name} analysis found. Run analyze_{boss_name}() first.")
                return

            self.analyses[boss_name].generate_plots(include_progress_plots=include_progress_plots)

        # Set proper method name and docstring
        generate_plots_method.__name__ = f"generate_{boss_name}_plots"
        generate_plots_method.__doc__ = (
            f"Generate plots for {boss_name} analysis.\n\n"
            ":param include_progress_plots: Whether to generate progress plots (default: True)"
        )

        return generate_plots_method


def main() -> None:
    """Run the main entry point for the application."""
    # Set up logging for the main function
    setup_logging()

    # Example usage - replace with your actual report codes
    analyzer = GuildLogAnalyzer()

    # Example report codes (replace with actual ones)
    report_codes = [
        "kPJma1QVhABKz4Hr",  # 25.05.
        "yC1KYmQpv9MbNw4T",  # 05.06.
        "GzqYMJW3hFHXVdxT",  # 12.06.
        "BTYHxq1QC6wdVjrv",  # 15.06.
        "29ykfGtYXWw6Zngb",  # 19.06.
        "jYAM7vCZ3PmzGNWg",  # 22.06.
        "XHwhTRPpgqrMvj6m",  # 26.06.
        "8xyNr6Ak3PmLHDK9",  # 29.06.
        "JgqDctCB8v9XryVQ",  # 03.07.
        "trY9VZXfGmw1KCpF",  # 06.07. Kill + Sprocketmonger
    ]

    try:
        # Analyze One-Armed Bandit encounters
        analyzer.analyze_one_armed_bandit(report_codes)

        # Generate plots (including progress plots)
        analyzer.generate_one_armed_bandit_plots(include_progress_plots=True)

        logger.info("Analysis completed successfully")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()
