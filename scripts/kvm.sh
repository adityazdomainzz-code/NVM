#!/usr/bin/env bash
# Usage: kvm.sh <action> <domain>
ACTION="$1"; NAME="$2"
case "$ACTION" in
  start) virsh start "$NAME" ;;
  stop) virsh shutdown "$NAME" ;;
  restart) virsh reboot "$NAME" ;;
  force-reboot) virsh destroy "$NAME"; virsh start "$NAME" ;;
  status) virsh domstate "$NAME" ;;
esac
