#!/usr/bin/env bash
# Usage: pinggy.sh <local_port>
# Creates a public tunnel using pinggy.io and prints the public URL.
ssh -o StrictHostKeyChecking=no -p 443 -R0:localhost:"$1" a.pinggy.io
