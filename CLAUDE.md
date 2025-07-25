# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Commands

### Installation

#### Virtual Environment Setup (Recommended)
```bash
# Use the project's virtual environment
source /home/jonathan/.virtualenvs/guild-log-analysis/bin/activate

# Install project in development mode
pip install -e .

# Install development dependencies
pip install -r requirements/dev.txt
pip install -r requirements/test.txt

# Use convenience aliases (source the aliases file)
source .venv_aliases
```

#### Alternative Installation
```bash
# Install package in development mode with all dependencies
pip install -e .

# Install from requirements files
pip install -r requirements/dev.txt  # Development tools
pip install -r requirements/test.txt  # Testing framework
```

### Virtual Environment Aliases

When using the project's virtual environment, you can source the convenience aliases:
```bash
source .venv_aliases

# Available commands:
venv-test tests/           # Run tests with virtual environment
venv-mypy src/            # Type checking with virtual environment
venv-flake8 src/          # Code linting with virtual environment
venv-black src/           # Code formatting with virtual environment
venv-isort src/           # Import sorting with virtual environment
venv-install              # Install project in development mode
```

### Code Quality
```bash
# Install and setup pre-commit hooks
pip install pre-commit
pre-commit install

# Run pre-commit on all files
pre-commit run --all-files

# Manual tool execution (use venv- prefixed commands if using virtual environment)
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

#### Test Output Management

Tests are configured to save all output (plots, logs, cache) to the `tests/` directory to keep them separate from production data:

- **Test plots**: Saved to `tests/plots/` instead of root `plots/`
- **Test cache**: Uses `tests/cache/`
- **Test logs**: Written to `tests/logs/`

This separation is achieved through the `configure_test_environment` fixture in `tests/conftest.py` which sets `OUTPUT_DIRECTORY=tests` for all test runs.

### Environment Configuration
The application requires a `.env` file with Warcraft Logs API credentials:
```
CLIENT_ID=your_client_id
REDIRECT_URI=http://localhost:8080/callback
```

## Architecture Overview

### Core Components

**Analysis Framework**: The codebase uses an extensible boss analysis system built around `BossAnalysisBase` abstract class in `src/guild_log_analysis/analysis/base.py`. Each boss-specific analysis inherits from this base class and implements the `analyze()` method.

**API Integration**: The `WarcraftLogsAPIClient` in `src/guild_log_analysis/api/client.py` handles GraphQL API communication with built-in rate limiting, caching, and error handling. All API responses are cached using the `CacheManager` with automatic file rotation.

**Main Analyzer**: The `GuildLogAnalyzer` class in `src/guild_log_analysis/main.py` serves as the primary interface, providing simple methods like `analyze_one_armed_bandit()` that delegate to specific boss analysis classes.

### Data Flow

1. Main analyzer initializes API client with OAuth token
2. Boss-specific analysis classes query Warcraft Logs GraphQL API
3. Raw data is processed using base class methods (`get_fight_ids`, `get_participants`, `get_damage_to_actor`, `analyze_interrupts`, `analyze_table_data`)
4. Results stored in `self.results` list with structured analysis data
5. Plotting classes generate visualizations from processed results

### Adding New Boss Analysis

Create new file in `src/guild_log_analysis/analysis/bosses/new_boss.py`:
- Inherit from `BossAnalysisBase`
- Set `boss_name`, `encounter_id`, and `difficulty` attributes
- Define `CONFIG` with unified analysis and plot configurations
- Add corresponding method to `GuildLogAnalyzer` class

#### Analysis and Plot Type Variations

**CRITICAL**: When adding new analysis or plot types to the system, you MUST update both the example boss configuration AND the corresponding tests to maintain comprehensive coverage.

The `ExampleBossAnalysis` serves as the canonical reference for all available analysis and plot types. Any new variation must be:

1. **Added to `example_boss.py` CONFIG**: Include a representative configuration demonstrating the new type
2. **Added to `test_example_boss.py`**: Create specific tests for the new variation

#### Testing Policy

**DO NOT create boss-specific tests.** Only the `ExampleBossAnalysis` should have comprehensive tests in `test_example_boss.py`. This approach:

- Tests all analysis and plot type variations generically
- Avoids testing dynamic content from specific boss encounters
- Ensures configuration system functionality without relying on external API data
- Maintains test stability and performance

Specific boss implementations (like `OneArmedBanditAnalysis`) should only be tested for:
- Basic initialization
- Registry registration
- Configuration structure validation

All functional testing of analysis types, plot types, and role variations should be done through the example boss tests.

**Current Analysis Types** (all must be represented in example boss):
- `interrupts`: Boss interrupt tracking
- `table_data`: Unified table-based analysis supporting multiple data types:
  - `"data_type": "Debuffs"`: Debuff duration tracking
  - `"data_type": "DamageTaken"`: Damage received from abilities
  - `"data_type": "Deaths"`: Player death tracking with optional ability filter
- `damage_to_actor`: Damage/healing to specific targets
- `damage_to_actor` with `filter_expression`: Filtered damage tracking

**Boss-Specific Analysis Types**:
- `wrong_mine_analysis`: Specialized analysis for correlating debuffs with damage events (implemented in sprocketmonger_lockenstock.py)

**Current Plot Types** (all must be represented in example boss):
- `NumberPlot`: Simple numeric displays
- `PercentagePlot`: Percentage-based plots
- `HitCountPlot`: Hit count with damage tracking

**Plot Column Configuration**:
- `column_key_1`: Primary data column (required)
- `column_header_1`: Primary column header (optional, defaults to blank)
- `column_key_2`: Secondary data column (optional, for HitCountPlot)
- `column_header_2`: Secondary column header (optional, defaults to blank)
- `type`: Plot type specification (e.g., `"NumberPlot"`)

**Note**: The column key system supports up to 3 data columns: Name, Column 1, Column 2, plus Change. All headers default to blank if not specified.

**Current Role Variations** (all must be represented in example boss):
- DPS only: `[PlayerRoles.DPS]`
- Healers only: `[PlayerRoles.HEALER]`
- Tanks only: `[PlayerRoles.TANK]`
- Tanks + DPS: `[PlayerRoles.TANK, PlayerRoles.DPS]`
- All roles: No `roles` field

#### Example Boss Testing Requirements

The `test_example_boss.py` file must contain tests for:
- Each analysis type with proper configuration validation
- Each plot type with proper configuration validation
- Each role variation
- Result key auto-generation from names
- Custom vs. auto-generated plot titles
- Filter expressions where applicable
- Configuration consistency between analysis and plots

This ensures that generic functionality can be tested without relying on dynamic content from specific boss encounters.

### Configuration System

Settings loaded via `Settings` class from environment variables with `.env` file support. Key configurations include API URLs, cache settings, output directories, and logging configuration.

#### Spell Data Configuration

Spell information is stored in `src/guild_log_analysis/config/spells.yaml` and contains comprehensive spell data organized by class:

```yaml
CLASSNAME:
  - spellID: 12345
    name: Spell Name
    cooldown: 60
    type: defensive
