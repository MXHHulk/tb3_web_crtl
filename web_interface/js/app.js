/**
 * 檔案名稱：app.js (網頁前端核心控制邏輯)
 * 檔案類型：JavaScript / 前端應用程式碼
 *
 * 核心功能：
 * 1. 建立與 ROS Bridge 的 WebSocket 連線，同步機器人狀態。
 * 2. 訂閱各種 ROS Topic (地圖、覆蓋紀錄、位姿) 並更新全域快取。
 * 3. 處理 UI 互動事件，包括縮放平移、手動遙控 (Teleop) 與任務啟動/停止。
 *
 * 通訊架構：
 *   Browser ←→ WebSocket:9090 ←→ rosbridge_server ←→ ROS Topics/Services
 *
 * 關鍵依賴：
 * - ROSLIB.js: ROS 官方提供的 JavaScript 客戶端庫。
 * - map_visualizer.js: 自定義的畫布渲染引擎 (需先載入)。
 */

// DOMContentLoaded：確保 HTML 元素全部載入後才執行，避免找不到 DOM 元素
document.addEventListener('DOMContentLoaded', () => {

    // 建立 ROS 連線實體
    // window.location.hostname 自動取得當前網頁的主機名稱 (IP 或 hostname)
    // 這樣無論從哪台電腦訪問，WebSocket 都會連到提供網頁的那台機器
    const ros = new ROSLIB.Ros({ url: 'ws://' + window.location.hostname + ':9090' });
    const statusBadge = document.getElementById('status');

    // =========================================================================
    // 畫布尺寸管理
    // =========================================================================

    /**
     * 動態調整所有畫布 (Canvas) 的尺寸，以適應當前瀏覽器視窗大小。
     * 每次視窗 resize 或初次載入時都需要呼叫，確保畫布解析度正確。
     */
    function resizeCanvases() {
        const viewport = document.getElementById('viewport');
        if (!viewport) return;

        const width = viewport.clientWidth;
        const height = viewport.clientHeight;

        // 視窗剛載入時尺寸可能為 0，需延遲等待 CSS 渲染完成後重試
        if (width === 0 || height === 0) {
            setTimeout(resizeCanvases, 500);
            return;
        }

        // 同步調整四個圖層畫布的像素尺寸
        // 注意：CSS 的 width/height 只影響顯示大小，canvas.width/height 才影響解析度
        ['canvas-map', 'canvas-processed', 'canvas-coverage', 'canvas-overlay'].forEach(id => {
            const canvas = document.getElementById(id);
            if (canvas) {
                canvas.width = width;
                canvas.height = height;
            }
        });

        // 地圖已載入但攝影機尚未初始化 (x=0 是預設值)，則重設攝影機至中心位置
        if (cachedMapMsg && Camera.x === 0) {
            Camera.reset(width, height);
        }
        renderAll();  // 重新渲染所有圖層以適應新尺寸
    }

    window.addEventListener('resize', resizeCanvases);  // 監聽視窗大小變化
    setTimeout(resizeCanvases, 100);                    // 頁面載入後 100ms 執行一次初始化

    // =========================================================================
    // ROS 連線狀態監聽
    // =========================================================================

    // WebSocket 成功連線到 rosbridge
    ros.on('connection', () => {
        statusBadge.innerText = '已連線';
        statusBadge.className = 'badge badge-success shadow-sm';
    });

    // WebSocket 連線發生錯誤 (例如 rosbridge 未啟動)
    ros.on('error', (error) => {
        statusBadge.innerText = '連線錯誤';
        statusBadge.className = 'badge badge-danger shadow-sm';
    });

    // WebSocket 連線已關閉 (例如機器人關機)
    ros.on('close', () => {
        statusBadge.innerText = '連線斷開';
        statusBadge.className = 'badge badge-warning shadow-sm';
    });

    // =========================================================================
    // ROS Topic 訂閱
    // 每個訂閱都在收到新訊息時更新對應的全域快取，並觸發重新渲染
    // =========================================================================

    // 訂閱原始 SLAM 地圖
    // 資料流：gmapping → /map → 此回呼 → cachedMapMsg → renderAll → drawMapBase
    const mapTopic = new ROSLIB.Topic({ ros, name: '/map', messageType: 'nav_msgs/OccupancyGrid' });
    mapTopic.subscribe((msg) => {
        // 第一次收到地圖時，初始化攝影機位置 (只執行一次)
        if (!cachedMapMsg) {
            const viewport = document.getElementById('viewport');
            Camera.reset(viewport.clientWidth, viewport.clientHeight);
        }
        cachedMapMsg = msg;
        // 在 UI 上顯示地圖的解析度與尺寸資訊
        document.getElementById('map-info').innerText =
            `${msg.info.width}x${msg.info.height} (${msg.info.resolution}m/px)`;
        renderAll();
    });

    // 訂閱已清掃區域的覆蓋軌跡地圖
    // 資料流：ccpp_manager → /ccpp/coverage_map → 此回呼 → cachedCoverageMsg
    const coverageTopic = new ROSLIB.Topic({ ros, name: '/ccpp/coverage_map', messageType: 'nav_msgs/OccupancyGrid' });
    coverageTopic.subscribe((msg) => {
        // 寫入特殊 z 值作為圖層類型識別碼，供 map_visualizer.js 的 drawMapBase 使用
        // 這是一個「協議約定」：利用 position.z 這個正常不用的欄位傳遞圖層種類
        msg.info.origin.position.z = 999;  // 識別為覆蓋軌跡圖層 → 顯示為藍色
        cachedCoverageMsg = msg;
        renderAll();
    });

    // 訂閱形態學預處理後的地圖 (去噪 + 安全邊距)
    const processedMapTopic = new ROSLIB.Topic({ ros, name: '/ccpp/processed_map', messageType: 'nav_msgs/OccupancyGrid' });
    processedMapTopic.subscribe((msg) => {
        msg.info.origin.position.z = 500;  // 識別為處理後地圖 → 顯示為橘紅色
        cachedProcessedMapMsg = msg;
        renderAll();
    });

    // 訂閱機器人的即時位姿 (由 ccpp_manager 從 TF 查詢後發布)
    const poseTopic = new ROSLIB.Topic({ ros, name: '/ccpp/robot_pose', messageType: 'geometry_msgs/PoseStamped' });
    poseTopic.subscribe((msg) => {
        cachedRobotPose = msg.pose;  // 只取 pose 部分，不需要 header
        // 在側邊欄顯示精確座標，保留 2 位小數
        document.getElementById('robot-pos').innerText =
            `X:${msg.pose.position.x.toFixed(2)}, Y:${msg.pose.position.y.toFixed(2)}`;
        renderAll();
    });

    // 訂閱當前清掃目標區域的多邊形邊界
    const targetTopic = new ROSLIB.Topic({ ros, name: '/ccpp/target_polygon', messageType: 'geometry_msgs/PolygonStamped' });
    targetTopic.subscribe((msg) => {
        cachedTargetPolygon = msg.polygon.points;  // 只取頂點陣列
        renderAll();
    });

    // 訂閱整體清掃進度 (0.0 ~ 1.0 的 Float32)
    const progressTopic = new ROSLIB.Topic({ ros, name: '/ccpp/task_progress', messageType: 'std_msgs/Float32' });
    progressTopic.subscribe((msg) => {
        const p = (msg.data * 100).toFixed(1);  // 轉換為百分比字串，保留 1 位小數
        document.getElementById('overall-progress').style.width = p + '%';  // 更新進度條寬度
        document.getElementById('progress-text').innerText = p + '%';        // 更新文字顯示
    });

    // =========================================================================
    // 地圖檢視控制 (Camera)
    // =========================================================================

    // 縮放按鈕：每次點擊縮放 20%
    document.getElementById('btn-zoom-in').onclick = () => { Camera.scale *= 1.2; renderAll(); };
    document.getElementById('btn-zoom-out').onclick = () => { Camera.scale /= 1.2; renderAll(); };

    // 旋轉按鈕：每次旋轉 15 度
    document.getElementById('btn-rotate-l').onclick = () => { Camera.rotation -= 15; renderAll(); };
    document.getElementById('btn-rotate-r').onclick = () => { Camera.rotation += 15; renderAll(); };

    // 重設按鈕：恢復預設的縮放、旋轉與置中位置
    document.getElementById('btn-reset').onclick = () => {
        const viewport = document.getElementById('viewport');
        Camera.reset(viewport.clientWidth, viewport.clientHeight);
        renderAll();
    };

    // =========================================================================
    // 手動遙控 (Teleop)
    // 透過發布 /cmd_vel (geometry_msgs/Twist) 直接控制機器人移動
    // =========================================================================

    // 建立速度指令 Topic 發布者
    const cmdVelTopic = new ROSLIB.Topic({
        ros: ros,
        name: '/cmd_vel',
        messageType: 'geometry_msgs/Twist'
    });

    const linearSpeed = 0.22;   // 最大線速度 (m/s)，TB3 Burger 額定最大 0.22
    const angularSpeed = 1.0;   // 最大角速度 (rad/s)

    let teleopTimer = null;     // setInterval 計時器，負責持續發布速度指令
    let currentLinear = 0;      // 當前線速度值
    let currentAngular = 0;     // 當前角速度值

    /**
     * 停止發送速度指令，並發送一個歸零的 Twist 訊息使機器人停止。
     * 在放開按鈕、按下 S 鍵或鬆開鍵盤時呼叫。
     */
    function stopPublishing() {
        currentLinear = 0;
        currentAngular = 0;
        if (teleopTimer) {
            clearInterval(teleopTimer);  // 停止定時發布
            teleopTimer = null;
            // 發送歸零訊息確保機器人立即停止，不會因為指令超時繼續滑行
            const twist = new ROSLIB.Message({
                linear:  { x: 0.0, y: 0.0, z: 0.0 },
                angular: { x: 0.0, y: 0.0, z: 0.0 }
            });
            cmdVelTopic.publish(twist);
        }
    }

    /**
     * 綁定遙控按鈕的滑鼠和觸控事件。
     * 按住按鈕時持續發送速度指令，放開時停止。
     * @param {string} id  - 按鈕的 HTML id
     * @param {number} lin - 線速度值 (正=前進, 負=後退)
     * @param {number} ang - 角速度值 (正=左轉, 負=右轉)
     */
    const bindBtn = (id, lin, ang) => {
        const btn = document.getElementById(id);
        if (!btn) return;

        // 滑鼠事件：適用於桌面瀏覽器
        btn.onmousedown = () => startPublishing(lin, ang);
        btn.onmouseup = stopPublishing;
        btn.onmouseleave = stopPublishing;  // 滑鼠離開按鈕區域也停止，防止按著不放跑出去

        // 觸控事件：適用於手機/平板
        btn.ontouchstart = (e) => { e.preventDefault(); startPublishing(lin, ang); };  // preventDefault 防止觸發 mousedown
        btn.ontouchend   = (e) => { e.preventDefault(); stopPublishing(); };
    };

    // 綁定四個方向按鈕：W(前進) X(後退) A(左轉) D(右轉)
    bindBtn('btn-teleop-w',  linearSpeed,  0);           // 前進
    bindBtn('btn-teleop-x', -linearSpeed,  0);           // 後退
    bindBtn('btn-teleop-a',  0,            angularSpeed); // 左轉
    bindBtn('btn-teleop-d',  0,           -angularSpeed); // 右轉

    // S 鍵停止按鈕 (單次點擊即停，不需要按住)
    const stopBtn = document.getElementById('btn-teleop-s');
    if (stopBtn) stopBtn.onclick = stopPublishing;

    // ---- 鍵盤控制 ----
    const keyState = {};  // 記錄各按鍵的當前按下狀態，支援多鍵同時按下

    window.addEventListener('keydown', (e) => {
        // 若當前焦點在輸入框，不攔截鍵盤事件 (避免打字時意外觸發移動)
        if (e.target.tagName.toLowerCase() === 'input') return;
        const key = e.key.toLowerCase();
        if (keyState[key]) return;  // 避免按住按鍵時重複觸發 keydown 事件
        keyState[key] = true;

        // 根據當前所有按下的鍵計算速度
        let lin = 0, ang = 0;
        if (keyState['w'])      lin = linearSpeed;
        else if (keyState['x']) lin = -linearSpeed;
        if (keyState['a'])      ang = angularSpeed;
        else if (keyState['d']) ang = -angularSpeed;

        if (lin !== 0 || ang !== 0) startPublishing(lin, ang);
        else if (key === 's') stopPublishing();
    });

    window.addEventListener('keyup', (e) => {
        const key = e.key.toLowerCase();
        keyState[key] = false;  // 釋放按鍵狀態

        // 重新計算剩餘按下的鍵是否還有速度指令
        let lin = 0, ang = 0;
        if (keyState['w'])      lin = linearSpeed;
        else if (keyState['x']) lin = -linearSpeed;
        if (keyState['a'])      ang = angularSpeed;
        else if (keyState['d']) ang = -angularSpeed;

        if (lin === 0 && ang === 0) stopPublishing();  // 全部釋放則停止
        else startPublishing(lin, ang);                 // 還有鍵按著則繼續
    });

    // ---- 圖層顯示/隱藏切換 ----
    // 每個 checkbox 的狀態改變都觸發重新渲染
    ['layer-map', 'layer-processed', 'layer-coverage', 'layer-target'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.onchange = renderAll;
    });

    // ---- 地圖拖曳平移 ----
    const viewport = document.getElementById('viewport');
    viewport.onmousedown = (e) => {
        Camera.isDragging = true;
        Camera.lastMouseX = e.clientX;
        Camera.lastMouseY = e.clientY;
    };
    window.onmousemove = (e) => {
        if (!Camera.isDragging) return;
        // 計算滑鼠移動增量，累加至攝影機位移
        Camera.x += (e.clientX - Camera.lastMouseX);
        Camera.y += (e.clientY - Camera.lastMouseY);
        Camera.lastMouseX = e.clientX;
        Camera.lastMouseY = e.clientY;
        renderAll();
    };
    window.onmouseup = () => { Camera.isDragging = false; };

    // ---- 滾輪縮放 ----
    viewport.onwheel = (e) => {
        e.preventDefault();  // 阻止頁面滾動
        // 向下滾動 (deltaY > 0) 縮小，向上滾動放大
        const factor = e.deltaY > 0 ? 0.9 : 1.1;
        Camera.scale *= factor;
        renderAll();
    };

    // =========================================================================
    // ROS Service 呼叫
    // 用於觸發機器人的任務狀態變更 (啟動/停止/重置)
    // =========================================================================

    // 建立 Service 客戶端實體
    const startSrv  = new ROSLIB.Service({ ros, name: '/ccpp/start',          serviceType: 'std_srvs/Trigger' });
    const stopSrv   = new ROSLIB.Service({ ros, name: '/ccpp/stop',           serviceType: 'std_srvs/Trigger' });
    const resetSrv  = new ROSLIB.Service({ ros, name: '/ccpp/reset_coverage', serviceType: 'std_srvs/Trigger' });
    const statusSrv = new ROSLIB.Service({ ros, name: '/ccpp/get_task_status', serviceType: 'turtlebot3_ccpp/GetTaskStatus' });

    // 記錄當前任務狀態，用於遙控時判斷是否需要先停止自動任務
    let currentTaskState = 'IDLE';

    // ---- 狀態輪詢 (每秒一次) ----
    // 定期向 ccpp_manager 查詢任務狀態，更新 UI 的狀態標籤
    setInterval(() => {
        if (!ros.isConnected) return;  // 未連線時跳過
        statusSrv.callService(new ROSLIB.ServiceRequest(), (res) => {
            currentTaskState = res.task_state;  // 更新本地狀態快取
            const badge = document.getElementById('task-state');
            if (badge) {
                badge.innerText = currentTaskState;
                // 根據是否在執行中決定顯示綠色或黃色標籤
                const isRunning = currentTaskState === 'EXPLORING' || currentTaskState === 'COVERING';
                badge.className = `badge ${isRunning ? 'badge-success' : 'badge-warning'} ml-2`;
            }
        });
    }, 1000);

    /**
     * 開始持續發送遙控速度指令。
     * 若當前自動任務正在執行，會先呼叫 stop 服務中止自動任務，再執行手動控制。
     * @param {number} linear  - 目標線速度 (m/s)
     * @param {number} angular - 目標角速度 (rad/s)
     */
    function startPublishing(linear, angular) {
        // 偵測到手動介入時，優先停止自動任務，防止 move_base 與手動指令衝突
        if (currentTaskState === 'EXPLORING' || currentTaskState === 'COVERING') {
            console.log('偵測到手動介入，正在中止自動任務...');
            stopSrv.callService(new ROSLIB.ServiceRequest(), (res) => {});
        }

        currentLinear = linear;
        currentAngular = angular;

        // 若計時器已在運行，不重複建立 (維持同一個發布頻率)
        if (!teleopTimer) {
            // 每 100ms (10Hz) 發布一次速度指令
            // ROS 的 cmd_vel 通常需要持續接收指令，停止發送後機器人會因看門狗超時而停止
            teleopTimer = setInterval(() => {
                const twist = new ROSLIB.Message({
                    linear:  { x: currentLinear,  y: 0.0, z: 0.0 },
                    angular: { x: 0.0, y: 0.0, z: currentAngular }
                });
                cmdVelTopic.publish(twist);
            }, 100);
        }
    }

    // ---- 任務控制按鈕事件綁定 ----

    // 啟動任務：呼叫 /ccpp/start 服務，ccpp_manager 進入 EXPLORING 狀態
    document.getElementById('btn-start').onclick = () => {
        startSrv.callService(new ROSLIB.ServiceRequest(), (res) => { alert(res.message); });
    };

    // 緊急停止：呼叫 /ccpp/stop 服務，ccpp_manager 回到 IDLE 狀態
    document.getElementById('btn-stop').onclick = () => {
        stopSrv.callService(new ROSLIB.ServiceRequest(), (res) => { alert(res.message); });
    };

    // 重置並重啟：確認後呼叫 /ccpp/reset_coverage，觸發系統完整重啟
    document.getElementById('btn-reset-coverage').onclick = () => {
        if (confirm('確定要清除當前覆蓋路徑並重啟系統嗎？')) {
            resetSrv.callService(new ROSLIB.ServiceRequest(), (res) => { console.log(res.message); });
        }
    };
});
