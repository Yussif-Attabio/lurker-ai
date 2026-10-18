#!/bin/bash
set -euo pipefail

# The instance is configured with instance-initiated shutdown behavior set to
# terminate. This independent timer therefore terminates the host no later than
# 50 minutes after bootstrap begins even if the controlling Mac disconnects.
systemd-run \
  --unit=lurker-m6-auto-terminate \
  --on-active=50m \
  --timer-property=AccuracySec=1s \
  /usr/sbin/shutdown -h now

dnf install -y docker
systemctl enable --now docker
usermod -aG docker ec2-user

touch /var/tmp/lurker-m6-bootstrap-ready
