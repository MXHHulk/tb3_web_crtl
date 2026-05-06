/**
 * CCPP 視覺化工具 Pro - 支援旋轉、縮放、平移與多層顯示
 */

const Camera = {
    x: 0, y: 0, scale: 1.0, rotation: 0,
    isDragging: false, lastMouseX: 0, lastMouseY: 0,
    
    reset(width, height) {
        this.x = width / 2;
        this.y = height / 2;
        this.scale = 0.8;
        this.rotation = 0;
    },
    
    apply(ctx) {
        ctx.setTransform(1, 0, 0, 1, 0, 0); // Reset
        ctx.clearRect(0, 0, ctx.canvas.width, ctx.canvas.height);
        
        ctx.translate(this.x, this.y);
        ctx.scale(this.scale, this.scale);
        ctx.rotate(this.rotation * Math.PI / 180);
    }
};

let cachedMapMsg = null;
let cachedCoverageMsg = null;
let cachedRobotPose = null;
let cachedTargetPolygon = null;

function renderAll() {
    const layers = [
        { id: 'canvas-map', drawer: drawMapBase, data: cachedMapMsg, visible: document.getElementById('layer-map').checked },
        { id: 'canvas-coverage', drawer: drawMapBase, data: cachedCoverageMsg, visible: document.getElementById('layer-coverage').checked },
        { id: 'canvas-overlay', drawer: drawOverlay, data: null, visible: true }
    ];

    layers.forEach(layer => {
        const canvas = document.getElementById(layer.id);
        const ctx = canvas.getContext('2d');
        if (layer.visible && layer.data) {
            Camera.apply(ctx);
            layer.drawer(layer.data, ctx);
        } else if (layer.id === 'canvas-overlay') {
            Camera.apply(ctx);
            layer.drawer(null, ctx);
        } else {
            ctx.setTransform(1, 0, 0, 1, 0, 0);
            ctx.clearRect(0, 0, canvas.width, canvas.height);
        }
    });
}

function drawMapBase(msg, ctx) {
    if (!msg || !msg.info) return;
    const { width, height } = msg.info;
    if (width === 0 || height === 0) {
        console.warn('Received map with 0 width or height');
        return;
    }

    const offscreen = document.createElement('canvas');
    offscreen.width = width;
    offscreen.height = height;
    const oCtx = offscreen.getContext('2d');
    const imgData = oCtx.createImageData(width, height);
    
    const isCoverage = (msg.info.origin.position.z === 999); // 密技：用 Z 分辨地圖類型
    
    for (let i = 0; i < msg.data.length; i++) {
        const val = msg.data[i];
        let r, g, b, a = 255;
        
        if (val === -1) { 
            r = g = b = 60; // 未知 (深灰)
        } else if (val === 0) { 
            r = g = b = 200; // 空地 (淺灰)
        } else if (val === 100) { 
            if (isCoverage) { 
                r = 0; g = 100; b = 255; a = 180; // 已覆蓋 (半透明藍)
            } else { 
                r = g = b = 0; // 障礙物 (黑)
            }
        } else {
            // 處理 1-99 之間的數值 (可能有些地圖會給中間值)
            const brightness = 200 - (val * 2);
            r = g = b = Math.max(0, brightness);
        }
        
        const row = Math.floor(i / width);
        const col = i % width;
        const idx = ((height - row - 1) * width + col) * 4;
        imgData.data[idx] = r; 
        imgData.data[idx+1] = g; 
        imgData.data[idx+2] = b; 
        imgData.data[idx+3] = a;
    }
    oCtx.putImageData(imgData, 0, 0);
    
    // 將座標原點移到地圖中心進行繪製
    ctx.drawImage(offscreen, -width/2, -height/2);
}

function drawOverlay(_, ctx) {
    if (!cachedMapMsg) return;
    const info = cachedMapMsg.info;

    // 1. 繪製目標區域
    if (cachedTargetPolygon && document.getElementById('layer-target').checked) {
        ctx.beginPath();
        cachedTargetPolygon.forEach((pt, i) => {
            const p = worldToCanvas(pt.x, pt.y, info);
            if (i === 0) ctx.moveTo(p.x, p.y); else ctx.lineTo(p.x, p.y);
        });
        ctx.closePath();
        ctx.fillStyle = 'rgba(0, 255, 0, 0.3)';
        ctx.fill();
        ctx.strokeStyle = '#00ff00';
        ctx.lineWidth = 2 / Camera.scale;
        ctx.stroke();
    }

    // 2. 繪製機器人
    if (cachedRobotPose) {
        const p = worldToCanvas(cachedRobotPose.position.x, cachedRobotPose.position.y, info);
        ctx.save();
        ctx.translate(p.x, p.y);
        // 畫圓圈
        ctx.beginPath();
        ctx.arc(0, 0, 8 / Camera.scale, 0, Math.PI * 2);
        ctx.fillStyle = 'yellow';
        ctx.fill();
        ctx.strokeStyle = 'white';
        ctx.stroke();
        // 畫方向箭頭
        ctx.rotate(getYawFromQuat(cachedRobotPose.orientation));
        ctx.beginPath();
        ctx.moveTo(0, 0);
        ctx.lineTo(15 / Camera.scale, 0);
        ctx.stroke();
        ctx.restore();
    }
}

function worldToCanvas(wx, wy, info) {
    return {
        x: (wx - info.origin.position.x) / info.resolution - info.width / 2,
        y: info.height / 2 - (wy - info.origin.position.y) / info.resolution
    };
}

function getYawFromQuat(q) {
    return Math.atan2(2.0 * (q.w * q.z + q.x * q.y), 1.0 - 2.0 * (q.y * q.y + q.z * q.z));
}
