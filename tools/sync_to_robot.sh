#!/usr/bin/env bash
# 在本地（Windows Git Bash / Linux）執行：把「已 commit」的實作程式同步到車上。
#
#   bash tools/sync_to_robot.sh            # 同步 HEAD
#   bash tools/sync_to_robot.sh --build    # 同步後在車上跑 catkin_make
#   ROBOT=ubuntu@192.168.0.50 bash tools/sync_to_robot.sh   # 換車子 IP
#
# 規則：
#   - 只同步實作程式（下面 PATHS），文件不上車。
#   - 只送已 commit 的內容（git archive HEAD，換行一律 LF）；有未 commit 的程式變更就拒絕，
#     確保車上跑的每一版都對得到一個 commit。車上會留 .synced_commit 記錄版本。
#   - 車上有、但 HEAD 已經沒有的檔案會被刪除（data/、maps/ 不在同步範圍，不受影響）。
#   - 車上控制台（ccpp-launcher 服務）若在執行，會自動重啟以載入新版；不會停掉正在跑的 roslaunch。
set -euo pipefail

ROBOT="${ROBOT:-ubuntu@172.20.10.5}"
DEST='catkin_ws/src/turtlebot3_ccpp'
PATHS=(scripts launch web test tools CMakeLists.txt package.xml)
BUILD=0
[[ "${1:-}" == "--build" ]] && BUILD=1

cd "$(git rev-parse --show-toplevel)"

if [[ -n "$(git status --porcelain -- "${PATHS[@]}")" ]]; then
    echo "✗ 以下程式有未 commit 的變更，請先 commit 再同步："
    git status --short -- "${PATHS[@]}"
    exit 1
fi

REV="$(git rev-parse --short HEAD)"
FILES="$(git ls-tree -r --name-only HEAD -- "${PATHS[@]}")"
echo "→ 同步 $REV 到 $ROBOT:~/$DEST"

git archive --format=tar HEAD -- "${PATHS[@]}" | ssh -o ConnectTimeout=8 "$ROBOT" "
    set -e
    cd ~/$DEST
    tar xf -
    # 刪掉 HEAD 已不存在的舊檔
    printf '%s\n' \"$FILES\" | sort > /tmp/ccpp_sync_keep
    [ \$(wc -l < /tmp/ccpp_sync_keep) -ge 5 ] || { echo '檔案清單異常，不刪舊檔'; exit 1; }
    find ${PATHS[*]} -type f -not -path '*/__pycache__/*' 2>/dev/null | sort > /tmp/ccpp_sync_have
    comm -13 /tmp/ccpp_sync_keep /tmp/ccpp_sync_have | while read -r f; do echo \"  刪除舊檔 \$f\"; rm -f \"\$f\"; done
    rm -f /tmp/ccpp_sync_keep /tmp/ccpp_sync_have
    find . -name __pycache__ -type d -prune -exec rm -rf {} +
    chmod +x scripts/*.py test/*.py tools/*.sh 2>/dev/null || true
    echo $REV > .synced_commit
    if [ $BUILD = 1 ]; then
        source /opt/ros/noetic/setup.bash
        cd ~/catkin_ws && catkin_make 2>&1 | tail -2
    fi
    if systemctl is-active --quiet ccpp-launcher.service; then
        sudo -n systemctl restart ccpp-launcher.service && echo '  已重啟車上控制台'
    fi
"
echo "✓ 車上已是 $REV"
