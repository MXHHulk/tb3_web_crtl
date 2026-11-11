#!/usr/bin/env bash
# 在車上執行：安裝並啟用車上控制台的 systemd 服務（開機自動啟動）
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
sudo cp "$HERE/ccpp-launcher.service" /etc/systemd/system/ccpp-launcher.service
sudo systemctl daemon-reload
sudo systemctl enable ccpp-launcher.service
sudo systemctl restart ccpp-launcher.service
sleep 2
systemctl --no-pager --lines=5 status ccpp-launcher.service || true
echo
echo "控制台網址：http://$(hostname -I | awk '{print $1}'):8000"
