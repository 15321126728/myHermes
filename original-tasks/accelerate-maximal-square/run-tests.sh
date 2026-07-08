#!/bin/bash

pip3 install pytest==8.4.1

# Make sure the task module and C extension are findable
# Set PYTHONPATH to include the task directory with maximal_square.py
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONPATH="$SCRIPT_DIR:$PYTHONPATH"

# make sure no CUDA is used
CUDA_VISIBLE_DEVICES="" python3 -m pytest "$SCRIPT_DIR/tests/test_outputs.py" -rA
