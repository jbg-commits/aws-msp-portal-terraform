#!/bin/bash
systemctl stop app.service || true
rm -rf /opt/msp-portal/*