```

**Spell Types:**
- `defensive`: Personal defensive cooldowns
- `heal`: Healing abilities
- `external`: External defensive/healing abilities
- `raid_defensive`: Raid-wide defensive abilities

**Usage Example:**
```python
from src.guild_log_analysis.config.constants import load_spells_data

spells = load_spells_data()
if spells:
    druid_spells = spells.get('DRUID', [])
    defensive_spells = [spell for spell in druid_spells if spell['type'] == 'defensive']
```

This data can be used for:
- Spell cooldown analysis
- Defensive ability usage tracking
- Class-specific spell filtering
- Raid cooldown coordination analysis

### Error Handling

Custom exceptions in `src/guild_log_analysis/api/exceptions.py` handle different failure scenarios:
- `AuthenticationError`: OAuth token issues
- `RateLimitError`: API rate limiting
- `APIError`: General API failures

### Caching Strategy

API responses cached with automatic file rotation when cache exceeds 10MB. Cache keys generated from GraphQL query + variables combination. Cache can be cleared programmatically or individual entries invalidated.

### Analysis Method Refactoring

The analysis system has been refactored to use a unified `analyze_table_data` method instead of multiple specialized methods. This consolidation provides several benefits:

**Replaced Methods:**
- `analyze_player_deaths` → `analyze_table_data` with `"data_type": "Deaths"`
- `analyze_debuff_uptime` → `analyze_table_data` with `"data_type": "Debuffs"`
- `analyze_damage_taken_from_ability` → `analyze_table_data` with `"data_type": "DamageTaken"`

**Legacy Configuration Migration:**
Old boss configurations using deprecated analysis types are automatically converted:
```python
# Old approach
"analysis": {
    "type": "player_deaths",
    "ability_id": 1216415,
}

