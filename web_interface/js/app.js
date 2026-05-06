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

    const poseTopicAMCL = new ROSLIB.Topic({ ros, name: '/amcl_pose', messageType: 'geometry_msgs/PoseWithCovarianceStamped' });
    const poseTopicOdom = new ROSLIB.Topic({ ros, name: '/odom', messageType: 'nav_msgs/Odometry' });

    const handlePose = (pose) => {
        cachedRobotPose = pose;
        document.getElementById('robot-pos').innerText = `X:${pose.position.x.toFixed(2)}, Y:${pose.position.y.toFixed(2)}`;
        renderAll();
    };

    poseTopicAMCL.subscribe((msg) => handlePose(msg.pose.pose));
    poseTopicOdom.subscribe((msg) => {
        // 只有在沒有 AMCL 資料時才使用 Odom
        if (!cachedRobotPose || (Date.now() - lastAmclTime > 5000)) {
            handlePose(msg.pose.pose);
        }
    });
    let lastAmclTime = 0;
    poseTopicAMCL.subscribe(() => lastAmclTime = Date.now());

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
