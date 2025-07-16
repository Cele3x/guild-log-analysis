# Test Fixtures

This directory contains reusable test fixtures and mock data files.

## Purpose

Test fixtures provide consistent, reusable test data that can be shared across multiple test files.

## Usage

Place fixture files here for:
- Sample API responses (JSON files)
- Mock data files
- Test configuration files
- Reference data for testing

## Example Structure

```
fixtures/
├── api_responses/
│   ├── sample_fights.json
│   ├── sample_players.json
│   └── sample_events.json
├── mock_data/
│   ├── test_players.json
│   └── test_reports.json
└── configs/
    └── test_settings.json
```

## Loading Fixtures

```python
import json
import os

def load_fixture(filename):
    fixture_path = os.path.join(os.path.dirname(__file__), 'fixtures', filename)
    with open(fixture_path, 'r') as f:
        return json.load(f)

# Usage in tests
sample_data = load_fixture('api_responses/sample_fights.json')
```
