# Contributing to Guild Log Analysis

Thank you for your interest in contributing to Guild Log Analysis! This document provides guidelines and information for contributors.

## Code of Conduct

This project adheres to a code of conduct. By participating, you are expected to uphold this code:

- Be respectful and inclusive
- Focus on constructive feedback
- Help create a welcoming environment for all contributors
- Respect different viewpoints and experiences

## How to Contribute

### Reporting Bugs

Before creating bug reports, please check existing issues to avoid duplicates. When creating a bug report, include:

- **Clear title and description**
- **Steps to reproduce** the issue
- **Expected vs actual behavior**
- **Environment details** (Python version, OS, etc.)
- **Log files** or error messages (remove sensitive data)
- **Minimal code example** if applicable

### Suggesting Features

Feature suggestions are welcome! Please:

- Check existing issues for similar suggestions
- Provide clear use cases and benefits
- Consider implementation complexity
- Be open to discussion and feedback

### Pull Requests

1. **Fork the repository** and create a feature branch
2. **Follow coding standards** (see below)
3. **Add tests** for new functionality
4. **Update documentation** as needed
5. **Ensure all tests pass**
6. **Submit a pull request** with clear description

## Development Setup

### Prerequisites

- Python 3.13 or higher (target version)
- Git
- pip

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/yourusername/guild-log-analysis.git
cd guild-log-analysis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode with all dependencies
pip install -e .

# Or install specific requirement sets
pip install -r requirements/dev.txt   # Development tools
pip install -r requirements/test.txt  # Testing framework

# Install pre-commit hooks
pip install pre-commit
pre-commit install
```

### Environment Configuration

The application requires a `.env` file with Warcraft Logs API credentials:

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
WOW_CLIENT_ID=your_client_id
WOW_REDIRECT_URI=http://localhost:8080/callback
```

### Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run with coverage
python -m pytest tests/ --cov=src/guild_log_analysis --cov-report=term-missing

# Run specific test categories
python -m pytest tests/unit/        # Unit tests only
python -m pytest tests/integration/ # Integration tests only
python -m pytest -m "not slow"      # Skip slow tests
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Lint code
flake8 src/ tests/

# Type checking
mypy src/

# Run all quality checks
pre-commit run --all-files
```

## Coding Standards

### Python Style

- Follow **PEP 8** guidelines
- Target **Python 3.13** features and syntax
- Use **Black** for code formatting (line length: 88)
- Use **isort** for import sorting with black profile
- Pass **flake8** linting with docstring checks
- Include **type hints** for all functions using modern syntax
- Write **docstrings** in reStructuredText format
- Use modern type hints: `dict[K, V]`, `list[T]`, `set[T]`, `tuple[T, ...]`
- Avoid importing `Dict`, `List`, `Set`, `Tuple` from typing unless necessary
- Only use typing module for advanced types like `Union`, `Optional`, `Protocol`

### Development Principles

- **Apply SOLID principles** for maintainable code architecture
- **Ensure code modularity** - keep functions and classes focused on single responsibilities
- **Implement appropriate error handling** using custom exceptions and proper logging
- **Consider performance implications** especially for API calls and data processing
- **Prefer constants over repeating strings** to avoid magic numbers and strings

### Example Function

```python
def analyze_interrupts(
    self,
    report_code: str,
    fight_ids: set[int],
    report_players: list[dict[str, Any]],
    ability_id: float,
    analysis_name: str
) -> list[dict[str, Any]]:
    """
    Analyze interrupt events for a specific ability.

    :param report_code: Warcraft Logs report code
    :param fight_ids: Set of fight IDs to analyze
    :param report_players: List of player data dictionaries
    :param ability_id: Game ID of the ability to track interrupts for
    :param analysis_name: Name of the analysis for logging
    :returns: List of player interrupt data
    :raises APIError: If API request fails
    """
    # Implementation here
    pass
```

### Constants Usage

Always use constants instead of magic strings:

```python
# Good
column_name = AnalysisConstants.PLAYER_NAME_COLUMN
ability_id = AnalysisConstants.OVERLOAD_ABILITY_ID

# Bad
column_name = "name"
ability_id = 460582
```

### Error Handling

Use appropriate custom exceptions:

```python
from guild_log_analysis.api.exceptions import APIError, DataNotFoundError

try:
    result = api_client.make_request(query)
except APIError as e:
    logger.error(f"API request failed: {e}")
    raise
```

### Testing Guidelines

- Write tests for all new functionality
- Use descriptive test names
- Follow AAA pattern (Arrange, Act, Assert)
- Mock external dependencies
- Test both success and failure cases

```python
def test_get_fight_ids_success(self, mock_api_client, sample_api_response):
    """Test successful fight IDs retrieval."""
    # Arrange
    mock_api_client.make_request.return_value = sample_api_response
    analysis = OneArmedBanditAnalysis(mock_api_client)

    # Act
    result = analysis.get_fight_ids("test_report")

    # Assert
    assert result == {1, 2}
    mock_api_client.make_request.assert_called_once()
