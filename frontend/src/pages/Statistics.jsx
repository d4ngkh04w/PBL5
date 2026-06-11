import { useState, useEffect } from "react";
import { BarChart3, Clock3, Database, TrendingUp } from "lucide-react";
import {
    Bar,
    BarChart,
    CartesianGrid,
    Cell,
    ResponsiveContainer,
    Tooltip,
    XAxis,
    YAxis,
} from "recharts";
import { getStatistics } from "../services/api";

/* Corporate Trust palette: Indigo → Violet → Emerald → Slate */
const colors = ["#4F46E5", "#7C3AED", "#10B981", "#64748B"];

const groupColors = {
    recycling: "#4F46E5",       // Indigo
    hazardous: "#7C3AED",       // Violet
    organic: "#10B981",         // Emerald
    non_recyclable: "#64748B",  // Slate
};

const groupToVi = {
    recycling: "Tái chế",
    organic: "Hữu cơ",
    hazardous: "Độc hại",
    non_recyclable: "Khác",
};

const classNameToVi = {
    battery: "Pin",
    biological: "Sinh học",
    cardboard: "Bìa carton",
    clothes: "Quần áo",
    "e-waste": "Rác điện tử",
    glass: "Thủy tinh",
    metal: "Kim loại",
    paper: "Giấy",
    plastic: "Nhựa",
    shoes: "Giày dép",
    unknown: "Không xác định",
    none: "Chưa có",
};

