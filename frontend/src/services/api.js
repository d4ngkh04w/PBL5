const WS_URL = import.meta.env.VITE_WS_URL;
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
