# Test Data

This directory contains test data files and development tools.

## Directory Structure

```
data/
└── http_queries/         # Manual HTTP test queries for API development
    ├── test.http         # HTTP requests for testing API endpoints
    └── http-client.private.env.json  # Environment variables for HTTP client
```

## HTTP Queries

The `http_queries/` directory contains:
- **test.http**: Manual HTTP requests for testing Warcraft Logs API endpoints
- **http-client.private.env.json**: Environment variables for the HTTP client

These files are used for:
- Manual API testing during development
- Debugging API requests
- Exploring new API endpoints

## Usage

Open `test.http` in a REST client (like IntelliJ IDEA or VS Code REST Client) to:
- Test API endpoints manually
- Debug GraphQL queries
- Explore API responses

## Security Note

The `http-client.private.env.json` file may contain sensitive information like API keys and should be:
- Never committed to version control
- Included in `.gitignore`
- Used only for local development
