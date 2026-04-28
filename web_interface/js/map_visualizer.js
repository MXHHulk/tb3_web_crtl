/**
 * CCPP 視覺化工具 - 還原版 (靜態顯示)
 */

function renderMap(message, canvas) {
    const ctx = canvas.getContext('2d');
    const { width, height } = message.info;
    canvas.width = width;
    canvas.height = height;

    const imageData = ctx.createImageData(width, height);
    const data = message.data;

    for (let i = 0; i < data.length; i++) {
        const val = data[i];
        let r, g, b;
        if (val === -1) { r = g = b = 100; }
        else if (val === 0) { r = g = b = 255; }
        else { r = g = b = 0; }
        
        const row = Math.floor(i / width);
        const col = i % width;
        const index = ((height - row - 1) * width + col) * 4;
        
        imageData.data[index] = r;
        imageData.data[index+1] = g;
        imageData.data[index+2] = b;
        imageData.data[index+3] = 255;
    }
    ctx.putImageData(imageData, 0, 0);

    // 同步 Overlay
    ["canvas-coverage", "canvas-overlay"].forEach(id => {
        const c = document.getElementById(id);
        if (c) {
            c.width = width;
            c.height = height;
        }
    });
}

function mapToCanvas(mx, my, mapInfo) {
    const px = (mx - mapInfo.origin.position.x) / mapInfo.resolution;
    const py = mapInfo.height - (my - mapInfo.origin.position.y) / mapInfo.resolution;
    return { x: px, y: py };
}

function drawTargetPolygon(points, canvas, mapInfo) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!points || points.length < 3) return;
    
    ctx.beginPath();
    const start = mapToCanvas(points[0].x, points[0].y, mapInfo);
    ctx.moveTo(start.x, start.y);
    for (let i = 1; i < points.length; i++) {
        const p = mapToCanvas(points[i].x, points[i].y, mapInfo);
        ctx.lineTo(p.x, p.y);
    }
    ctx.closePath();
    ctx.fillStyle = 'rgba(0, 255, 0, 0.4)';
    ctx.fill();
    ctx.strokeStyle = '#00ff00';
    ctx.lineWidth = 2;
    ctx.stroke();
}

function drawRobot(pose, canvas, mapInfo) {
    const ctx = canvas.getContext('2d');
    const p = mapToCanvas(pose.position.x, pose.position.y, mapInfo);
    ctx.fillStyle = 'yellow';
    ctx.beginPath();
    ctx.arc(p.x, p.y, 5, 0, Math.PI * 2);
    ctx.fill();
}
