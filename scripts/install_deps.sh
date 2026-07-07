#!/bin/bash
set -e

if [ ! -d /opt/msp-portal-venv ]; then
  python3 -m venv /opt/msp-portal-venv
fi

/opt/msp-portal-venv/bin/pip install --quiet --upgrade pip
/opt/msp-portal-venv/bin/pip install --quiet -r /opt/msp-portal/requirements.txt
