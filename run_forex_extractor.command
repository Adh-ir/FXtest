#!/bin/bash
cd "$(dirname "$0")"
echo "Installing dependencies..."
pip3 install -r code/requirements.txt
python3 code/main.py