```

## Project Structure

### Adding New Boss Analysis

The registry-based system makes adding new boss analyses extremely simple:

1. **Create new file** in `src/guild_log_analysis/analysis/bosses/new_boss.py`
2. **Use `@register_boss()` decorator** - automatically registers the class
3. **Inherit from `BossAnalysisBase`** and set boss attributes
4. **Define `ANALYSIS_CONFIG`** - specify what analyses to run
5. **Define `PLOT_CONFIG`** - specify how to visualize the data
6. **Add constants** to `config/constants.py` if needed
7. **Create comprehensive tests** in `tests/unit/test_analysis/`
8. **Update documentation** and examples

**No manual changes needed to `GuildLogAnalyzer` class!** Methods are auto-generated:
- `analyzer.analyze_<boss_name>()`
- `analyzer.generate_<boss_name>_plots()`

#### Example Implementation

```python
from typing import Any
from ..base import BossAnalysisBase
from ..registry import register_boss

@register_boss("new_boss")  # Automatic registration
class NewBossAnalysis(BossAnalysisBase):
    def __init__(self, api_client: Any) -> None:
        super().__init__(api_client)
        self.boss_name = "New Boss"
        self.encounter_id = 1234
        self.difficulty = 5

    # Configuration-driven analysis (no methods needed!)
    ANALYSIS_CONFIG = [
        {"name": "Interrupts", "type": "interrupts", "ability_id": 12345},
        {"name": "Damage", "type": "damage_to_actor", "target_game_id": 67890, "result_key": "damage_to_adds"}
    ]

    PLOT_CONFIG = [
        {"analysis_name": "Interrupts", "plot_type": "NumberPlot", "title": "Interrupts", "value_column": "interrupts", "value_column_name": "Count"}
    ]
```

### File Organization

```
src/guild_log_analysis/
├── config/          # Configuration and constants
├── api/             # API client and authentication
│   ├── client.py    # WarcraftLogsAPIClient with caching
│   ├── auth.py      # OAuth authentication
│   └── exceptions.py # Custom API exceptions
├── analysis/        # Analysis modules
│   ├── base.py      # BossAnalysisBase with generic execution
│   ├── registry.py  # Boss registration decorator system
│   └── bosses/      # Boss-specific configuration files
│       ├── one_armed_bandit.py  # Configuration-based analysis
│       └── example_boss.py      # Example template
├── plotting/        # Visualization modules
│   ├── base.py      # BaseTablePlot abstract class
│   └── styles.py    # Plot styling and colors
├── utils/           # Utility functions
└── main.py          # GuildLogAnalyzer with auto-registration
```

## Documentation

### Docstring Format

Use reStructuredText format for all docstrings:

```python
def function_name(param1: str, param2: int) -> bool:
    """
    Brief description of the function.

    Longer description if needed, explaining the purpose,
    behavior, and any important details.

    :param param1: Description of first parameter
    :param param2: Description of second parameter
    :returns: Description of return value
    :raises ValueError: When parameter is invalid
    :raises APIError: When API request fails
    """
```

### README Updates

When adding features, update:
- Feature list
- Usage examples
- API reference
- Configuration options

## Commit Guidelines

### Commit Message Format

Follow these guidelines for consistent commit messages:

- Start with a short imperative sentence (max 50 chars) summarizing the changes
- Use present tense (e.g., "Add feature" not "Added feature")
- Leave a blank line after the first sentence
- Provide a more detailed explanation (max 2-3 sentences) if needed
- Keep the entire message under 74 characters per line
- Be insightful but concise, avoiding overly verbose descriptions
- Do not prefix the message with conventional commit types

**Examples:**
```
Add comprehensive CLAUDE.md development guide

Include development commands, architecture overview, code style
guidelines, and commit message format for future Claude Code
instances working with this codebase.
```

```
Fix failing tests and improve mock object handling

Add proper exception handling for Mock objects in base analysis
class and update test mocks to match actual implementation.
```

### Branch Naming

- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation updates
- `refactor/description` - Code refactoring

## Release Process

1. Update version in `pyproject.toml`
2. Update `CHANGELOG.md`
3. Create release branch
4. Run full test suite
5. Create pull request
6. Tag release after merge

## Getting Help

- Check existing documentation
- Search issues for similar problems
- Ask questions in discussions
- Contact maintainers for complex issues

## Recognition

Contributors will be recognized in:
- README acknowledgments
- Release notes
- Contributor list

Thank you for contributing to Guild Log Analysis!
