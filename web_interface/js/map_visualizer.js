/**
 * 檔案名稱：map_visualizer.js (地圖渲染引擎)
 * 檔案類型：JavaScript / 前端繪圖工具
 *
 * 核心功能：
 * 1. 實現一個虛擬攝影機系統 (Camera)，支援地圖的平移、縮放與旋轉。
 * 2. 解析 ROS OccupancyGrid 數據並將其轉化為 HTML5 Canvas 影像。
 * 3. 繪製機器人、目標區域、以及多層疊加的地圖資訊。
 *
 * 多層畫布架構：
 *   canvas-map       (底層) → SLAM 原始地圖 (灰白黑)
 *   canvas-processed (中層) → 演算法視角的處理後地圖 (橘紅障礙物)
 *   canvas-coverage  (中層) → 已清掃覆蓋軌跡 (半透明藍)
 *   canvas-overlay   (頂層) → 機器人圖示 + 目標多邊形 (永遠可見)
 *
 * 技術細節：
 * - 使用 setTransform 處理座標變換，一次呼叫即可設定平移/縮放/旋轉。
 * - 透過離屏畫布 (Offscreen Canvas) 預渲染地圖以提升效能。
 * - 物理對應：將機器人的世界座標 (m) 映射至像素座標。
 */

/**
 * 虛擬攝影機物件：管理地圖在畫布上的檢視狀態。
 * 所有渲染函數都透過 Camera.apply() 套用相同的座標變換，確保各圖層對齊。
 */
const Camera = {
    x: 0,           // 攝影機在畫布上的 X 位移 (像素)
    y: 0,           // 攝影機在畫布上的 Y 位移 (像素)
    scale: 1.0,     // 縮放倍率 (1.0 = 原始大小)
    rotation: 0,    // 旋轉角度 (角度制，非弧度)
    isDragging: false,   // 滑鼠拖曳狀態旗標
    lastMouseX: 0,       // 上一次滑鼠位置 X，用於計算拖曳增量
    lastMouseY: 0,       // 上一次滑鼠位置 Y，用於計算拖曳增量

    /**
     * 重設攝影機至初始狀態，將地圖置中並縮放至適當大小。
     * 在視窗調整大小或按下「重設」按鈕時呼叫。
     * @param {number} width  - 畫布寬度 (px)
     * @param {number} height - 畫布高度 (px)
     */
    reset(width, height) {
        this.x = width / 2;    // 將原點設在畫布中心
        this.y = height / 2;
        this.scale = 0.8;      // 初始縮放 80%，讓地圖有些邊距
        this.rotation = 0;     // 清除旋轉
    },

    /**
     * 將攝影機的當前狀態套用至指定的 2D 繪圖上下文。
     * 呼叫後，後續的所有繪圖操作都會在此座標系統下執行。
     * @param {CanvasRenderingContext2D} ctx - 目標畫布的 2D context
     */
    apply(ctx) {
        // setTransform(a,b,c,d,e,f) 設定變換矩陣，重設為單位矩陣 (無變換)
        ctx.setTransform(1, 0, 0, 1, 0, 0);
        // 清除整個畫布，準備重新繪製
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);

        // 依序套用：平移 → 縮放 → 旋轉
        // 注意順序很重要：先平移到中心，再縮放旋轉，才能以中心為基準
        ctx.translate(this.x, this.y);
        ctx.scale(this.scale, this.scale);
        ctx.rotate(this.rotation * Math.PI / 180);  // 轉換為弧度
    }
};

// ============================================================================
// 全域數據快取
// 儲存從 ROS Topic 接收到的最新訊息，供各渲染函數使用
// null 表示尚未收到該 Topic 的第一筆資料
// ============================================================================
let cachedMapMsg = null;           // /map - SLAM 原始地圖
let cachedProcessedMapMsg = null;  // /ccpp/processed_map - 預處理後地圖
let cachedCoverageMsg = null;      // /ccpp/coverage_map - 覆蓋軌跡地圖
let cachedRobotPose = null;        // /ccpp/robot_pose - 機器人姿態
let cachedTargetPolygon = null;    // /ccpp/target_polygon - 清掃目標多邊形頂點

/**
 * 核心渲染函數：遍歷所有圖層並根據可見性決定是否繪製。
 * 由 ROS Topic 回呼或 UI 事件觸發，每次呼叫都完整重繪所有畫布。
 */
