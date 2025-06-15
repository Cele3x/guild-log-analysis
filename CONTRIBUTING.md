# Contributing to WoW Guild Analysis

Thank you for your interest in contributing to WoW Guild Analysis! This document provides guidelines and information for contributors.

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

- Python 3.11 or higher
- Git
- pip

### Setup Steps

```bash
# Clone your fork
git clone https://github.com/yourusername/wow-guild-analysis.git
cd wow-guild-analysis

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev,test]"

# Install pre-commit hooks
pre-commit install
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/wow_guild_analysis --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest -m "not slow"  # Skip slow tests
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
- Use **Black** for code formatting (line length: 100)
- Use **isort** for import sorting
- Pass **flake8** linting
- Include **type hints** for all functions
- Write **docstrings** in reStructuredText format

### Example Function

```python
def analyze_interrupts(
    self,
    report_code: str,
    fight_ids: Set[int],
    report_players: List[Dict[str, Any]],
    ability_id: float,
    analysis_name: str
) -> List[Dict[str, Any]]:
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
from wow_guild_analysis.api.exceptions import APIError, DataNotFoundError

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

1. Create new file in `src/wow_guild_analysis/analysis/bosses/`
2. Inherit from `BossAnalysisBase`
3. Add constants to `config/constants.py`
4. Create tests in `tests/unit/test_analysis/`
5. Update documentation

### File Organization

```
src/wow_guild_analysis/
├── config/          # Configuration and constants
├── api/             # API client and authentication
├── analysis/        # Analysis modules
│   ├── base.py      # Base classes
│   └── bosses/      # Boss-specific implementations
├── plotting/        # Visualization modules
└── utils/           # Utility functions
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

Use conventional commit format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```
feat(analysis): add new boss analysis for Sikran
fix(api): handle rate limiting edge case
docs(readme): update installation instructions
test(plotting): add tests for percentage plots
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

Thank you for contributing to WoW Guild Analysis!

