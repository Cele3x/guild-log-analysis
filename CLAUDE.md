# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation
```bash
# Recommended: Install package in development mode with all dependencies
pip install -e .

# Alternative: Install from requirements files
pip install -r requirements/dev.txt  # Development tools
pip install -r requirements/test.txt  # Testing framework
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

#### Enhanced Pre-commit Configuration

The project includes comprehensive pre-commit hooks that enforce CLAUDE.md guidelines:

**Code Formatting & Style:**
- Black with 79-character line length (PEP 8)
- isort for import organization
- flake8 with additional plugins for enhanced linting

**Quality & Security:**
- mypy for strict type checking (Python 3.13)
- bandit for security vulnerability scanning
- pydocstyle for reST docstring format validation

**Additional Checks:**
- File hygiene (trailing whitespace, end-of-file fixes)
- YAML, JSON, TOML validation
- Python best practices enforcement

All hooks are configured to align with the code style guidelines in this document.

### Testing
```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src/guild_log_analysis --cov-report=term-missing

# Run specific test types
python -m pytest tests/unit/        # Unit tests only
python -m pytest tests/integration/ # Integration tests only
```

### Environment Configuration
The application requires a `.env` file with Warcraft Logs API credentials:
```
WOW_CLIENT_ID=your_client_id
WOW_REDIRECT_URI=http://localhost:8080/callback
```

## Architecture Overview

### Core Components

**Analysis Framework**: The codebase uses an extensible boss analysis system built around `BossAnalysisBase` abstract class in `src/guild_log_analysis/analysis/base.py`. Each boss-specific analysis inherits from this base class and implements the `analyze()` method.

**API Integration**: The `WarcraftLogsAPIClient` in `src/guild_log_analysis/api/client.py` handles GraphQL API communication with built-in rate limiting, caching, and error handling. All API responses are cached using the `CacheManager` with automatic file rotation.

**Main Analyzer**: The `GuildLogAnalyzer` class in `src/guild_log_analysis/main.py` serves as the primary interface, providing simple methods like `analyze_one_armed_bandit()` that delegate to specific boss analysis classes.

### Data Flow

1. Main analyzer initializes API client with OAuth token
2. Boss-specific analysis classes query Warcraft Logs GraphQL API
3. Raw data is processed using base class methods (`get_fight_ids`, `get_participants`, `get_damage_to_actor`, `analyze_interrupts`, `analyze_debuff_uptime`)
4. Results stored in `self.results` list with structured analysis data
5. Plotting classes generate visualizations from processed results

### Adding New Boss Analysis

Create new file in `src/guild_log_analysis/analysis/bosses/new_boss.py`:
- Inherit from `BossAnalysisBase`
- Set `boss_name`, `encounter_id`, and `difficulty` attributes
- Implement `analyze(report_codes)` method
- Add corresponding method to `GuildLogAnalyzer` class

### Configuration System

Settings loaded via `Settings` class from environment variables with `.env` file support. Key configurations include API URLs, cache settings, output directories, and logging configuration.

### Error Handling

Custom exceptions in `src/guild_log_analysis/api/exceptions.py` handle different failure scenarios:
- `AuthenticationError`: OAuth token issues
- `RateLimitError`: API rate limiting
- `APIError`: General API failures

### Caching Strategy

API responses cached with automatic file rotation when cache exceeds 10MB. Cache keys generated from GraphQL query + variables combination. Cache can be cleared programmatically or individual entries invalidated.

## Code Style Guidelines

### Python Standards
- Target Python 3.13
- Adhere to PEP 8 guidelines
- Use modern type hints: `dict[K, V]`, `list[T]`, `set[T]`, `tuple[T, ...]`
- Avoid importing `Dict`, `List`, `Set`, `Tuple` from typing unless necessary
- Only use typing module for advanced types like `Union`, `Optional`, `Protocol`, etc.
- Utilize clear and descriptive variable and function names
- Add comments for complex logic or non-obvious implementations

### Documentation
Add reStructuredText (reST) format docstrings to all functions:

```python
"""
This is a reST style.

:param param1: this is a first param
:param param2: this is a second param
:returns: this is a description of what is returned
:raises keyError: raises an exception
"""
```

### Development Principles
- Apply SOLID principles
- Ensure code modularity and maintainability
- Implement appropriate error handling
- Consider performance implications
- Prefer constants over repeating strings

## Commit Message Format

Follow these guidelines:
- Start with a short imperative sentence (max 50 chars) summarizing the changes
- Use present tense
- Leave a blank line after the first sentence
- Provide a more detailed explanation (max 2-3 sentences)
- Keep the entire message under 74 characters
- Be insightful but concise, avoiding overly verbose descriptions
- Do not prefix the message with anything
