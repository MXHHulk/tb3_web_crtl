const ros = new ROSLIB.Ros({ url: 'ws://' + window.location.hostname + ':9090' });
let currentMapInfo = null;
let currentTargetPolygon = null;

const statusBadge = document.getElementById('status');

ros.on('connection', () => {
    statusBadge.innerText = '已連線';
    statusBadge.className = 'badge badge-success';
});

// Topics
const mapTopic = new ROSLIB.Topic({ ros, name: '/map', messageType: 'nav_msgs/OccupancyGrid' });
mapTopic.subscribe((msg) => {
    currentMapInfo = msg.info;
    renderMap(msg, document.getElementById('canvas-map'));
});

const targetTopic = new ROSLIB.Topic({ ros, name: '/ccpp/target_polygon', messageType: 'geometry_msgs/PolygonStamped' });
targetTopic.subscribe((msg) => {
    currentTargetPolygon = msg.polygon.points;
});

const poseTopic = new ROSLIB.Topic({ ros, name: '/amcl_pose', messageType: 'geometry_msgs/PoseWithCovarianceStamped' });
poseTopic.subscribe((msg) => {
    document.getElementById('robot-pos').innerText = `X:${msg.pose.pose.position.x.toFixed(2)}, Y:${msg.pose.pose.position.y.toFixed(2)}`;
    if (currentMapInfo) {
        const canvas = document.getElementById('canvas-overlay');
        if (currentTargetPolygon) drawTargetPolygon(currentTargetPolygon, canvas, currentMapInfo);
        drawRobot(msg.pose.pose, canvas, currentMapInfo);
    }
});

// Services
const startSrv = new ROSLIB.Service({ ros, name: '/ccpp/start', serviceType: 'std_srvs/Trigger' });
const stopSrv = new ROSLIB.Service({ ros, name: '/ccpp/stop', serviceType: 'std_srvs/Trigger' });

document.getElementById('btn-start').addEventListener('click', () => {
    startSrv.callService(new ROSLIB.ServiceRequest(), (res) => { alert(res.message); });
});

document.getElementById('btn-stop').addEventListener('click', () => {
    stopSrv.callService(new ROSLIB.ServiceRequest(), (res) => { alert(res.message); });
});
