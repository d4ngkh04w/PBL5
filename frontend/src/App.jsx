import { useEffect, useMemo, useRef, useState } from "react";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import { getSystemStatus, setEsp32StreamState, wsService, controlRotateTray, controlToggleDoor } from "./services/api";
import {
    BarChart3,
    LayoutDashboard,
    Menu,
    Power,
    RotateCw,
    Trash2,
    X,
} from "lucide-react";
import Dashboard from "./pages/Dashboard";
import Statistics from "./pages/Statistics";
import "./App.css";

const WASTE_TYPES = ["Nhựa", "Kim loại", "Giấy", "Khác"];

const formatTime = (date) =>
    date.toLocaleTimeString("vi-VN", {
        hour: "2-digit",
        minute: "2-digit",
        second: "2-digit",
    });

const createLog = (action, result) => ({
    action,
    result,
    time: formatTime(new Date()),
});

function App() {
    const [trayPosition, setTrayPosition] = useState(1);
    const [targetTray, setTargetTray] = useState(1);
    const [binWeights, setBinWeights] = useState({
        1: 0,
        2: 0,
        3: 0,
        4: 0,
    });
    const [doorOpen, setDoorOpen] = useState(false);
    const [toast, setToast] = useState("");
    const toastTimerRef = useRef(null);
    const [latestAi, setLatestAi] = useState({
        type: "Chưa có",
        confidence: 0,
        image: null,
    });
    const [logs, setLogs] = useState([]);
    const [isStreamActive, setIsStreamActive] = useState(true);
    const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

    const pushLog = (action, result) => {
        setLogs((prev) => [createLog(action, result), ...prev].slice(0, 8));
    };

    useEffect(() => {
        const loadSystemStatus = async () => {
            try {
                const status = await getSystemStatus();

                setTrayPosition(status.trayPosition ?? 1);
                setTargetTray(status.targetTray ?? 1);
                setDoorOpen(Boolean(status.doorOpen));
                setBinWeights({
                    1: Number(status.binWeights?.["1"] ?? status.binWeights?.[1] ?? 0),
                    2: Number(status.binWeights?.["2"] ?? status.binWeights?.[2] ?? 0),
                    3: Number(status.binWeights?.["3"] ?? status.binWeights?.[3] ?? 0),
                    4: Number(status.binWeights?.["4"] ?? status.binWeights?.[4] ?? 0),
                });

                if (status.latestAi) {
                    setLatestAi({
                        type: status.latestAi.type || "Chưa có",
                        confidence:
                            status.latestAi.confidence <= 1
                                ? Math.round(status.latestAi.confidence * 100)
                                : status.latestAi.confidence,
                        image: status.latestAi.image || null,
                    });
                }

                if (Array.isArray(status.logs)) {
                    setLogs(status.logs);
                }
            } catch (error) {
                pushLog("Lấy trạng thái backend", "Thất bại");
            }
        };

        loadSystemStatus();
    }, []);

    // --- WEBSOCKET CONNECTION ---
    useEffect(() => {
        wsService.connect();

        const handleNewTrashDetected = (data) => {
            console.log("🗑️  New trash detected:", data);

            // Backend returns: {"class": "hazardous", "confidence": 0.95, "image": "data:image/jpeg;..."}
            const { class: trashClass, confidence, image, weight } = data;

            // Map backend class names to frontend type names
            const typeMap = {
                hazardous: "Kim loại",
                non_recyclable: "Khác",
                organic: "Giấy",
                recycling: "Nhựa",
            };

            const binMap = {
                recycling: 1,
                organic: 2,
                hazardous: 3,
                non_recyclable: 4,
            };

            const type = typeMap[trashClass] || "Khác";
            const confidencePercent = Math.round(confidence * 100);
            const binIndex = binMap[trashClass];

            if (binIndex && typeof weight === "number") {
                setBinWeights((prevWeights) => ({
                    ...prevWeights,
                    [binIndex]: Number((prevWeights[binIndex] + weight).toFixed(2)),
                }));
            }

            setLatestAi({ type, confidence: confidencePercent, image });
            pushLog("AI Nhận diện rác", `${type} (${confidencePercent}%)`);
            showSuccess(`Nhận diện: ${type} - ${confidencePercent}%`);
        };

        const handleSystemLog = (data) => {
            if (Array.isArray(data)) {
                setLogs(data);
            }
        };

        wsService.on("NEW_TRASH_DETECTED", handleNewTrashDetected);
        wsService.on("SYSTEM_LOG", handleSystemLog);

        return () => {
            wsService.off("NEW_TRASH_DETECTED", handleNewTrashDetected);
            wsService.off("SYSTEM_LOG", handleSystemLog);
            wsService.disconnect();
        };
    }, []);

    const showSuccess = (message) => {
        setToast(message);
        window.clearTimeout(toastTimerRef.current);
        toastTimerRef.current = window.setTimeout(() => setToast(""), 2400);
    };

    const handleRotateTray = async () => {
        const next = targetTray;

        if (trayPosition === next) {
            showSuccess(`Mâm đã ở sẵn ngăn ${next}`);
            return;
        }

        const success = await controlRotateTray(next);
        if (success) {
            setTrayPosition(next);
            showSuccess(`Đã ra lệnh xoay mâm sang ngăn ${next}`);
        } else {
            showSuccess("Lỗi khi xoay mâm. Kiểm tra kết nối ESP32.");
        }
    };

    const handleToggleDoor = async () => {
        const next = !doorOpen;
        const success = await controlToggleDoor(next);
        if (success) {
            setDoorOpen(next);
            showSuccess(next ? "Đã ra lệnh mở cửa" : "Đã ra lệnh đóng cửa");
        } else {
            showSuccess("Lỗi khi điều khiển cửa. Kiểm tra kết nối ESP32.");
        }
    };

    const handleStreamToggle = async () => {
        const next = !isStreamActive;
        const ok = await setEsp32StreamState(next);

        if (ok) {
            setIsStreamActive(next);
            showSuccess(next ? "Đã bật stream" : "Đã tắt stream");
            return;
        }

        showSuccess("Không điều khiển được stream ESP32");
    };

    const dashboardProps = useMemo(
        () => ({
            trayPosition,
            targetTray,
            binWeights,
            doorOpen,
            latestAi,
            logs,
            toast,
            isStreamActive,
            onStreamToggle: handleStreamToggle,
        }),
        [
            trayPosition,
            targetTray,
            binWeights,
            doorOpen,
            latestAi,
            logs,
            toast,
            isStreamActive,
            handleStreamToggle,
        ],
    );

    return (
        <BrowserRouter>
            <div className="app-shell">
                <aside className="sidebar" aria-label="Thanh điều hướng">
                    <div className="sidebar-top">
                        <div className="brand">
                            <div className="brand-icon">
                                <Trash2 size={20} />
                            </div>
                            <span>Smart Bin</span>
                        </div>
                        <button
                            className="mobile-menu-btn"
                            onClick={() => setMobileMenuOpen((v) => !v)}
                            aria-label={mobileMenuOpen ? "Đóng menu" : "Mở menu"}
                            aria-expanded={mobileMenuOpen}
                        >
                            {mobileMenuOpen ? <X size={22} /> : <Menu size={22} />}
                        </button>
                    </div>

                    <div className={`sidebar-collapse ${mobileMenuOpen ? "open" : ""}`}>
                        <nav className="menu" aria-label="Menu chính">
                            <NavLink
                                to="/"
                                end
                                className={({ isActive }) =>
                                    `menu-item ${isActive ? "active" : ""}`
                                }
                                onClick={() => setMobileMenuOpen(false)}
                            >
                                <LayoutDashboard size={18} />
                                <span>Dashboard</span>
                            </NavLink>
                            <NavLink
                                to="/statistics"
                                className={({ isActive }) =>
                                    `menu-item ${isActive ? "active" : ""}`
                                }
                                onClick={() => setMobileMenuOpen(false)}
                            >
                                <BarChart3 size={18} />
                                <span>Thống kê</span>
                            </NavLink>
                        </nav>

                        <div className="control-panel">
                            <p className="control-title">Bộ điều khiển</p>
                            <label className="control-label" htmlFor="target-tray">
                                Chọn ngăn muốn xoay tới
                            </label>
                            <select
                                id="target-tray"
                                className="control-select"
                                value={targetTray}
                                onChange={(event) =>
                                    setTargetTray(Number(event.target.value))
                                }
                            >
                                <option value={1}>Ngăn 1</option>
                                <option value={2}>Ngăn 2</option>
                                <option value={3}>Ngăn 3</option>
                                <option value={4}>Ngăn 4</option>
                            </select>
                            <button
                                type="button"
                                className="control-btn"
                                onClick={handleRotateTray}
                            >
                                <span>Xoay mâm tới ngăn đã chọn</span>
                                <RotateCw size={16} />
                            </button>
                            <button
                                type="button"
                                className="control-btn secondary"
                                onClick={handleToggleDoor}
                            >
                                <span>{doorOpen ? "Đóng cửa" : "Mở cửa"}</span>
                                <Power size={16} />
                            </button>
                        </div>
                    </div>
                </aside>

                <main className="content-area">
                    <Routes>
                        <Route
                            path="/"
                            element={<Dashboard {...dashboardProps} />}
                        />
                        <Route
                            path="/statistics"
                            element={
                                <Statistics
                                    logs={logs}
                                    trayPosition={trayPosition}
                                    latestAi={latestAi}
                                />
                            }
                        />
                    </Routes>
                </main>
            </div>
        </BrowserRouter>
    );
}

export default App;
