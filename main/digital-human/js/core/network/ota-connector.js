import { log } from '../../utils/logger.js?v=0205';

export async function webSocketConnect(otaUrl, config) {
    if (!validateConfig(config)) {
        return;
    }

    const otaResult = await sendOTA(otaUrl, config);
    if (!otaResult) {
        log('Unable to get websocket information from OTA server', 'error');
        return;
    }

    const { websocket } = otaResult;
    if (!websocket || !websocket.url) {
        log(`OTA response missing websocket.url: ${JSON.stringify(otaResult)}`, 'error');
        return;
    }

    const connUrl = buildReachableWebSocketUrl(websocket.url, otaUrl);

    if (websocket.token) {
        if (websocket.token.startsWith('Bearer ')) {
            connUrl.searchParams.append('authorization', websocket.token);
        } else {
            connUrl.searchParams.append('authorization', 'Bearer ' + websocket.token);
        }
    }

    connUrl.searchParams.append('device-id', config.deviceId);
    connUrl.searchParams.append('client-id', config.clientId);

    const wsurl = connUrl.toString();
    log(`Connecting to websocket: ${wsurl}`, 'info');

    const serverUrlInput = document.getElementById('serverUrl');
    if (serverUrlInput) {
        serverUrlInput.value = wsurl;
    }

    return new WebSocket(wsurl);
}

function buildReachableWebSocketUrl(websocketUrl, otaUrl) {
    const connUrl = new URL(websocketUrl);
    const ota = new URL(otaUrl, window.location.href);

    if (connUrl.protocol !== 'ws:' && connUrl.protocol !== 'wss:') {
        throw new Error(`Invalid websocket protocol: ${connUrl.protocol}`);
    }

    const otaHost = ota.hostname;
    const wsHost = connUrl.hostname;
    const wsUsesLoopback = wsHost === '0.0.0.0' || wsHost === '127.0.0.1' || wsHost === 'localhost';
    const wsUsesDockerBridge = isDockerBridgeHost(wsHost);
    const otaUsesLoopback = otaHost === '127.0.0.1' || otaHost === 'localhost';

    // OTA can return a server-local host. If the browser reached OTA through a
    // different host, use that host for the websocket endpoint too.
    if (wsUsesLoopback && !otaUsesLoopback) {
        log(`OTA returned websocket host ${wsHost}; using OTA host ${otaHost} instead`, 'warning');
        connUrl.hostname = otaHost;
    }

    if (wsUsesDockerBridge) {
        log(`OTA returned Docker bridge websocket host ${wsHost}; using OTA host ${otaHost} instead`, 'warning');
        connUrl.hostname = otaHost;
    }

    if (window.location.protocol === 'https:' && connUrl.protocol === 'ws:') {
        log('Current page is HTTPS; switching websocket protocol to WSS', 'warning');
        connUrl.protocol = 'wss:';
    }

    return connUrl;
}

function isDockerBridgeHost(hostname) {
    const parts = hostname.split('.').map((part) => Number(part));
    if (parts.length !== 4 || parts.some((part) => !Number.isInteger(part) || part < 0 || part > 255)) {
        return false;
    }

    // Docker's default bridge networks commonly use 172.17.0.0/16 through
    // 172.31.0.0/16. These addresses are usually unreachable from browsers on
    // the host machine even when the container port is published.
    return parts[0] === 172 && parts[1] >= 17 && parts[1] <= 31;
}

function validateConfig(config) {
    if (!config.deviceMac) {
        log('Device MAC address cannot be empty', 'error');
        return false;
    }
    if (!config.clientId) {
        log('Client ID cannot be empty', 'error');
        return false;
    }
    return true;
}

async function sendOTA(otaUrl, config) {
    try {
        const res = await fetch(otaUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Device-Id': config.deviceId,
                'Client-Id': config.clientId
            },
            body: JSON.stringify({
                version: 0,
                uuid: '',
                application: {
                    name: 'xiaozhi-web-test',
                    version: '1.0.0',
                    compile_time: '2025-04-16 10:00:00',
                    idf_version: '4.4.3',
                    elf_sha256: '1234567890abcdef1234567890abcdef1234567890abcdef'
                },
                ota: { label: 'xiaozhi-web-test' },
                board: {
                    type: config.deviceName,
                    ssid: 'xiaozhi-web-test',
                    rssi: 0,
                    channel: 0,
                    ip: '192.168.1.1',
                    mac: config.deviceMac
                },
                flash_size: 0,
                minimum_free_heap_size: 0,
                mac_address: config.deviceMac,
                chip_model_name: '',
                chip_info: { model: 0, cores: 0, revision: 0, features: 0 },
                partition_table: [{ label: '', type: 0, subtype: 0, address: 0, size: 0 }]
            })
        });

        if (!res.ok) {
            throw new Error(`${res.status} ${res.statusText}`);
        }

        return await res.json();
    } catch (err) {
        log(`OTA request failed: ${err.message || err}`, 'error');
        return null;
    }
}
