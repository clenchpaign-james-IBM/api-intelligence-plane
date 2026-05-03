import React, { useState, useEffect } from 'react';
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import axios from 'axios';

interface AgenticMetrics {
  success_rate: number;
  avg_query_latency: number;
  avg_single_agent_latency: number;
  avg_multi_agent_latency: number;
  fallback_rate: number;
  confidence_correlation: number;
  tool_success_rate: number;
  agent_usage: Record<string, number>;
  query_volume_by_hour: Array<{ hour: string; count: number }>;
  latency_distribution: Array<{ range: string; count: number }>;
  fallback_triggers: Record<string, number>;
  top_queries: Array<{ query: string; count: number; avg_latency: number }>;
}

const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

const AgenticMetrics: React.FC = () => {
  const [metrics, setMetrics] = useState<AgenticMetrics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [timeRange, setTimeRange] = useState<'1h' | '24h' | '7d' | '30d'>('24h');

  useEffect(() => {
    fetchMetrics();
    const interval = setInterval(fetchMetrics, 60000); // Refresh every minute
    return () => clearInterval(interval);
  }, [timeRange]);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      const response = await axios.get<AgenticMetrics>(
        `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1/query/metrics`,
        { params: { time_range: timeRange } }
      );
      setMetrics(response.data);
      setError(null);
    } catch (err) {
      setError('Failed to fetch agentic metrics');
      console.error('Error fetching metrics:', err);
    } finally {
      setLoading(false);
    }
  };

  if (loading && !metrics) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl">Loading metrics...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-xl text-red-600">{error}</div>
      </div>
    );
  }

  if (!metrics) {
    return null;
  }

  // Prepare data for charts
  const agentUsageData = Object.entries(metrics.agent_usage).map(([name, count]) => ({
    name: name.replace('_', ' ').toUpperCase(),
    count,
  }));

  const fallbackTriggersData = Object.entries(metrics.fallback_triggers).map(([trigger, count]) => ({
    name: trigger.replace('_', ' '),
    count,
  }));

  // Status indicators
  const getStatusColor = (value: number, threshold: number, inverse = false) => {
    if (inverse) {
      return value < threshold ? 'text-green-600' : 'text-red-600';
    }
    return value >= threshold ? 'text-green-600' : 'text-red-600';
  };

  const getStatusIcon = (value: number, threshold: number, inverse = false) => {
    const isGood = inverse ? value < threshold : value >= threshold;
    return isGood ? '✓' : '✗';
  };

  return (
    <div className="p-6 bg-gray-50 min-h-screen">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6 flex justify-between items-center">
          <h1 className="text-3xl font-bold text-gray-900">Agentic Query Metrics</h1>
          <div className="flex gap-2">
            {(['1h', '24h', '7d', '30d'] as const).map((range) => (
              <button
                key={range}
                onClick={() => setTimeRange(range)}
                className={`px-4 py-2 rounded ${
                  timeRange === range
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-700 hover:bg-gray-100'
                }`}
              >
                {range}
              </button>
            ))}
          </div>
        </div>

        {/* Key Performance Indicators */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-gray-600">Agentic Success Rate</p>
                <p className={`text-3xl font-bold ${getStatusColor(metrics.success_rate, 0.9)}`}>
                  {(metrics.success_rate * 100).toFixed(1)}%
                </p>
                <p className="text-xs text-gray-500 mt-1">Target: ≥90%</p>
              </div>
              <span className={`text-2xl ${getStatusColor(metrics.success_rate, 0.9)}`}>
                {getStatusIcon(metrics.success_rate, 0.9)}
              </span>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-gray-600">Avg Query Latency</p>
                <p className={`text-3xl font-bold ${getStatusColor(metrics.avg_query_latency, 5000, true)}`}>
                  {(metrics.avg_query_latency / 1000).toFixed(2)}s
                </p>
                <p className="text-xs text-gray-500 mt-1">Target: {'<'}5s</p>
              </div>
              <span className={`text-2xl ${getStatusColor(metrics.avg_query_latency, 5000, true)}`}>
                {getStatusIcon(metrics.avg_query_latency, 5000, true)}
              </span>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-gray-600">Fallback Rate</p>
                <p className={`text-3xl font-bold ${getStatusColor(metrics.fallback_rate, 0.1, true)}`}>
                  {(metrics.fallback_rate * 100).toFixed(1)}%
                </p>
                <p className="text-xs text-gray-500 mt-1">Target: {'<'}10%</p>
              </div>
              <span className={`text-2xl ${getStatusColor(metrics.fallback_rate, 0.1, true)}`}>
                {getStatusIcon(metrics.fallback_rate, 0.1, true)}
              </span>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <div className="flex justify-between items-start">
              <div>
                <p className="text-sm text-gray-600">Tool Success Rate</p>
                <p className={`text-3xl font-bold ${getStatusColor(metrics.tool_success_rate, 0.95)}`}>
                  {(metrics.tool_success_rate * 100).toFixed(1)}%
                </p>
                <p className="text-xs text-gray-500 mt-1">Target: ≥95%</p>
              </div>
              <span className={`text-2xl ${getStatusColor(metrics.tool_success_rate, 0.95)}`}>
                {getStatusIcon(metrics.tool_success_rate, 0.95)}
              </span>
            </div>
          </div>
        </div>

        {/* Latency Breakdown */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Latency by Agent Type</h2>
            <div className="space-y-4">
              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-gray-600">Single-Agent Queries</span>
                  <span className={`text-sm font-semibold ${getStatusColor(metrics.avg_single_agent_latency, 5000, true)}`}>
                    {(metrics.avg_single_agent_latency / 1000).toFixed(2)}s
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      metrics.avg_single_agent_latency < 5000 ? 'bg-green-600' : 'bg-red-600'
                    }`}
                    style={{ width: `${Math.min((metrics.avg_single_agent_latency / 5000) * 100, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">Target: {'<'}5s</p>
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-gray-600">Multi-Agent Queries</span>
                  <span className={`text-sm font-semibold ${getStatusColor(metrics.avg_multi_agent_latency, 10000, true)}`}>
                    {(metrics.avg_multi_agent_latency / 1000).toFixed(2)}s
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      metrics.avg_multi_agent_latency < 10000 ? 'bg-green-600' : 'bg-red-600'
                    }`}
                    style={{ width: `${Math.min((metrics.avg_multi_agent_latency / 10000) * 100, 100)}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">Target: {'<'}10s</p>
              </div>

              <div>
                <div className="flex justify-between mb-1">
                  <span className="text-sm text-gray-600">Confidence Correlation</span>
                  <span className={`text-sm font-semibold ${getStatusColor(metrics.confidence_correlation, 0.8)}`}>
                    {metrics.confidence_correlation.toFixed(2)}
                  </span>
                </div>
                <div className="w-full bg-gray-200 rounded-full h-2">
                  <div
                    className={`h-2 rounded-full ${
                      metrics.confidence_correlation >= 0.8 ? 'bg-green-600' : 'bg-red-600'
                    }`}
                    style={{ width: `${metrics.confidence_correlation * 100}%` }}
                  />
                </div>
                <p className="text-xs text-gray-500 mt-1">Target: ≥0.8</p>
              </div>
            </div>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Latency Distribution</h2>
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={metrics.latency_distribution}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="range" />
                <YAxis />
                <Tooltip />
                <Bar dataKey="count" fill="#0088FE" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Agent Usage and Fallback Triggers */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Agent Usage Distribution</h2>
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie
                  data={agentUsageData}
                  cx="50%"
                  cy="50%"
                  labelLine={false}
                  label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  outerRadius={80}
                  fill="#8884d8"
                  dataKey="count"
                >
                  {agentUsageData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>

          <div className="bg-white p-6 rounded-lg shadow">
            <h2 className="text-xl font-semibold mb-4">Fallback Triggers</h2>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={fallbackTriggersData} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" />
                <YAxis dataKey="name" type="category" width={150} />
                <Tooltip />
                <Bar dataKey="count" fill="#FF8042" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Query Volume Over Time */}
        <div className="bg-white p-6 rounded-lg shadow mb-6">
          <h2 className="text-xl font-semibold mb-4">Query Volume Over Time</h2>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={metrics.query_volume_by_hour}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="hour" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="count" stroke="#0088FE" strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* Top Queries */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h2 className="text-xl font-semibold mb-4">Top Queries</h2>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Query
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Count
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Avg Latency
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {metrics.top_queries.map((query, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 text-sm text-gray-900 max-w-md truncate">
                      {query.query}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {query.count}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {(query.avg_latency / 1000).toFixed(2)}s
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AgenticMetrics;

// Made with Bob
