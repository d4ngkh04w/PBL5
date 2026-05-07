import {
    Activity,
    Camera,
    CheckCircle2,
    Layers3,
    Sparkles,
    Play,
    Pause,
} from "lucide-react";
import { useEffect, useState } from "react";

const STREAM_URL =
    import.meta.env.VITE_STREAM_URL || "http://192.168.1.27:81/stream";

const typeClassMap = {
    Nhựa: "ai-chip ai-chip-plastic",
    "Kim loại": "ai-chip ai-chip-metal",
    Giấy: "ai-chip ai-chip-paper",
    Khác: "ai-chip ai-chip-other",
};

const Dashboard = ({
    trayPosition,
    targetTray,
    binWeights,
    doorOpen,
    latestAi,
    logs,
    toast,
    isStreamActive,
    onStreamToggle,
}) => {
    const isCorrectTray = trayPosition === targetTray;
    const aiChipClass = typeClassMap[latestAi.type] || typeClassMap["Khác"];
    const [streamError, setStreamError] = useState(false);
    const [streamSession, setStreamSession] = useState(Date.now());

    const streamSrc = `${STREAM_URL}${STREAM_URL.includes("?") ? "&" : "?"}t=${streamSession}`;

    useEffect(() => {
        if (isStreamActive) {
            setStreamError(false);
            setStreamSession(Date.now());
        }
    }, [isStreamActive]);

    return (
        <section className="page dashboard-page">
            {toast ? (
                <div className="toast-success" role="status" aria-live="polite">
                    {toast}
                </div>
            ) : null}

            <header className="page-header">
                <h1>Tổng quan</h1>
                <p>Chào mừng quay lại hệ thống Smart Bin.</p>
            </header>

            <div className="metrics-grid">
                <MetricCard
                    title="Vị trí mâm"
                    value={`Ngăn ${trayPosition}`}
                    desc={
                        isCorrectTray
                            ? "Đúng vị trí mục tiêu"
                            : "Lệch vị trí mục tiêu"
                    }
                    icon={<Layers3 size={20} />}
                    status={isCorrectTray ? "good" : "warn"}
                />
                <MetricCard
                    title="Trạng thái cửa"
                    value={doorOpen ? "Đang mở" : "Đang đóng"}
                    desc={
                        doorOpen ? "Cửa đã mở cho thao tác" : "Cửa đóng an toàn"
                    }
                    icon={<CheckCircle2 size={20} />}
                    status={doorOpen ? "warn" : "good"}
                />
                <MetricCard
                    title="Loại rác vừa nhận diện"
                    value={latestAi.type}
                    desc="Nhận diện bởi AI"
                    icon={<Sparkles size={20} />}
                    status="info"
                />
                <MetricCard
                    title="Độ tự tin"
                    value={`${latestAi.confidence}%`}
                    desc="Confidence của mô hình"
                    icon={<Activity size={20} />}
                    status="info"
                />
            </div>

            <div className="content-grid">
                <article className="panel-card">
                    <div className="panel-title">
                        <Camera size={18} />
                        <h2>ESP32-CAM Live Stream</h2>
                        <button
                            onClick={onStreamToggle}
                            className={`stream-toggle-btn ${isStreamActive ? "active" : "inactive"}`}
                            aria-label={isStreamActive ? "Dừng stream" : "Phát stream"}
                        >
                            {isStreamActive ? (
                                <>
                                    <Pause size={16} />
                                    Dừng
                                </>
                            ) : (
                                <>
                                    <Play size={16} />
                                    Phát
                                </>
                            )}
                        </button>
                    </div>
                    {isStreamActive && (
                        <div className="camera-placeholder">
                            {streamError ? (
                                <div className="camera-error">
                                    <span>Không tải được stream</span>
                                    <small>{STREAM_URL}</small>
                                </div>
                            ) : (
                                <img
                                    src={streamSrc}
                                    alt="ESP32-CAM Live Stream"
                                    onError={() => setStreamError(true)}
                                    onLoad={() => setStreamError(false)}
                                />
                            )}
                        </div>
                    )}
                    {!isStreamActive && (
                        <div className="camera-placeholder">
                            <span>Stream bị tắt</span>
                        </div>
                    )}
                    <div className="camera-ai-result">
                        <span className={aiChipClass}>{latestAi.type}</span>
                        <span>Độ tự tin: {latestAi.confidence}%</span>
                    </div>
                </article>

                <article className="panel-card">
                    <div className="panel-title">
                        <Layers3 size={18} />
                        <h2>Trạng thái phần cứng</h2>
                    </div>
                    <div className="bins-grid">
                        {[1, 2, 3, 4].map((bin) => (
                            <div
                                key={bin}
                                className={`bin-cell ${bin === trayPosition ? "active" : ""}`}
                            >
                                <strong>Ngăn {bin}</strong>
                                <small>
                                    {bin === trayPosition
                                        ? "Vị trí hiện tại"
                                        : "Sẵn sàng"}
                                </small>
                                <small className="bin-weight">
                                    Khối lượng:{" "}
                                    {(binWeights?.[bin] ?? 0).toFixed(2)} kg
                                </small>
                            </div>
                        ))}
                    </div>
                    <div
                        className={`door-state ${doorOpen ? "open" : "closed"}`}
                        role="status"
                    >
                        Cửa sập: {doorOpen ? "MỞ" : "ĐÓNG"}
                    </div>
                </article>
            </div>

            <article className="log-card">
                <div className="log-header">
                    <h2>Nhật ký hệ thống</h2>
                    <span>Tối đa 8 dòng gần nhất</span>
                </div>
                <table>
                    <thead>
                        <tr>
                            <th>Tên hành động</th>
                            <th>Kết quả</th>
                            <th>Thời gian</th>
                        </tr>
                    </thead>
                    <tbody>
                        {logs.map((log) => (
                            <tr key={`${log.time}-${log.action}`}>
                                <td>{log.action}</td>
                                <td>{log.result}</td>
                                <td>{log.time}</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </article>
        </section>
    );
};

const MetricCard = ({ title, value, desc, icon, status }) => (
    <article className="metric-card">
        <div className="metric-icon">{icon}</div>
        <p className="metric-title">{title}</p>
        <p className="metric-value">{value}</p>
        <p className={`metric-desc ${status}`}>{desc}</p>
    </article>
);

export default Dashboard;
