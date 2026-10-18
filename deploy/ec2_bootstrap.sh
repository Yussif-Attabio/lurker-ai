#!/bin/bash
set -euxo pipefail

# The EC2 instance is launched with instance-initiated shutdown behavior set to
# terminate. This timer therefore destroys the instance no later than 50 minutes
# after bootstrap begins, even if the controlling Mac disconnects.
systemd-run \
  --unit=lurker-m3-auto-terminate \
  --on-active=50m \
  --timer-property=AccuracySec=1s \
  /usr/sbin/shutdown -h now

dnf install -y docker
systemctl enable --now docker
usermod -aG docker ec2-user

touch /var/tmp/lurker-m3-bootstrap-ready
