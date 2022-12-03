#!/bin/bash
sudo apt-get install python3 python3-pip libglib2.0-dev
pip3 install -r requirements.txt
HELPER_LOC="$(pip3 show bluepy | grep Location: | cut -c 11-)/bluepy/bluepy-helper"
CAPABILITIES='cap_net_raw,cap_net_admin+eip'
sudo setcap $CAPABILITIES "$HELPER_LOC"
sudo setcap -v $CAPABILITIES "$HELPER_LOC"