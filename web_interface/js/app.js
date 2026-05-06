// 使用 DOMContentLoaded 確保 HTML 元素都已經準備好
document.addEventListener('DOMContentLoaded', () => {
    const ros = new ROSLIB.Ros({ url: 'ws://' + window.location.hostname + ':9090' });
    const statusBadge = document.getElementById('status');

    // 初始化畫布大小
    function resizeCanvases() {
        const viewport = document.getElementById('viewport');
        if (!viewport) return;
        
        const width = viewport.clientWidth;
        const height = viewport.clientHeight;
        
        if (width === 0 || height === 0) {
            // 如果還沒取得尺寸，稍後再試
            setTimeout(resizeCanvases, 500);
            return;
        }

        ['canvas-map', 'canvas-coverage', 'canvas-overlay'].forEach(id => {
            const canvas = document.getElementById(id);
            if (canvas) {
                canvas.width = width;
                canvas.height = height;
            }
        });
        console.log(`Canvases resized to: ${width}x${height}`);
        
        // 如果已經有地圖資料，重設攝影機並重新繪製
        if (cachedMapMsg && Camera.x === 0) {
            Camera.reset(width, height);
        }
        renderAll();
    }

    window.addEventListener('resize', resizeCanvases);
    // 延遲一下下執行，確保 CSS 佈局已完成
    setTimeout(resizeCanvases, 100);

    ros.on('connection', () => {
        statusBadge.innerText = '已連線';
        statusBadge.className = 'badge badge-success shadow-sm';
        console.log('Connected to rosbridge');
    });

    ros.on('error', (error) => {
        console.warn('Error connecting to rosbridge: ', error);
        statusBadge.innerText = '連線錯誤';
        statusBadge.className = 'badge badge-danger shadow-sm';
    });

    ros.on('close', () => {
        console.log('Connection to rosbridge closed');
        statusBadge.innerText = '連線斷開';
        statusBadge.className = 'badge badge-warning shadow-sm';
    });

    // ROS Topics 訂閱
    const mapTopic = new ROSLIB.Topic({ ros, name: '/map', messageType: 'nav_msgs/OccupancyGrid' });
    mapTopic.subscribe((msg) => {
        console.log('Received map:', msg.info.width, 'x', msg.info.height);
        if (!cachedMapMsg) {
            const viewport = document.getElementById('viewport');
            Camera.reset(viewport.clientWidth, viewport.clientHeight);
        }
        cachedMapMsg = msg;
        document.getElementById('map-info').innerText = `${msg.info.width}x${msg.info.height} (${msg.info.resolution}m/px)`;
        renderAll();
    });

    const coverageTopic = new ROSLIB.Topic({ ros, name: '/ccpp/coverage_map', messageType: 'nav_msgs/OccupancyGrid' });
    coverageTopic.subscribe((msg) => {
        msg.info.origin.position.z = 999; // 標記為覆蓋圖層
        cachedCoverageMsg = msg;
        renderAll();
    });

    const poseTopic = new ROSLIB.Topic({ ros, name: '/ccpp/robot_pose', messageType: 'geometry_msgs/PoseStamped' });

    const handlePose = (pose) => {
        cachedRobotPose = pose;
        document.getElementById('robot-pos').innerText = `X:${pose.position.x.toFixed(2)}, Y:${pose.position.y.toFixed(2)}`;
        renderAll();
    };

    poseTopic.subscribe((msg) => handlePose(msg.pose));

    const targetTopic = new ROSLIB.Topic({ ros, name: '/ccpp/target_polygon', messageType: 'geometry_msgs/PolygonStamped' });
    targetTopic.subscribe((msg) => {
        cachedTargetPolygon = msg.polygon.points;
        renderAll();
    });

    const progressTopic = new ROSLIB.Topic({ ros, name: '/ccpp/task_progress', messageType: 'std_msgs/Float32' });
    progressTopic.subscribe((msg) => {
        const p = (msg.data * 100).toFixed(1);
        document.getElementById('overall-progress').style.width = p + '%';
        document.getElementById('progress-text').innerText = p + '%';
    });

    // UI 控制事件
    document.getElementById('btn-zoom-in').onclick = () => { Camera.scale *= 1.2; renderAll(); };
    document.getElementById('btn-zoom-out').onclick = () => { Camera.scale /= 1.2; renderAll(); };
    document.getElementById('btn-rotate-l').onclick = () => { Camera.rotation -= 15; renderAll(); };
    document.getElementById('btn-rotate-r').onclick = () => { Camera.rotation += 15; renderAll(); };
    document.getElementById('btn-reset').onclick = () => { 
        const viewport = document.getElementById('viewport');
        Camera.reset(viewport.clientWidth, viewport.clientHeight); 
        renderAll(); 
    };

    // Teleop Control
    const cmdVelTopic = new ROSLIB.Topic({
        ros: ros,
        name: '/cmd_vel',
        messageType: 'geometry_msgs/Twist'
    });

    const linearSpeed = 0.22;
    const angularSpeed = 1.0;
    
    let teleopTimer = null;
    let currentLinear = 0;
    let currentAngular = 0;

    function startPublishing(linear, angular) {
        currentLinear = linear;
        currentAngular = angular;
        if (!teleopTimer) {
            teleopTimer = setInterval(() => {
                const twist = new ROSLIB.Message({
                    linear: { x: currentLinear, y: 0.0, z: 0.0 },
                    angular: { x: 0.0, y: 0.0, z: currentAngular }
                });
                cmdVelTopic.publish(twist);
            }, 100); // 10Hz
        }
    }

    function stopPublishing() {
        currentLinear = 0;
        currentAngular = 0;
        if (teleopTimer) {
            clearInterval(teleopTimer);
            teleopTimer = null;
            const twist = new ROSLIB.Message({
                linear: { x: 0.0, y: 0.0, z: 0.0 },
                angular: { x: 0.0, y: 0.0, z: 0.0 }
            });
            cmdVelTopic.publish(twist);
        }
    }

    // 滑鼠控制
    const bindBtn = (id, lin, ang) => {
        const btn = document.getElementById(id);
        if (!btn) return;
        btn.onmousedown = () => startPublishing(lin, ang);
        btn.onmouseup = stopPublishing;
        btn.onmouseleave = stopPublishing;
        
        btn.ontouchstart = (e) => { e.preventDefault(); startPublishing(lin, ang); };
        btn.ontouchend = (e) => { e.preventDefault(); stopPublishing(); };
    };

    bindBtn('btn-teleop-w', linearSpeed, 0);
    bindBtn('btn-teleop-x', -linearSpeed, 0);
    bindBtn('btn-teleop-a', 0, angularSpeed);
    bindBtn('btn-teleop-d', 0, -angularSpeed);
    
    const stopBtn = document.getElementById('btn-teleop-s');
    if (stopBtn) stopBtn.onclick = stopPublishing;

    // 鍵盤控制
    const keyState = {};
    window.addEventListener('keydown', (e) => {
        if (e.target.tagName.toLowerCase() === 'input' || e.target.tagName.toLowerCase() === 'textarea') return;
        const key = e.key.toLowerCase();
        if (keyState[key]) return; // 避免持續按壓重複觸發
        keyState[key] = true;
        
        let lin = 0, ang = 0;
        if (keyState['w']) lin = linearSpeed;
        else if (keyState['x']) lin = -linearSpeed;
        if (keyState['a']) ang = angularSpeed;
        else if (keyState['d']) ang = -angularSpeed;
        
        if (lin !== 0 || ang !== 0) startPublishing(lin, ang);
        else if (key === 's') stopPublishing();
    });

    window.addEventListener('keyup', (e) => {
        const key = e.key.toLowerCase();
        keyState[key] = false;
        
        let lin = 0, ang = 0;
        if (keyState['w']) lin = linearSpeed;
        else if (keyState['x']) lin = -linearSpeed;
        if (keyState['a']) ang = angularSpeed;
        else if (keyState['d']) ang = -angularSpeed;

        if (lin === 0 && ang === 0) stopPublishing();
        else startPublishing(lin, ang);
    });

    // 圖層切換
    ['layer-map', 'layer-coverage', 'layer-target'].forEach(id => {
        document.getElementById(id).onchange = renderAll;
    });

    // 滑鼠拖曳平移
    const viewport = document.getElementById('viewport');
    viewport.onmousedown = (e) => {
        Camera.isDragging = true;
        Camera.lastMouseX = e.clientX;
        Camera.lastMouseY = e.clientY;
    };
    window.onmousemove = (e) => {
        if (!Camera.isDragging) return;
        Camera.x += (e.clientX - Camera.lastMouseX);
        Camera.y += (e.clientY - Camera.lastMouseY);
        Camera.lastMouseX = e.clientX;
        Camera.lastMouseY = e.clientY;
        renderAll();
    };
    window.onmouseup = () => { Camera.isDragging = false; };

    // 滾輪縮放
    viewport.onwheel = (e) => {
        e.preventDefault();
        const factor = e.deltaY > 0 ? 0.9 : 1.1;
        Camera.scale *= factor;
        renderAll();
    };

    // ROS Service 調用
    const startSrv = new ROSLIB.Service({ ros, name: '/ccpp/start', serviceType: 'std_srvs/Trigger' });
    const stopSrv = new ROSLIB.Service({ ros, name: '/ccpp/stop', serviceType: 'std_srvs/Trigger' });
    const resetSrv = new ROSLIB.Service({ ros, name: '/ccpp/reset_coverage', serviceType: 'std_srvs/Trigger' });

    document.getElementById('btn-start').onclick = () => {
        startSrv.callService(new ROSLIB.ServiceRequest(), (res) => { alert(res.message); });
    };
    document.getElementById('btn-stop').onclick = () => {
        stopSrv.callService(new ROSLIB.ServiceRequest(), (res) => { alert(res.message); });
    };
    document.getElementById('btn-reset-coverage').onclick = () => {
        if (confirm('確定要清除當前覆蓋路徑並重新見圖嗎？')) {
            resetSrv.callService(new ROSLIB.ServiceRequest(), (res) => { console.log(res.message); });
        }
    };
});
