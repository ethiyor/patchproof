#!/usr/bin/env sh
set -eu

python -m pip install --upgrade pip
python -m pip install -e .

cd frontend
npm ci
npm run build
