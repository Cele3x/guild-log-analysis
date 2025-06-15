# Guild Log Analysis

A comprehensive tool for analyzing World of Warcraft guild logs from Warcraft Logs API.

## Author

**Jonathan Sasse**
Email: jonathan.sasse@outlook.de

## Features

- **Registry-Based Boss Analysis**: Extensible decorator-based system for analyzing different raid bosses
- **Automatic Method Generation**: Boss analyses are automatically registered and methods are generated at runtime
- **Configuration-Driven Analysis**: Define analyses through simple configuration arrays instead of repetitive code
- **One-Armed Bandit Analysis**: Complete analysis for Liberation of Undermine encounters
- **Professional Plotting**: High-quality visualizations with consistent styling
- **API Integration**: Seamless integration with Warcraft Logs GraphQL API
- **Intelligent Caching**: Smart caching system to minimize API calls with automatic rotation
- **Type Safety**: Full type annotations throughout the codebase

## Requirements

- Python 3.13+
- Warcraft Logs API access token

## Installation

### Method 1: Install All Requirements (Recommended)
```bash
# Navigate to your project directory
cd guild-log-analysis

# Install the package in development mode (includes all dependencies)
pip install -e .
```

### Method 2: Install Specific Requirement Sets
```bash
# Base requirements only (for production use)
pip install -r requirements/base.txt

# Development requirements (includes base + dev tools)
pip install -r requirements/dev.txt

# Test requirements (includes base + testing frameworks)
pip install -r requirements/test.txt
```

### Method 3: Using Virtual Environment (Best Practice)
```bash
# Create a virtual environment
python -m venv ~/.virtualenvs/guild-log-analysis

# Activate it (Linux/Mac)
source ~/.virtualenvs/guild-log-analysis/bin/activate
# Or on Windows:
# ~/.virtualenvs/guild-log-analysis/Scripts/activate

# Install the package
pip install -e .
```

**Note**: The project was developed using virtual environment at `/home/jonathan/.virtualenvs/guild-log-analysis`

## Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your Warcraft Logs API credentials:
   ```
   WOW_CLIENT_ID=your_client_id
   WOW_REDIRECT_URI=http://localhost:8080/callback
   ```

## Usage

### Basic Usage

```python
from guild_log_analysis.main import GuildLogAnalyzer

# Initialize analyzer (automatically registers all boss analyses)
analyzer = GuildLogAnalyzer()

# Analyze One-Armed Bandit encounters (method auto-generated)
analyzer.analyze_one_armed_bandit(["report_code1", "report_code2"])

# Generate plots (method auto-generated)
analyzer.generate_one_armed_bandit_plots()

# All registered boss analyses have auto-generated methods:
# analyzer.analyze_<boss_name>(report_codes)
# analyzer.generate_<boss_name>_plots()
```

### Adding New Boss Analyses

The registry-based system makes adding new boss analyses extremely simple. Just create a configuration file:

```python
# src/guild_log_analysis/analysis/bosses/new_boss.py
from typing import Any
from ..base import BossAnalysisBase
from ..registry import register_boss

@register_boss("new_boss")  # Automatically creates analyzer.analyze_new_boss() method
class NewBossAnalysis(BossAnalysisBase):
    """Analysis for New Boss encounters."""

    def __init__(self, api_client: Any) -> None:
        super().__init__(api_client)
        self.boss_name = "New Boss"
        self.encounter_id = 1234  # Your encounter ID
        self.difficulty = 5  # Mythic

    # Define what analyses to run (no code needed!)
    ANALYSIS_CONFIG = [
        {
            "name": "Boss Interrupts",
            "type": "interrupts",
            "ability_id": 12345,  # Replace with actual ability ID
        },
        {
            "name": "Debuff Uptime",
            "type": "debuff_uptime",
            "ability_id": 67890.0,  # Replace with actual debuff ID
        },
        {
            "name": "Add Damage",
            "type": "damage_to_actor",
            "target_game_id": 11111,  # Replace with actual game ID
            "result_key": "damage_to_adds",
        }
    ]

    # Define how to visualize the data (no code needed!)
    PLOT_CONFIG = [
        {
            "analysis_name": "Boss Interrupts",
            "plot_type": "NumberPlot",
            "title": "Boss Interrupts",
            "value_column": "interrupts",
            "value_column_name": "Interrupts",
        },
        {
            "analysis_name": "Debuff Uptime",
            "plot_type": "PercentagePlot",
            "title": "Debuff Uptime",
            "value_column": "uptime_percentage",
            "value_column_name": "Uptime %",
        },
        {
            "analysis_name": "Add Damage",
            "plot_type": "NumberPlot",
            "title": "Damage to Adds",
            "value_column": "damage_to_adds",
            "value_column_name": "Damage",
        }
    ]
```

**That's it!** The system automatically:
- Registers the boss analysis class
- Creates `analyzer.analyze_new_boss()` method
- Creates `analyzer.generate_new_boss_plots()` method
- Handles all analysis execution and plot generation

**No changes needed to `main.py` or any other files!**

## Project Structure

```
guild-log-analysis/
├── src/guild_log_analysis/
│   ├── analysis/
│   │   ├── base.py              # Base analysis class with generic execution
│   │   ├── registry.py          # Boss registration decorator system
│   │   └── bosses/
│   │       ├── one_armed_bandit.py  # One-Armed Bandit analysis
│   │       └── example_boss.py      # Example boss template
│   ├── api/
│   │   ├── auth.py              # Authentication handling
│   │   ├── client.py            # API client with caching
│   │   └── exceptions.py        # Custom exceptions
│   ├── config/
│   │   ├── constants.py         # Application constants
│   │   ├── settings.py          # Configuration settings
│   │   └── logging_config.py    # Logging configuration
│   ├── plotting/
│   │   ├── base.py              # Plotting utilities
│   │   └── styles.py            # Plot styling
│   ├── utils/
│   │   ├── cache.py             # Caching utilities
│   │   └── helpers.py           # Helper functions
│   └── main.py                  # Main application with auto-registration
├── tests/                       # Test suite
├── requirements/                # Requirement files
├── logs/                        # Application logs
├── plots/                       # Generated plot images
└── README.md                    # This file
```

## Development

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src/guild_log_analysis --cov-report=term-missing

# Run specific test categories
python -m pytest tests/unit/        # Unit tests only
python -m pytest tests/integration/ # Integration tests only
```

### Code Quality

```bash
# Install and setup pre-commit hooks
pip install pre-commit
pre-commit install

# Run pre-commit on all files
pre-commit run --all-files

# Manual tool execution
black src/ tests/          # Format code
isort src/ tests/          # Sort imports
flake8 src/ tests/         # Lint code
mypy src/                  # Type checking
```

## License

MIT License - see LICENSE file for details.
