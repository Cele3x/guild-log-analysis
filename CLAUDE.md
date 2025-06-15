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
