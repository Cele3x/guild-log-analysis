# Tests Directory

This directory contains all test files and test-related resources for the Guild Log Analysis project.

## Directory Structure

```
tests/
├── README.md                 # This file - explains test directory structure
├── conftest.py              # PyTest configuration and shared fixtures
├── __init__.py              # Makes tests a Python package
├── unit/                    # Unit tests - test individual components in isolation
│   ├── test_analysis/       # Tests for analysis module
│   ├── test_api/            # Tests for API client functionality
│   ├── test_config/         # Tests for configuration management
│   ├── test_plotting/       # Tests for plotting functionality
│   ├── test_cli.py          # Tests for CLI interface
│   └── test_main.py         # Tests for main analyzer
├── integration/             # Integration tests - test component interactions
│   └── test_full_analysis.py # End-to-end analysis tests
├── fixtures/                # Test fixtures and mock data files
├── data/                    # Test data files and HTTP queries
│   └── http_queries/        # Manual HTTP test queries
└── output/                  # Test output files (isolated from production)
    ├── plots/               # Test-generated plot files
    ├── cache/               # Test cache files
    └── logs/                # Test log files
```

## Test Configuration

The test environment is configured in `conftest.py` to:
- Use `tests/output/` for all test outputs (plots, cache, logs)
- Provide common fixtures and mock data
- Isolate test data from production data

## Running Tests

```bash
# Run all tests
python -m pytest tests/

# Run unit tests only
python -m pytest tests/unit/

# Run integration tests only
python -m pytest tests/integration/

# Run with coverage
python -m pytest tests/ --cov=src/guild_log_analysis --cov-report=term-missing
```

## Test Guidelines

1. **Unit Tests**: Test individual functions/classes in isolation using mocks
2. **Integration Tests**: Test component interactions with minimal mocking
3. **Fixtures**: Place reusable test data in `fixtures/` directory
4. **Output**: All test outputs go to `tests/output/` subdirectories
5. **Isolation**: Tests should not depend on external APIs or production data
