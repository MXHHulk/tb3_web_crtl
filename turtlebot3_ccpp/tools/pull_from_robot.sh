#!/usr/bin/env bash
# 在本地（Windows Git Bash / Linux）執行：把車上產生的實驗紀錄與地圖拉回電腦備份。
#
#   bash turtlebot3_ccpp/tools/pull_from_robot.sh
#   ROBOT=ubuntu@192.168.0.50 bash turtlebot3_ccpp/tools/pull_from_robot.sh   # 換車子 IP
#
# 車上 ~/catkin_ws/src/turtlebot3_ccpp/{data,maps}  →  本地 experiments/robot/{data,maps}
#
# 規則：
#   - 只增不刪：車上的檔案不動；本地已有、車上已刪的檔案保留。同名檔以車上版本覆蓋
#     （coverage_runs.csv 等累加型 CSV 在車上只會變長）。
#   - 每次執行在 experiments/robot/pull_log.txt 記一行：時間、車上程式版本、檔案數。
#   - 每筆紀錄對應的程式版本：車上 .synced_commit（同步時寫入）；之後會寫進各紀錄檔。
set -euo pipefail

ROBOT="${ROBOT:-ubuntu@172.20.10.5}"
SRC='catkin_ws/src/turtlebot3_ccpp'

cd "$(git rev-parse --show-toplevel)"
OUT='experiments/robot'
mkdir -p "$OUT"

REV="$(ssh -o ConnectTimeout=8 "$ROBOT" "cat ~/$SRC/.synced_commit 2>/dev/null || echo unknown")"
echo "→ 從 $ROBOT 拉回 data/、maps/（車上程式版本 $REV）"

ssh -o ConnectTimeout=8 "$ROBOT" "cd ~/$SRC && tar cf - \$(ls -d data maps 2>/dev/null)" | tar xf - -C "$OUT"

N="$(find "$OUT/data" "$OUT/maps" -type f 2>/dev/null | wc -l)"
echo "$(date '+%F %T')  robot=$REV  files=$N" >> "$OUT/pull_log.txt"
echo "✓ 已備份到 $OUT（共 $N 個檔案）"
