#!/usr/bin/env bash
# Usage: lxc.sh <action> <name>
ACTION="$1"; NAME="$2"
case "$ACTION" in
  start) lxc-start -n "$NAME" -d ;;
  stop) lxc-stop -n "$NAME" ;;
  restart) lxc-stop -n "$NAME" 2>/dev/null; lxc-start -n "$NAME" -d ;;
  status) lxc-info -n "$NAME" | head -20 ;;
  create) echo "Create LXC from Proxmox/Incus/LXD template on the node." ;;
esac
