import { useMemo, useRef, useState } from "react";
import { BrowserRouter, NavLink, Route, Routes } from "react-router-dom";
import {
    BarChart3,
    LayoutDashboard,
    Power,
    RotateCw,
    Trash2,
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
    const [targetTray, setTargetTray] = useState(2);
    const [binWeights, setBinWeights] = useState({
        1: 1.2,
        2: 0.8,
        3: 1.5,
        4: 0.6,
    });
    const [doorOpen, setDoorOpen] = useState(false);
    const [toast, setToast] = useState("");
    const toastTimerRef = useRef(null);
    const [latestAi, setLatestAi] = useState({
        type: "Nhựa",
        confidence: 96.3,
    });
    const [logs, setLogs] = useState([
        createLog("Khởi động hệ thống", "Thành công"),
        createLog("Đồng bộ cảm biến", "Thành công"),
    ]);

    const pushLog = (action, result) => {
        setLogs((prev) => [createLog(action, result), ...prev].slice(0, 8));
    };

    const showSuccess = (message) => {
        setToast(message);
        window.clearTimeout(toastTimerRef.current);
        toastTimerRef.current = window.setTimeout(() => setToast(""), 2400);
    };

    const handleRotateTray = () => {
        setTrayPosition((prev) => {
            const next = targetTray;

            if (prev === next) {
                showSuccess(`Mâm đã ở sẵn ngăn ${next}`);
                pushLog("Xoay mâm", `Không đổi (đã ở vị trí ${next})`);
                return prev;
            }

            const type = WASTE_TYPES[(next - 1) % WASTE_TYPES.length];
            const confidence = Number((90 + Math.random() * 9.8).toFixed(1));
            const addedWeight = Number((0.05 + Math.random() * 0.3).toFixed(2));

            setBinWeights((prevWeights) => ({
                ...prevWeights,
                [next]: Number((prevWeights[next] + addedWeight).toFixed(2)),
            }));

            setLatestAi({ type, confidence });
            pushLog("Xoay mâm", `Thành công (vị trí ${next})`);
            showSuccess(`Đã xoay mâm sang ngăn ${next}`);

            return next;
        });
    };

    const handleToggleDoor = () => {
        setDoorOpen((prev) => {
            const next = !prev;
            const actionLabel = next ? "Mở cửa" : "Đóng cửa";
            pushLog(actionLabel, "Thành công");
            showSuccess(next ? "Đã mở cửa sập" : "Đã đóng cửa sập");
            return next;
        });
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
        }),
        [trayPosition, targetTray, binWeights, doorOpen, latestAi, logs, toast],
    );

    return (
        <BrowserRouter>
            <div className="app-shell">
                <aside className="sidebar">
                    <div className="brand">
                        <Trash2 size={18} />
                        <span>Smart Bin</span>
                    </div>

                    <nav className="menu">
                        <NavLink
                            to="/"
                            end
                            className={({ isActive }) =>
                                `menu-item ${isActive ? "active" : ""}`
                            }
                        >
                            <LayoutDashboard size={18} />
                            <span>Dashboard</span>
                        </NavLink>
                        <NavLink
                            to="/statistics"
                            className={({ isActive }) =>
                                `menu-item ${isActive ? "active" : ""}`
                            }
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
