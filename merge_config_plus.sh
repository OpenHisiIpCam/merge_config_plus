#!/usr/bin/env sh

BASEDIR=$(dirname "$0")

PYTHONPATH=${BASEDIR} /usr/bin/env python3 -m merge_config_plus $@ 
