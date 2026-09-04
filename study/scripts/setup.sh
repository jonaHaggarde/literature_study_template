#!/usr/bin/env bash
# One-time environment setup: creates a virtual environment and installs
# dependencies. Run from anywhere; this script locates study/ itself.
#
#   ./scripts/setup.sh

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/.."

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

echo "Installing dependencies..."
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r scripts/requirements.txt

echo ""
echo "Done. Activate the environment in your shell with:"
echo "  source .venv/bin/activate"
echo "Then drop PDFs into PDFs/ and run: python scripts/convert.py"
