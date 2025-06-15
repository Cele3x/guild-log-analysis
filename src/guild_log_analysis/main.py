"""
Main application module for Guild Log Analysis.

This module provides a simple interface for analyzing guild logs
without complex logic implementation.
"""

import logging
from typing import Any, Dict

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
        self.analyses: Dict[str, Any] = {}
        logger.debug("API client initialized successfully")

    def analyze_one_armed_bandit(self, report_codes: list) -> None:
        """
        Analyze One-Armed Bandit encounters.

        :param report_codes: List of Warcraft Logs report codes to analyze
        """
        from .analysis.bosses.one_armed_bandit import OneArmedBanditAnalysis

        analysis = OneArmedBanditAnalysis(self.api_client)
        logger.info(f"Initialized One-Armed Bandit analysis for {len(report_codes)} reports")
        analysis.analyze(report_codes)
        self.analyses["one_armed_bandit"] = analysis

    def generate_one_armed_bandit_plots(self) -> None:
        """Generate plots for One-Armed Bandit analysis."""
        if "one_armed_bandit" not in self.analyses:
            logger.warning("No One-Armed Bandit analysis found. Run analyze_one_armed_bandit() first.")
            return

        self.analyses["one_armed_bandit"].generate_plots()


def main() -> None:
    """Run the main entry point for the application."""
    # Set up logging for the main function
    setup_logging()

    # Example usage - replace with your actual report codes
    analyzer = GuildLogAnalyzer()

    # Example report codes (replace with actual ones)
    report_codes = ["yC1KYmQpv9MbNw4T", "GzqYMJW3hFHXVdxT"]  # 05.06.  # 12.06.

    try:
        # Analyze One-Armed Bandit encounters
        analyzer.analyze_one_armed_bandit(report_codes)

        # Generate plots
        analyzer.generate_one_armed_bandit_plots()

        logger.info("Analysis completed successfully")

    except Exception as e:
        logger.error(f"Analysis failed: {e}")
        raise


if __name__ == "__main__":
    main()
