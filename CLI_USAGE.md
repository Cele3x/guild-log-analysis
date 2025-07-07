# Guild Log Analysis CLI

The Guild Log Analysis CLI provides a command-line interface for analyzing World of Warcraft guild logs from Warcraft Logs.

## Installation

After installing the package, you can use the CLI in several ways:

```bash
# If installed via pip
guild-analyze --help

# Using Python module
python -m guild_log_analysis.cli --help

# Using the script directly
./scripts/analyze --help
```

## Basic Usage

### List Available Bosses

```bash
guild-analyze --list-bosses
```

### Analyze Reports

```bash
# Basic analysis with all plots
guild-analyze --reports kPJma1QVhABKz4Hr yC1KYmQpv9MbNw4T --boss one_armed_bandit

# Analysis without progress plots
guild-analyze --reports report1 report2 --boss one_armed_bandit --no-progress-plots

# Analysis only (no plots)
guild-analyze --reports report1 --boss one_armed_bandit --analysis-only

# Verbose output
guild-analyze --reports report1 --boss one_armed_bandit --verbose
```

## Command-Line Arguments

### Required Arguments (unless using `--list-bosses`)

- `--reports`, `-r`: One or more Warcraft Logs report codes
- `--boss`, `-b`: Boss encounter to analyze

### Optional Arguments

- `--progress-plots`, `-p`: Generate progress plots showing trends over time (default: disabled)
- `--list-bosses`, `-l`: List available boss encounters and exit
- `--verbose`, `-v`: Enable verbose logging output
- `--debug`, `-d`: Enable debug logging output
- `--output-dir`, `-o`: Output directory for plots and results (default: output)

## Examples

### Basic Analysis (Regular Plots Only)

```bash
guild-analyze --reports kPJma1QVhABKz4Hr yC1KYmQpv9MbNw4T --boss one_armed_bandit
```

This will:
- Analyze the specified reports for One-Armed Bandit encounters
- Generate regular plots for each encounter
- Save all output to the `output/` directory

### Analysis with Progress Plots

```bash
guild-analyze --reports report1 report2 --boss one_armed_bandit --progress-plots
```

This will generate both regular plots and progress plots showing trends over time.

### Custom Output Directory

```bash
guild-analyze --reports report1 report2 --boss one_armed_bandit --output-dir /path/to/custom/output
```

### Verbose Output for Debugging

```bash
guild-analyze --reports report1 --boss one_armed_bandit --verbose --debug
```

## Authentication

The CLI uses the `.env` file in your project directory for Warcraft Logs API authentication. Ensure your `.env` file contains:

```
CLIENT_ID=your_client_id
REDIRECT_URI=http://localhost:8080/callback
```

## Output

- **Regular plots**: Saved to `output/YYYY-MM-DD/` directory
- **Progress plots**: Saved to `output/multi_line_YYYY-MM-DD_to_YYYY-MM-DD/` directory (when `--progress-plots` is used)
- **Logs**: Saved to `logs/wow_analysis.log`

## Default Behavior

- **Plots**: Regular plots are always generated
- **Progress plots**: Disabled by default (use `--progress-plots` to enable)
- **Output directory**: `output/` (use `--output-dir` to customize)
- **Authentication**: Uses `.env` file credentials

## Error Handling

The CLI provides helpful error messages for common issues:

- Missing required arguments
- Invalid boss names
- Network connectivity issues
- API authentication problems

Use `--verbose` or `--debug` for more detailed error information.
