# Test Output Directory

This directory contains all output files generated during test execution.

## Directory Structure

```
output/
├── plots/     # Test-generated plot files (.png, .jpg, etc.)
├── cache/     # Test cache files (API responses, etc.)
└── logs/      # Test log files
```

## Purpose

This directory is used to isolate test outputs from production outputs:
- **Production outputs**: Go to the root `output/` directory
- **Test outputs**: Go to `tests/output/` directory

## Configuration

The test environment is configured in `tests/conftest.py` to use this directory:
```python
os.environ["OUTPUT_DIRECTORY"] = "tests"
```

## Maintenance

Files in this directory are:
- Generated automatically during test runs
- Safe to delete (will be regenerated)
- Excluded from version control via `.gitignore`
- Should not be committed to the repository
