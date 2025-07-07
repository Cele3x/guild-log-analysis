#!/usr/bin/env python3
"""Command-line interface for Guild Log Analysis."""

import argparse
import logging
import sys

from .analysis.registry import get_registered_bosses
from .config.logging_config import setup_logging
from .main import GuildLogAnalyzer

logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the command-line argument parser.

    :returns: Configured ArgumentParser instance
    """
    parser = argparse.ArgumentParser(
        description="Analyze World of Warcraft guild log data from Warcraft Logs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --reports kPJma1QVhABKz4Hr yC1KYmQpv9MbNw4T --boss one_armed_bandit
  %(prog)s --reports report1 report2 --boss one_armed_bandit --progress-plots
  %(prog)s --reports report1 --boss one_armed_bandit --verbose
  %(prog)s --list-bosses
        """,
    )

    # Report codes (required unless listing bosses)
    parser.add_argument(
        "--reports",
        "-r",
        nargs="+",
        help="Warcraft Logs report codes to analyze (e.g., kPJma1QVhABKz4Hr)",
        metavar="REPORT_CODE",
    )

    # Boss selection (required unless listing bosses)
    parser.add_argument(
        "--boss",
        "-b",
        help="Boss encounter to analyze (use --list-bosses to see available options)",
        metavar="BOSS_NAME",
    )

    # Progress plots flag (disabled by default)
    parser.add_argument(
        "--progress-plots",
        "-p",
        action="store_true",
        help="Generate progress plots showing trends over time",
        default=False,
    )

    # List available bosses
    parser.add_argument(
        "--list-bosses",
        "-l",
        action="store_true",
        help="List available boss encounters and exit",
    )

    # Verbose logging
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Enable verbose logging output",
    )

    # Debug logging
    parser.add_argument(
        "--debug",
        "-d",
        action="store_true",
        help="Enable debug logging output",
    )

    # Output directory
    parser.add_argument(
        "--output-dir",
        "-o",
        help="Output directory for plots and results (default: output)",
        metavar="DIR",
        default="output",
    )

    return parser


def list_available_bosses() -> None:
    """List all available boss encounters."""
    bosses = get_registered_bosses()
    if not bosses:
        print("No boss encounters are currently registered.")
        return

    print("Available boss encounters:")
    for boss_name, boss_class in bosses.items():
        # Get boss display name if available
        try:
            instance = boss_class(None)  # Create with None client for info only
            display_name = getattr(instance, "boss_name", boss_name.replace("_", " ").title())
            print(f"  {boss_name:20} - {display_name}")
        except Exception:
            print(f"  {boss_name:20} - {boss_name.replace('_', ' ').title()}")


def setup_logging_level(verbose: bool, debug: bool) -> None:
    """
    Configure logging level based on command-line arguments.

    :param verbose: Enable verbose logging
    :param debug: Enable debug logging
    """
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)
    elif verbose:
        logging.getLogger().setLevel(logging.INFO)
    else:
        logging.getLogger().setLevel(logging.WARNING)


def validate_args(args: argparse.Namespace) -> bool:
    """
    Validate command-line arguments.

    :param args: Parsed command-line arguments
    :returns: True if arguments are valid, False otherwise
    """
    # If listing bosses, no other arguments are required
    if args.list_bosses:
        return True

    # Both reports and boss are required for analysis
    if not args.reports:
        print("Error: --reports is required unless using --list-bosses", file=sys.stderr)
        return False

    if not args.boss:
        print("Error: --boss is required unless using --list-bosses", file=sys.stderr)
        return False

    # Validate boss name
    available_bosses = get_registered_bosses()
    if args.boss not in available_bosses:
        print(f"Error: Unknown boss '{args.boss}'", file=sys.stderr)
        print(f"Available bosses: {', '.join(available_bosses.keys())}", file=sys.stderr)
        return False

    return True


def run_analysis(args: argparse.Namespace) -> None:
    """
    Run the analysis with the provided arguments.

    :param args: Parsed command-line arguments
    """
    logger.info(f"Starting analysis for {args.boss} with {len(args.reports)} reports")

    # Initialize analyzer (uses .env variables for authentication)
    analyzer = GuildLogAnalyzer()

    # Get the analyze method for the specified boss
    analyze_method_name = f"analyze_{args.boss}"
    if not hasattr(analyzer, analyze_method_name):
        raise ValueError(f"Boss '{args.boss}' is not properly registered")

    analyze_method = getattr(analyzer, analyze_method_name)

    # Run analysis
    logger.info(f"Running analysis for {args.boss}...")
    analyze_method(args.reports)
    logger.info("Analysis completed successfully")

    # Generate plots (always enabled)
    plot_method_name = f"generate_{args.boss}_plots"
    if hasattr(analyzer, plot_method_name):
        plot_method = getattr(analyzer, plot_method_name)
        logger.info("Generating plots...")
        plot_method(include_progress_plots=args.progress_plots)

        if args.progress_plots:
            logger.info("Plot generation (including progress plots) completed successfully")
        else:
            logger.info("Plot generation completed successfully")
    else:
        logger.warning(f"Plot generation method {plot_method_name} not found")


def main() -> None:
    """CLI entry point for the application."""
    parser = create_parser()
    args = parser.parse_args()

    # Handle list bosses command (no logging needed)
    if args.list_bosses:
        list_available_bosses()
        return

    # Set up logging for actual analysis operations
    setup_logging()
    setup_logging_level(args.verbose, args.debug)

    # Validate arguments
    if not validate_args(args):
        sys.exit(1)

    try:
        run_analysis(args)
        logger.info("All operations completed successfully")
    except KeyboardInterrupt:
        logger.info("Operation cancelled by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Operation failed: {e}")
        if args.debug:
            logger.exception("Full traceback:")
        sys.exit(1)


if __name__ == "__main__":
    main()