# New unified approach
"analysis": {
    "type": "table_data",
    "ability_id": 1216415,
    "data_type": "Deaths",
}
```

**Benefits of Unified Approach:**
- Reduced code duplication (~400 lines removed)
- Consistent API for all table-based queries
- Easier maintenance and extension
- Unified caching and error handling
- Standardized field mapping across data types

### Universal Duration Normalization

Duration normalization is applied only to change calculations to ensure fair comparisons across reports with different fight durations:

**Change Normalization:**
- Previous data is normalized by fight duration for accurate change calculations
- Count-based metrics (interrupts, hit_count, etc.) → "per 30 minutes" for changes
- Damage-based metrics (damage_taken, damage_to_actor, etc.) → "per 30 minutes" for changes

**Non-Normalized Data:**
- Current/normal values are displayed without normalization
- Progress plots show actual values, not normalized values
- Percentage metrics (uptime_percentage, etc.) → Already relative, no normalization needed
- Death counts → Discrete events, not time-dependent

**Implementation Details:**
- Previous data is normalized using its fight duration in the analysis layer
- Current data remains unnormalized for display
- Change calculations normalize current values temporarily for accurate comparisons
- Both current and previous values are normalized to "per 30 minutes" for change calculations
- Original values preserved as `{metric}_original` for reference
- Normalization applied in `_generate_single_plot` for previous data and in plot classes for change calculations

**Benefits:**
- Normal values display actual raid performance without artificial scaling
- Change calculations are fair across different fight durations
- Progress plots show true progression without duration bias
- Accurate change percentages when comparing reports with different durations

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

## Version Management and Changelog

### CHANGELOG.md Updates

**CRITICAL**: Always check if CHANGELOG.md needs updates when making changes to the codebase.

#### When to Update CHANGELOG.md

1. **Code Changes**: Any modification to source code in `src/`
2. **New Features**: Added functionality or capabilities
3. **Bug Fixes**: Corrections to existing functionality
4. **Breaking Changes**: Modifications that affect existing APIs or behavior
5. **Documentation Updates**: Significant changes to README, CONTRIBUTING, or architecture docs
6. **Dependency Changes**: Updates to requirements or build configuration
7. **Configuration Changes**: Modifications to settings, environment variables, or deployment

#### Version Type Determination (Semantic Versioning)

Follow [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH):

**MAJOR (X.0.0)** - Breaking changes:
- API changes that break existing functionality
- Removal of deprecated features
- Architectural changes requiring user intervention
- Changes to public interfaces or method signatures

**MINOR (0.X.0)** - New features (backward compatible):
- New boss analysis implementations
- New API endpoints or methods
- Additional configuration options
- New CLI commands or arguments
- Enhanced functionality that doesn't break existing code

**PATCH (0.0.X)** - Bug fixes and minor improvements:
- Bug fixes that don't change functionality
- Performance improvements
- Documentation corrections
- Dependency updates (security patches)
- Code refactoring without behavior changes

#### Changelog Update Process

1. **Check Git Status**: Determine if changes warrant a changelog entry
2. **Assess Impact**: Determine if changes are MAJOR, MINOR, or PATCH level
3. **Check Current Version**: Look at the latest version in CHANGELOG.md
4. **Check Git Tags**: Run `git tag -l` to see if current version has been released
5. **Determine Action**:
   - If version hasn't been released (no git tag exists): Add to existing version section
   - If version has been released (git tag exists): Create new version section
6. **Update pyproject.toml**: Increment version number to match changelog
7. **Categorize Changes**: Use appropriate sections (Added, Changed, Deprecated, Removed, Fixed, Security)

#### Git Release Status Commands

```bash
# Check existing git tags
git tag -l

# Check if specific version is tagged
git tag -l "v2.0.0"

# Check current branch status
git status

# Check recent commits since last tag
git log --oneline $(git describe --tags --abbrev=0)..HEAD
```

#### Example Changelog Entry Structure

```markdown
## [X.Y.Z] - YYYY-MM-DD

### Added
- New feature descriptions
- New functionality additions

### Changed
- Modifications to existing features
- **BREAKING**: Mark breaking changes clearly

### Fixed
- Bug fixes and corrections

### Technical Details
- Implementation specifics
- Architectural improvements
```

#### Version Update Checklist

- [ ] Determine version type (MAJOR/MINOR/PATCH)
- [ ] Check if current version is already released (git tags)
- [ ] Update CHANGELOG.md with appropriate section
- [ ] Update version in pyproject.toml
- [ ] Ensure all changes are documented
- [ ] Verify changelog follows Keep a Changelog format

#### Practical Application

**Before making any code changes:**
1. Check `git tag -l` to see what versions are released
2. Look at current version in CHANGELOG.md
3. Assess whether your planned changes warrant a new version

**After making changes:**
1. Determine change impact (MAJOR/MINOR/PATCH)
2. Update CHANGELOG.md under current version if unreleased, or create new version section
3. Update pyproject.toml version if creating new version
4. Document all changes with clear descriptions
5. Categorize properly (Added/Changed/Fixed/etc.)

**Example Decision Tree:**
- Breaking API change → MAJOR version → New section in CHANGELOG.md
- New feature addition → MINOR version → New section in CHANGELOG.md
- Bug fix or improvement → PATCH version → New section in CHANGELOG.md
- Documentation only → No version change → Add to current unreleased version

## Commit Message Format

Follow these guidelines:
- Start with a short imperative sentence (max 50 chars) summarizing the changes
- Use present tense
- Leave a blank line after the first sentence
- Provide a more detailed explanation (max 2-3 sentences)
- Keep the entire message under 74 characters
- Be insightful but concise, avoiding overly verbose descriptions
- Do not prefix the message with anything
