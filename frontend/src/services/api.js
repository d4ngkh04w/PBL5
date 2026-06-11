const WS_URL = import.meta.env.VITE_WS_URL || `ws://${window.location.hostname}:5762/ws`;
export const FRONTEND_API_KEY = import.meta.env.VITE_API_KEY || "";
const ESP32_STREAM_CONTROL_URL =
    import.meta.env.VITE_ESP32_STREAM_CONTROL_URL || "";

class WebSocketService {
    constructor() {
        this.ws = null;
        this.listeners = {};
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 3000;
    }

    connect(url = WS_URL) {
        return new Promise((resolve, reject) => {
            try {
                this.ws = new WebSocket(url);

                this.ws.onopen = () => {
                    console.log("✅ WebSocket connected");
                    this.reconnectAttempts = 0;
                    this.emit("connected");
                    resolve();
                };

                this.ws.onmessage = (event) => {
                    const message = JSON.parse(event.data);
                    console.log("📨 Message received:", message);
                    this.emit(message.event, message.data);
                };

                this.ws.onerror = (error) => {
                    console.error("❌ WebSocket error:", error);
                    this.emit("error", error);
                    reject(error);
                };

                this.ws.onclose = () => {
                    console.log("🔌 WebSocket disconnected");
                    this.emit("disconnected");
                    this.attemptReconnect(url);
                };
            } catch (error) {
                reject(error);
            }
        });
    }

    attemptReconnect(url) {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(
                `🔄 Reconnecting... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`,
            );
            setTimeout(() => this.connect(url), this.reconnectDelay);
        } else {
            console.error("❌ Max reconnect attempts reached");
            this.emit("reconnect_failed");
        }
    }

    on(event, callback) {
        if (!this.listeners[event]) {
            this.listeners[event] = [];
        }
        this.listeners[event].push(callback);
    }

    off(event, callback) {
        if (!this.listeners[event]) return;
        this.listeners[event] = this.listeners[event].filter(
            (cb) => cb !== callback,
        );
    }

    emit(event, data) {
        if (!this.listeners[event]) return;
        this.listeners[event].forEach((callback) => callback(data));
    }

    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }

    isConnected() {
        return this.ws && this.ws.readyState === WebSocket.OPEN;
    }
}

export const wsService = new WebSocketService();

export async function setEsp32StreamState(enabled) {
    if (!ESP32_STREAM_CONTROL_URL) {
        console.warn("VITE_ESP32_STREAM_CONTROL_URL is not configured");
        return false;
    }

    try {
        const response = await fetch(
            `${ESP32_STREAM_CONTROL_URL}?enabled=${enabled ? 1 : 0}`,
        );
        return response.ok;
    } catch (error) {
        console.error("Failed to control ESP32 stream:", error);
        return false;
    }
}

export async function getSystemStatus() {
    const API_BASE_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5762/api`;
    try {
        const response = await fetch(`${API_BASE_URL}/status`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Failed to fetch system status:", error);
        throw error;
    }
}

export async function getStatistics() {
    const API_BASE_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5762/api`;
    try {
        const response = await fetch(`${API_BASE_URL}/statistics`);
        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }
        return await response.json();
    } catch (error) {
        console.error("Failed to fetch statistics:", error);
        throw error;
    }
}

export async function controlRotateTray(trayId) {
    const API_BASE_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5762/api`;
    try {
        const response = await fetch(`${API_BASE_URL}/control/rotate`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ tray_id: trayId }),
        });
        return response.ok;
    } catch (error) {
        console.error("Failed to control rotate tray:", error);
        return false;
    }
}

export async function controlToggleDoor(isOpen) {
    const API_BASE_URL = import.meta.env.VITE_API_URL || `http://${window.location.hostname}:5762/api`;
    try {
        const action = isOpen ? "open" : "close";
        const response = await fetch(`${API_BASE_URL}/control/door`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({ action }),
        });
        return response.ok;
    } catch (error) {
        console.error("Failed to control toggle door:", error);
        return false;
    }
}
