# Guild Log Analysis

A comprehensive tool for analyzing World of Warcraft guild logs from Warcraft Logs API.

## Author

**Jonathan Sasse**
Email: radiant.daemme0w@icloud.com

## Features

- **Boss Analysis Framework**: Extensible system for analyzing different raid bosses
- **One-Armed Bandit Analysis**: Complete analysis for Liberation of Undermine encounters
- **Professional Plotting**: High-quality visualizations with consistent styling
- **API Integration**: Seamless integration with Warcraft Logs GraphQL API
- **Caching System**: Intelligent caching to minimize API calls
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

# Initialize analyzer
analyzer = GuildLogAnalyzer()

# Analyze One-Armed Bandit encounters
analyzer.analyze_one_armed_bandit(["report_code1", "report_code2"])

# Generate plots
analyzer.generate_one_armed_bandit_plots()
```

### Adding New Boss Analyses

To add a new boss analysis, simply create a new file in `src/guild_log_analysis/analysis/bosses/`:

```python
# src/guild_log_analysis/analysis/bosses/new_boss.py
from guild_log_analysis.analysis.base import BossAnalysisBase

class NewBossAnalysis(BossAnalysisBase):
    """Analysis for New Boss encounters."""

    def __init__(self, api_client: WarcraftLogsAPIClient) -> None:
        super().__init__(api_client)
        self.boss_name = "New Boss"
        self.encounter_id = 1234  # Your encounter ID
        self.difficulty = 5  # Mythic

    def analyze(self, report_codes: list[str]) -> None:
        """Implement your analysis logic here."""
        # Your custom analysis implementation
        pass
```

Then add a simple method to the main analyzer:

```python
# In main.py
def analyze_new_boss(self, report_codes: list[str]) -> None:
    """Analyze New Boss encounters."""
    from guild_log_analysis.analysis.bosses.new_boss import NewBossAnalysis

    analysis = NewBossAnalysis(self.api_client)
    analysis.analyze(report_codes)
    self.analyses['new_boss'] = analysis
```

## Project Structure

```
guild-log-analysis/
├── src/guild_log_analysis/
│   ├── analysis/
│   │   ├── base.py              # Base analysis class
│   │   └── bosses/
│   │       └── one_armed_bandit.py  # One-Armed Bandit analysis
│   ├── api/
│   │   ├── auth.py              # Authentication handling
│   │   ├── client.py            # API client
│   │   └── exceptions.py        # Custom exceptions
│   ├── config/
│   │   ├── constants.py         # Application constants
│   │   └── settings.py          # Configuration settings
│   ├── plotting/
│   │   ├── base.py              # Plotting utilities
│   │   └── styles.py            # Plot styling
│   ├── utils/
│   │   ├── cache.py             # Caching utilities
│   │   └── helpers.py           # Helper functions
│   └── main.py                  # Main application
├── tests/                       # Test suite
├── requirements/                # Requirement files
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
