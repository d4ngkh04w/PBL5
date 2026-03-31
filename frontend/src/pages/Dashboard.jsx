import {
    Activity,
    Camera,
    CheckCircle2,
    Layers3,
    Sparkles,
    Play,
    Pause,
} from "lucide-react";

const STREAM_URL =
    import.meta.env.VITE_STREAM_URL || "http://localhost:8080/stream";

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

    return (
        <section className="page dashboard-page">
            {toast ? <div className="toast-success">{toast}</div> : null}

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
                    icon={<Layers3 size={18} />}
                    status={isCorrectTray ? "good" : "warn"}
                />
                <MetricCard
                    title="Trạng thái cửa"
                    value={doorOpen ? "Đang mở" : "Đang đóng"}
                    desc={
                        doorOpen ? "Cửa đã mở cho thao tác" : "Cửa đóng an toàn"
                    }
                    icon={<CheckCircle2 size={18} />}
                    status={doorOpen ? "warn" : "good"}
                />
                <MetricCard
                    title="Loại rác vừa nhận diện"
                    value={latestAi.type}
                    desc="Nhận diện bởi AI"
                    icon={<Sparkles size={18} />}
                    status="info"
                />
                <MetricCard
                    title="Độ tự tin"
                    value={`${latestAi.confidence}%`}
                    desc="Confidence của mô hình"
                    icon={<Activity size={18} />}
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
                            style={{
                                marginLeft: "auto",
                                padding: "6px 12px",
                                border: "none",
                                background: isStreamActive
                                    ? "#ef4444"
                                    : "#10b981",
                                color: "white",
                                borderRadius: "4px",
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                gap: "6px",
                                fontSize: "14px",
                            }}
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
                            <img
                                src={STREAM_URL}
                                alt="ESP32-CAM Live Stream"
                                style={{
                                    width: "100%",
                                    height: "100%",
                                    objectFit: "cover",
                                }}
                                onError={() =>
                                    console.log("Stream connection failed")
                                }
                            />
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
