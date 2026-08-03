#!/usr/bin/env bash
# build.sh — Render's build command. Set in Render dashboard as: ./build.sh
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate