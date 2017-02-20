#!/bin/bash

set -e
set -x
echo "This test checking if ssh is available"
sleep 5 # to allow cloudinit to setup ssh login
timeout --foreground 120 $ssh uname -a
