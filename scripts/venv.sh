#!/bin/bash
# Convenience script for working with the virtual environment

VENV_PATH="/home/jonathan/.virtualenvs/guild-log-analysis"
PYTHON_PATH="$VENV_PATH/bin/python"

# Activate virtual environment
source "$VENV_PATH/bin/activate"

# Function to run commands with the virtual environment Python
run_cmd() {
    "$PYTHON_PATH" "$@"
}

# Export functions and variables for use in other scripts
export VENV_PATH
export PYTHON_PATH
export -f run_cmd

echo "Virtual environment activated: $VENV_PATH"
echo "Python version: $($PYTHON_PATH --version)"
echo "Available commands:"
echo "  run_cmd <python_command>  - Run Python command with venv"
echo "  pytest tests/             - Run tests"
echo "  mypy src/                 - Type checking"
echo "  flake8 src/               - Code linting"
echo "  black src/                - Code formatting"