const Statistics = ({ logs, trayPosition }) => {
    const [stats, setStats] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let isMounted = true;
        const fetchStats = async () => {
            try {
                setLoading(true);
                const data = await getStatistics();
                if (isMounted) {
                    setStats(data);
                    setError(null);
                }
            } catch (err) {
                console.error("Lỗi khi tải thống kê:", err);
                if (isMounted) {
                    setError("Không thể tải dữ liệu thống kê từ backend.");
                }
            } finally {
                if (isMounted) {
                    setLoading(false);
                }
            }
        };

        fetchStats();
        return () => {
            isMounted = false;
        };
    }, []);

    if (loading) {
        return (
            <section className="page" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '300px', gap: '12px' }}>
                <div className="spinner" style={{
                    width: '40px',
                    height: '40px',
                    border: '3px solid #E2E8F0',
                    borderTopColor: '#4F46E5',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite'
                }}></div>
                <style>{`
                    @keyframes spin {
                        to { transform: rotate(360deg); }
                    }
                `}</style>
                <p style={{ color: '#64748B', fontSize: '14px', fontFamily: "'Plus Jakarta Sans', sans-serif" }}>
                    Đang tải dữ liệu thống kê từ hệ thống...
                </p>
            </section>
        );
    }

    if (error) {
        return (
            <section className="page" style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: '300px', gap: '12px' }}>
                <div style={{ color: '#EF4444', fontSize: '16px', fontWeight: 600 }}>⚠️ {error}</div>
                <button 
                    onClick={() => window.location.reload()} 
                    style={{
                        padding: '8px 16px',
                        background: '#4F46E5',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        cursor: 'pointer',
                        fontSize: '14px',
                        fontWeight: 500
                    }}
                >
                    Thử lại
                </button>
            </section>
        );
    }

    // Process group distribution for bar chart
    const wasteData = stats ? stats.group_distribution.map(item => ({
        name: groupToVi[item.group] || item.group,
        value: item.count,
        rawGroup: item.group
    })) : [];

    const hourlyData = stats ? stats.hourly_distribution : [];
    const mostCommonVi = stats ? (classNameToVi[stats.most_common_class] || stats.most_common_class) : "Chưa có";
    const avgConfidencePercent = stats ? Math.round(stats.most_common_class_confidence * 100) : 0;

    return (
        <section className="page">
            <header className="page-header">
                <h1>Thống kê</h1>
                <p>Tổng hợp nhanh dữ liệu từ hệ thống phân loại rác.</p>
            </header>

            <div className="stats-top-grid">
                <div className="metric-card">
                    <div className="metric-icon">
                        <Database size={20} />
                    </div>
                    <p className="metric-title">Tổng lượt phân loại</p>
                    <p className="metric-value">{stats.total_count}</p>
                    <p className="metric-desc info">
                        Cập nhật theo phiên gần nhất
                    </p>
                </div>
                <div className="metric-card">
                    <div className="metric-icon">
                        <TrendingUp size={20} />
                    </div>
                    <p className="metric-title">Loại rác phổ biến nhất</p>
                    <p className="metric-value">{mostCommonVi}</p>
                    <p className="metric-desc good">
                        Số lượng: {stats.most_common_class_count} lượt (TB tự tin: {avgConfidencePercent}%)
                    </p>
                </div>
                <div className="metric-card">
                    <div className="metric-icon">
                        <Clock3 size={20} />
                    </div>
                    <p className="metric-title">Vị trí mâm hiện tại</p>
                    <p className="metric-value">Ngăn {trayPosition}</p>
                    <p className="metric-desc info">Đồng bộ theo dashboard</p>
                </div>
            </div>

            <div className="charts-grid">
                <article className="panel-card chart-card">
                    <div className="panel-title">
                        <BarChart3 size={18} />
                        <h2>Phân bố loại rác</h2>
                    </div>
                    <ResponsiveContainer width="100%" height={280}>
                        <BarChart
                            data={wasteData}
                            margin={{
                                top: 20,
                                right: 20,
                                left: -10,
                                bottom: 0,
                            }}
                        >
                            <CartesianGrid
                                strokeDasharray="4 4"
                                vertical={false}
                                stroke="#E2E8F0"
                            />
                            <XAxis
                                dataKey="name"
                                tick={{ fill: "#64748B", fontSize: 13 }}
                                axisLine={{ stroke: "#E2E8F0" }}
                                tickLine={false}
                            />
                            <YAxis
                                tick={{ fill: "#64748B", fontSize: 13 }}
                                axisLine={false}
                                tickLine={false}
                            />
                            <Tooltip
                                contentStyle={{
                                    background: "#FFFFFF",
                                    border: "1px solid #E2E8F0",
                                    borderRadius: "8px",
                                    boxShadow: "0 4px 20px -2px rgba(79, 70, 229, 0.1)",
                                }}
                                labelStyle={{
                                    fontFamily: "'Plus Jakarta Sans', sans-serif",
                                    fontWeight: 700,
                                    color: "#0F172A",
                                }}
                                itemStyle={{
                                    color: "#0F172A",
                                }}
                            />
                            <Bar dataKey="value" radius={[8, 8, 0, 0]}>
                                {wasteData.map((entry, index) => (
                                    <Cell
                                        key={`cell-${entry.name}`}
                                        fill={groupColors[entry.rawGroup] || colors[index % colors.length]}
                                    />
                                ))}
                            </Bar>
                        </BarChart>
                    </ResponsiveContainer>
                </article>

                <article className="panel-card chart-card">
                    <div className="panel-title">
                        <TrendingUp size={18} />
                        <h2>Lượng xử lý theo giờ</h2>
                    </div>
                    <ResponsiveContainer width="100%" height={280}>
                        <BarChart
                            data={hourlyData}
                            margin={{
                                top: 20,
                                right: 20,
                                left: -10,
                                bottom: 0,
                            }}
                        >
                            <CartesianGrid
                                strokeDasharray="4 4"
                                vertical={false}
                                stroke="#E2E8F0"
                            />
                            <XAxis
                                dataKey="time"
                                tick={{ fill: "#64748B", fontSize: 13 }}
                                axisLine={{ stroke: "#E2E8F0" }}
                                tickLine={false}
                            />
                            <YAxis
                                tick={{ fill: "#64748B", fontSize: 13 }}
                                axisLine={false}
                                tickLine={false}
                            />
                            <Tooltip
                                contentStyle={{
                                    background: "#FFFFFF",
                                    border: "1px solid #E2E8F0",
                                    borderRadius: "8px",
                                    boxShadow: "0 4px 20px -2px rgba(79, 70, 229, 0.1)",
                                }}
                                labelStyle={{
                                    fontFamily: "'Plus Jakarta Sans', sans-serif",
                                    fontWeight: 700,
                                    color: "#0F172A",
                                }}
                                itemStyle={{
                                    color: "#0F172A",
                                }}
                            />
                            <Bar
                                dataKey="count"
                                radius={[8, 8, 0, 0]}
                                fill="#4F46E5"
                            />
                        </BarChart>
                    </ResponsiveContainer>
                </article>
            </div>

            <article className="log-card">
                <div className="log-header">
                    <h2>Lịch sử thao tác gần đây</h2>
                    <span>Dữ liệu đồng bộ từ dashboard</span>
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
                            <tr key={`stats-${log.time}-${log.action}`}>
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

export default Statistics;

