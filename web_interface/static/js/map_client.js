/**
 * map_client.js — 地圖監控前端邏輯
 *
 * 資料流：
 *   Flask /api/events (SSE) ──► 收到 map_update 事件
 *       └─► 預先載入新圖片 (Image preload)
 *               └─► 載入完成後替換 <img src>，消除閃爍
 *
 * SSE 斷線自動重連（3 秒後重試），不需要 WebSocket 或 rosbridge。
 */

(function () {
    'use strict';

    // ── DOM 元素 ────────────────────────────────────────────────────────────
    var mapImg       = document.getElementById('map-img');
    var noMapEl      = document.getElementById('no-map');
    var statusBadge  = document.getElementById('status');
    var sseStatusEl  = document.getElementById('sse-status');
    var lastUpdateEl = document.getElementById('last-update');
    var mapSizeEl    = document.getElementById('map-size');
    var mapResEl     = document.getElementById('map-resolution');
    var mapVerEl     = document.getElementById('map-version');
    var mapCaption   = document.getElementById('map-caption');

    // ── 狀態更新輔助函式 ────────────────────────────────────────────────────

    function setConnected() {
        statusBadge.textContent = '已連線';
        statusBadge.className   = 'badge badge--connected';
        sseStatusEl.textContent = '串流中';
    }

    function setDisconnected() {
        statusBadge.textContent = '已斷線';
        statusBadge.className   = 'badge badge--disconnected';
        sseStatusEl.textContent = '斷線';
    }

    function setReconnecting() {
        statusBadge.textContent = '重連中...';
        statusBadge.className   = 'badge badge--reconnecting';
        sseStatusEl.textContent = '重連中';
    }

    // ── 地圖圖片更新 ────────────────────────────────────────────────────────

    /**
     * 先在背景預載新圖，載入成功後才替換顯示圖，避免圖片更新時的閃爍。
     * URL 附加版本號 ?v=N 作為快取破壞參數，強制瀏覽器重新請求。
     *
     * @param {number} version - 地圖版本號（由 SSE 事件帶入）
     * @param {Object} meta    - 地圖元數據（width, height, resolution）
     */
    function updateMap(version, meta) {
        var url = '/api/map/image?v=' + version;
        var temp = new Image();

        temp.onload = function () {
            mapImg.src          = temp.src;
            mapImg.style.display = 'block';
            noMapEl.style.display = 'none';

            // 更新資訊面板
            mapSizeEl.textContent = meta.width + ' × ' + meta.height + ' px';
            mapResEl.textContent  = meta.resolution.toFixed(4) + ' m/px';
            mapVerEl.textContent  = '#' + version;
            lastUpdateEl.textContent = new Date().toLocaleTimeString('zh-TW');
            mapCaption.textContent   =
                meta.width + '×' + meta.height + 'px  ·  ' +
                meta.resolution.toFixed(4) + ' m/px  ·  版本 #' + version;
        };

        temp.onerror = function () {
            // 圖片載入失敗（地圖尚未就緒），靜默等待下一次更新
        };

        temp.src = url;
    }

    // ── SSE 連線管理 ────────────────────────────────────────────────────────

    var es = null;

    function connectSSE() {
        if (es) { es.close(); }

        es = new EventSource('/api/events');

        es.onopen = function () {
            setConnected();
        };

        /**
         * 每次收到 SSE 訊息時觸發。
         * 伺服器推送的格式：{ type, version, width, height, resolution }
         * 心跳行 (": heartbeat") 不會觸發此事件，瀏覽器自動忽略。
         */
        es.onmessage = function (e) {
            var data = JSON.parse(e.data);
            if (data.type === 'map_update') {
                updateMap(data.version, data);
            }
        };

        es.onerror = function () {
            setDisconnected();
            es.close();
            es = null;
            // 3 秒後自動重連
            setReconnecting();
            setTimeout(connectSSE, 3000);
        };
    }

    // ── 初始化 ──────────────────────────────────────────────────────────────

    // 頁面載入時先嘗試取得現有地圖（伺服器可能已有快取）
    // 使用版本 0 觸發一次載入，若無地圖則靜默忽略
    updateMap(0, { width: '?', height: '?', resolution: 0 });

    connectSSE();

})();
