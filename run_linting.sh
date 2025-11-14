#!/bin/sh

# Remove unused imports and variables
echo "Running autoflake..."
autoflake --in-place --remove-all-unused-imports --remove-unused-variables --ignore-init-module-imports -r .

# Run other linters
echo "Running flake8..."
flake8 . --max-line-length=79 --ignore=E501,W503,W504

echo "Running pylint..."
pylint --recursive=y --ignore=venv,env,.venv,.env .