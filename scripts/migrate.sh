#!/bin/bash
set -e

cd /opt/msp-portal
/opt/msp-portal-venv/bin/python -m alembic -c alembic.ini upgrade head
