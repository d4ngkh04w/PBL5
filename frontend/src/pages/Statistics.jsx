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

/* Corporate Trust palette: Indigo → Violet → Emerald → Slate */
const colors = ["#4F46E5", "#7C3AED", "#10B981", "#64748B"];

const Statistics = ({ logs, trayPosition, latestAi }) => {
    const wasteData = [
        { name: "Nhựa", value: 32 },
        { name: "Kim loại", value: 18 },
        { name: "Giấy", value: 27 },
        { name: "Khác", value: 11 },
    ];

    const hourlyData = [
        { time: "08h", count: 6 },
        { time: "10h", count: 9 },
        { time: "12h", count: 7 },
        { time: "14h", count: 11 },
        { time: "16h", count: 8 },
    ];

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
                    <p className="metric-value">88</p>
                    <p className="metric-desc info">
                        Cập nhật theo phiên gần nhất
                    </p>
                </div>
                <div className="metric-card">
                    <div className="metric-icon">
                        <TrendingUp size={20} />
                    </div>
                    <p className="metric-title">Loại rác phổ biến</p>
                    <p className="metric-value">{latestAi.type}</p>
                    <p className="metric-desc good">
                        Độ tự tin {latestAi.confidence}%
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
                                        fill={colors[index % colors.length]}
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