function renderAll() {
    // 圖層定義陣列：每個物件描述一個畫布圖層的繪製規則
    const layers = [
        {
            id: 'canvas-map',           // 底層：SLAM 原始地圖
            drawer: drawMapBase,
            data: cachedMapMsg,
            visible: document.getElementById('layer-map').checked
        },
        {
            id: 'canvas-processed',     // 中層：演算法處理後地圖
            drawer: drawMapBase,
            data: cachedProcessedMapMsg,
            visible: document.getElementById('layer-processed').checked
        },
        {
            id: 'canvas-coverage',      // 中層：已清掃覆蓋軌跡
            drawer: drawMapBase,
            data: cachedCoverageMsg,
            visible: document.getElementById('layer-coverage').checked
        },
        {
            id: 'canvas-overlay',       // 頂層：機器人與多邊形 (永遠可見)
            drawer: drawOverlay,
            data: null,
            visible: true
        }
    ];

    layers.forEach(layer => {
        const canvas = document.getElementById(layer.id);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');

        if (layer.visible && layer.data) {
            // 可見且有資料：套用攝影機變換後繪製
            Camera.apply(ctx);
            layer.drawer(layer.data, ctx);
        } else if (layer.id === 'canvas-overlay') {
            // 覆蓋層 (機器人、多邊形) 永遠需要應用變換並繪製
            // 即使沒有明確的 data，機器人圖示也要保持顯示
            Camera.apply(ctx);
            layer.drawer(null, ctx);
        } else {
            // 不可見的圖層：重設變換矩陣並清空畫布
            ctx.setTransform(1, 0, 0, 1, 0, 0);
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    });
}

/**
 * 繪製基礎地圖層 (OccupancyGrid → Canvas 像素陣列)。
 *
 * 使用離屏畫布 (Offscreen Canvas) 的原因：
 *   直接操作 ImageData 像素陣列比呼叫 fillRect 快很多。
 *   先在離屏畫布完成所有像素計算，再一次性 drawImage 到主畫布。
 *
 * 圖層類型識別方式 (自定義協議)：
 *   由 app.js 在接收 Topic 時寫入 msg.info.origin.position.z：
 *   z=999 → coverage map (清掃軌跡，藍色)
 *   z=500 → processed map (處理後障礙物，橘紅色)
 *   z=0   → 原始 SLAM 地圖 (黑白灰)
 *
 * @param {Object} msg - ROS OccupancyGrid 訊息物件
 * @param {CanvasRenderingContext2D} ctx - 已套用攝影機變換的畫布 context
 */
function drawMapBase(msg, ctx) {
    if (!msg || !msg.info) return;
    const { width, height } = msg.info;
    if (width === 0 || height === 0) return;

    // --- 建立離屏畫布 ---
    // 離屏畫布與地圖解析度相同 (width x height 像素)
    const offscreen = document.createElement('canvas');
    offscreen.width = width;
    offscreen.height = height;
    const oCtx = offscreen.getContext('2d');
    // createImageData 建立一個 RGBA 像素緩衝區，每個像素 4 bytes (R, G, B, A)
    const imgData = oCtx.createImageData(width, height);

    // 根據 z 值辨識圖層類型，決定顏色映射規則
    const isCoverage = (msg.info.origin.position.z === 999);
    const isProcessed = (msg.info.origin.position.z === 500);

    // --- 逐像素上色 ---
    for (let i = 0; i < msg.data.length; i++) {
        const val = msg.data[i];  // ROS 值：-1 (未知) / 0 (空地) / 100 (障礙物)
        let r, g, b, a = 255;    // 預設完全不透明

        if (val === -1) {
            r = g = b = 60;        // 未知區域 → 深灰色 (#3c3c3c)
        } else if (val === 0) {
            r = g = b = 200;       // 可行駛空地 → 淺灰色 (#c8c8c8)
        } else if (val === 100) {
            if (isCoverage) {
                // 已清掃軌跡：半透明藍色，可看穿底層地圖
                r = 0; g = 100; b = 255; a = 180;
            } else if (isProcessed) {
                // 演算法視角的障礙物：橘紅色，表示安全邊距膨脹後的結果
                r = 255; g = 100; b = 0; a = 200;
            } else {
                r = g = b = 0;     // 原始障礙物 → 黑色 (#000000)
            }
        } else {
            // 其他漸層數值 (1~99)：反比映射到亮度
            const brightness = 200 - (val * 2);
            r = g = b = Math.max(0, brightness);
        }

        // --- 計算 ImageData 陣列索引 ---
        // ROS OccupancyGrid 的原點在左下角，但 Canvas 原點在左上角
        // 因此需要「翻轉 Y 軸」：row = height - 1 - row_from_bottom
        const row = Math.floor(i / width);
        const col = i % width;
        const idx = ((height - row - 1) * width + col) * 4;  // 每像素佔 4 個 bytes

        imgData.data[idx]     = r;
        imgData.data[idx + 1] = g;
        imgData.data[idx + 2] = b;
        imgData.data[idx + 3] = a;
    }

    // 將像素陣列寫入離屏畫布
    oCtx.putImageData(imgData, 0, 0);

    // 將離屏畫布貼到主畫布，以地圖中心為原點 (-width/2, -height/2)
    // 因為 Camera.apply() 已將原點移到視窗中心，所以地圖會自動置中
    ctx.drawImage(offscreen, -width / 2, -height / 2);
}

/**
 * 繪製覆蓋物圖層：機器人圖示與目標清掃多邊形。
 * 此函數對應 canvas-overlay，永遠繪製在最上層。
 *
 * @param {null} _ - 此圖層不需要傳入 data 參數
 * @param {CanvasRenderingContext2D} ctx - 已套用攝影機變換的畫布 context
 */
function drawOverlay(_, ctx) {
    if (!cachedMapMsg) return;
    const info = cachedMapMsg.info;

    // --- 1. 繪製清掃目標區域的綠色多邊形 ---
    if (cachedTargetPolygon && document.getElementById('layer-target').checked) {
        ctx.beginPath();
        cachedTargetPolygon.forEach((pt, i) => {
            // 將 ROS 世界座標 (m) 轉換為畫布像素座標
            const p = worldToCanvas(pt.x, pt.y, info);
            if (i === 0) ctx.moveTo(p.x, p.y);
            else ctx.lineTo(p.x, p.y);
        });
        ctx.closePath();
        ctx.fillStyle = 'rgba(0, 255, 0, 0.3)';  // 半透明綠色填充
        ctx.fill();
        ctx.strokeStyle = '#00ff00';              // 亮綠色邊框
        // 線條寬度除以 scale，確保縮放時線條粗細保持視覺一致
        ctx.lineWidth = 2 / Camera.scale;
        ctx.stroke();
    }

    // --- 2. 繪製代表機器人的黃色圓點與方向指針 ---
    if (cachedRobotPose) {
        const p = worldToCanvas(cachedRobotPose.position.x, cachedRobotPose.position.y, info);
        ctx.save();  // 儲存當前繪圖狀態，避免旋轉影響後續繪製

        ctx.translate(p.x, p.y);  // 將繪圖原點移至機器人位置

        // 繪製機器人主體：黃色實心圓 + 白色邊框
        ctx.beginPath();
        ctx.arc(0, 0, 8 / Camera.scale, 0, Math.PI * 2);  // 半徑隨縮放調整
        ctx.fillStyle = 'yellow';
        ctx.fill();
        ctx.strokeStyle = 'white';
        ctx.stroke();

        // 繪製方向指針：從圓心延伸一條線，指向機器人當前朝向
        // 需要將四元數旋轉轉換為 Yaw 角度，再進行 canvas 旋轉
        ctx.rotate(-getYawFromQuat(cachedRobotPose.orientation));
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(15 / Camera.scale, 0);  // 長度隨縮放調整
        ctx.stroke();

        ctx.restore();  // 還原繪圖狀態，清除 translate 與 rotate 的影響
    }
}

/**
 * 工具函數：將物理世界座標 (x, y) 轉換為畫布像素座標。
 *
 * 座標系轉換說明：
 *   ROS 地圖座標原點 (origin) 是地圖左下角的世界座標 (m)
 *   畫布以 drawMapBase 時的 (-width/2, -height/2) 為左上角
 *   Y 軸方向相反 (ROS 向上為正，Canvas 向下為正)
 *
 * @param {number} wx - 世界座標 X (公尺)
 * @param {number} wy - 世界座標 Y (公尺)
 * @param {Object} info - OccupancyGrid.info (包含 origin, resolution, width, height)
 * @returns {{x: number, y: number}} 畫布像素座標
 */
function worldToCanvas(wx, wy, info) {
    return {
        // X：世界座標相對於地圖原點的像素偏移，再減去半寬以對齊 drawImage 的中心偏移
        x: (wx - info.origin.position.x) / info.resolution - info.width / 2,
        // Y：翻轉 Y 軸 (地圖高度 - 像素位置 = Canvas Y 座標)
        y: info.height / 2 - (wy - info.origin.position.y) / info.resolution
    };
}

/**
 * 工具函數：從 ROS 四元數訊息中提取 Yaw 偏航角 (繞 Z 軸的旋轉角度)。
 *
 * 四元數 → Yaw 轉換公式 (歐拉角 ZYX 分解)：
 *   yaw = atan2(2*(w*z + x*y), 1 - 2*(y² + z²))
 *
 * @param {Object} q - ROS orientation 四元數 {x, y, z, w}
 * @returns {number} Yaw 角 (弧度)
 */
function getYawFromQuat(q) {
    return Math.atan2(
        2.0 * (q.w * q.z + q.x * q.y),
        1.0 - 2.0 * (q.y * q.y + q.z * q.z)
    );
}
