import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  BarChart3, 
  Clock, 
  ThumbsUp, 
  ThumbsDown, 
  ShieldCheck, 
  Activity, 
  FileText, 
  RefreshCw, 
  Calendar,
  MessageSquare,
  Sparkles,
  ChevronDown,
  ChevronUp,
  AlertCircle
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const EvaluationDashboard = () => {
  const [stats, setStats] = useState(null);
  const [logs, setLogs] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [chartMetric, setChartMetric] = useState('queries'); // 'queries' | 'latency' | 'scores'
  const [expandedLogId, setExpandedLogId] = useState(null);
  const [feedbackLoadingId, setFeedbackLoadingId] = useState(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError('');
    try {
      const token = localStorage.getItem('token');
      const headers = { Authorization: `Bearer ${token}` };

      const statsResp = await axios.get(`${API_URL}/evaluations/stats`, { headers });
      setStats(statsResp.data);

      const logsResp = await axios.get(`${API_URL}/evaluations/logs`, { headers });
      setLogs(logsResp.data || []);
    } catch (err) {
      console.error('Failed to load evaluation telemetry:', err);
      setError(err.response?.data?.detail || 'Failed to load evaluation dashboard data.');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleToggleFeedback = async (evalId, currentFeedback, targetValue) => {
    setFeedbackLoadingId(evalId);
    try {
      const token = localStorage.getItem('token');
      const newValue = currentFeedback === targetValue ? 0 : targetValue;

      await axios.post(
        `${API_URL}/evaluations/${evalId}/feedback`,
        { feedback: newValue },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setLogs((prevLogs) =>
        prevLogs.map((log) => (log.id === evalId ? { ...log, user_feedback: newValue } : log))
      );

      if (stats) {
        let upDiff = 0;
        let downDiff = 0;

        if (currentFeedback === 1) upDiff = -1;
        if (currentFeedback === -1) downDiff = -1;
        if (newValue === 1) upDiff = 1;
        if (newValue === -1) downDiff = 1;

        const newUp = stats.thumbs_up_count + upDiff;
        const newDown = stats.thumbs_down_count + downDiff;
        const totalRated = newUp + newDown;
        const positivePct = totalRated > 0 ? Math.round((newUp / totalRated) * 100 * 10) / 10 : 0.0;

        setStats({
          ...stats,
          thumbs_up_count: newUp,
          thumbs_down_count: newDown,
          positive_feedback_pct: positivePct
        });
      }
    } catch (err) {
      console.error('Failed to update feedback:', err);
    } finally {
      setFeedbackLoadingId(null);
    }
  };

  const getScoreColor = (score) => {
    if (score === null || score === undefined) return 'text-zinc-500 bg-zinc-50 border-zinc-200';
    if (score >= 0.8) return 'text-emerald-700 bg-emerald-50 border-emerald-100';
    if (score >= 0.5) return 'text-amber-700 bg-amber-50 border-amber-100';
    return 'text-rose-700 bg-rose-50 border-rose-100';
  };

  const toggleExpandLog = (id) => {
    setExpandedLogId(expandedLogId === id ? null : id);
  };

  if (isLoading && !stats) {
    return (
      <div className="flex flex-col items-center justify-center py-32 space-y-3">
        <RefreshCw className="h-6 w-6 text-zinc-650 animate-spin" />
        <p className="text-zinc-500 text-[10px] font-bold uppercase tracking-widest animate-pulse">Compiling analytics telemetry...</p>
      </div>
    );
  }

  const dailyMetrics = stats?.daily_metrics || [];
  const chartHeight = 160;
  const chartWidth = 720;
  const paddingX = 45;
  const paddingY = 20;
  const graphHeight = chartHeight - paddingY * 2;
  const graphWidth = chartWidth - paddingX * 2;

  let maxChartVal = 1;
  if (dailyMetrics.length > 0) {
    if (chartMetric === 'queries') {
      maxChartVal = Math.max(...dailyMetrics.map((d) => d.total_queries), 1);
    } else if (chartMetric === 'latency') {
      maxChartVal = Math.max(...dailyMetrics.map((d) => d.avg_latency), 1);
    } else {
      maxChartVal = 1.0;
    }
  }

  return (
    <div className="space-y-6 pb-12 font-sans select-none animate-fade-in">
      
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-lg font-bold tracking-tight text-[#18181b]">
            Evaluation Console
          </h1>
          <p className="text-xs text-zinc-500 font-semibold mt-1">
            Track metrics telemetry for RAG accuracy alignments, response latencies, and user feedback signals.
          </p>
        </div>
        <button
          id="evaluation-dashboard-refresh"
          onClick={fetchData}
          disabled={isLoading}
          className="flex items-center justify-center space-x-2 py-2 px-3.5 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-xl text-xs font-bold text-zinc-650 hover:text-[#18181b] transition-all cursor-pointer shadow-sm btn-press-active"
        >
          <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
          <span>Refresh metrics</span>
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-50 border border-rose-100 rounded-2xl text-rose-700 flex items-start space-x-3 text-xs leading-relaxed shadow-sm">
          <AlertCircle size={16} className="shrink-0 mt-0.5" />
          <p>{error}</p>
        </div>
      )}

      {/* Metrics Grid dashboard */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        {[
          { label: 'Volume', value: stats?.total_queries || 0, desc: 'Total query items', icon: MessageSquare, color: 'text-[#18181b]' },
          { label: 'Latency', value: stats?.avg_latency_ms ? `${stats.avg_latency_ms} ms` : '0 ms', desc: 'Avg response delay', icon: Clock, color: 'text-[#18181b]' },
          { label: 'Groundedness', value: stats?.avg_faithfulness ? (stats.avg_faithfulness * 100).toFixed(0) + '%' : '0%', desc: 'Context faithfulness', icon: ShieldCheck, color: 'text-emerald-700', progress: stats?.avg_faithfulness || 0, barColor: 'bg-emerald-600' },
          { label: 'Relevance', value: stats?.avg_relevance ? (stats.avg_relevance * 100).toFixed(0) + '%' : '0%', desc: 'Query alignment ratio', icon: Sparkles, color: 'text-purple-750', progress: stats?.avg_relevance || 0, barColor: 'bg-purple-600' },
          { label: 'Feedback', value: stats?.positive_feedback_pct ? `${stats.positive_feedback_pct}%` : '0%', desc: `${stats?.thumbs_up_count || 0} Up / ${stats?.thumbs_down_count || 0} Down`, icon: ThumbsUp, color: 'text-amber-700' }
        ].map((metric, i) => (
          <div key={i} className="bg-white border border-zinc-200/80 rounded-2xl p-4 flex flex-col justify-between shadow-sm hover:shadow-md transition-all duration-200 card-hover-effect">
            <div className="flex items-center justify-between text-zinc-400">
              <span className="text-[9px] font-bold uppercase tracking-wider">{metric.label}</span>
              <div className="p-1.5 bg-zinc-50 border border-zinc-100 rounded-lg text-zinc-555">
                <metric.icon size={13} />
              </div>
            </div>
            <div className="mt-3">
              <span className={`text-lg font-extrabold ${metric.color}`}>{metric.value}</span>
              {metric.progress !== undefined && (
                <div className="w-full bg-zinc-100 h-1 rounded-full mt-2 overflow-hidden">
                  <div className={`h-full ${metric.barColor}`} style={{ width: `${metric.progress * 100}%` }} />
                </div>
              )}
              <p className="text-[9px] text-zinc-500 font-semibold mt-1">{metric.desc}</p>
            </div>
          </div>
        ))}
      </div>

      {/* SVG Chart Trends */}
      <div className="bg-white border border-zinc-200/80 rounded-3xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-zinc-150 pb-3">
          <div className="flex items-center space-x-2.5">
            <Activity size={15} className="text-zinc-600" />
            <h2 className="text-[10px] font-bold text-[#18181b] uppercase tracking-wider">Performance Trends</h2>
          </div>
          
          <div className="flex bg-zinc-100 p-1 rounded-xl border border-zinc-200 self-start">
            {[
              { id: 'queries', label: 'Volume' },
              { id: 'latency', label: 'Latency' },
              { id: 'scores', label: 'Accuracy' }
            ].map((metric) => (
              <button
                key={metric.id}
                onClick={() => setChartMetric(metric.id)}
                className={`px-3 py-1 rounded-lg text-[9px] font-bold uppercase tracking-wider transition-all cursor-pointer ${
                  chartMetric === metric.id ? 'bg-white text-[#18181b] shadow-sm' : 'text-zinc-500 hover:text-[#18181b]'
                }`}
              >
                {metric.label}
              </button>
            ))}
          </div>
        </div>

        <div className="w-full overflow-x-auto py-2 hide-scrollbar">
          {dailyMetrics.length === 0 ? (
            <div className="h-32 flex flex-col items-center justify-center text-zinc-400">
              <BarChart3 size={24} className="text-zinc-300 mb-2" />
              <p className="text-[10px] font-bold uppercase tracking-wider">No historical logs recorded</p>
            </div>
          ) : (
            <div className="min-w-[720px] flex justify-center">
              <svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} width={chartWidth} height={chartHeight} className="overflow-visible">
                {/* grid lines */}
                {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
                  const y = paddingY + graphHeight * (1 - ratio);
                  const displayVal = (maxChartVal * ratio).toFixed(chartMetric === 'scores' ? 2 : 0);
                  return (
                    <g key={i} className="opacity-40">
                      <line x1={paddingX} y1={y} x2={chartWidth - paddingX} y2={y} stroke="#e4e4e7" strokeWidth="1" strokeDasharray="3 3" />
                      <text x={paddingX - 10} y={y + 3} fill="#71717a" fontSize="8" fontWeight="bold" textAnchor="end">{displayVal}</text>
                    </g>
                  );
                })}

                {/* Plot points */}
                {dailyMetrics.map((day, idx) => {
                  const x = paddingX + (graphWidth / (dailyMetrics.length)) * idx + (graphWidth / (dailyMetrics.length)) / 2;
                  const barWidth = Math.max(10, Math.min(22, (graphWidth / dailyMetrics.length) * 0.4));
                  
                  let val = 0;
                  let color = '#71717a';
                  
                  if (chartMetric === 'queries') {
                    val = day.total_queries;
                    color = '#18181b';
                  } else if (chartMetric === 'latency') {
                    val = day.avg_latency;
                    color = '#0d9488';
                  }

                  if (chartMetric === 'scores') {
                    const yFaith = paddingY + graphHeight * (1 - day.avg_faithfulness);
                    const yRel = paddingY + graphHeight * (1 - day.avg_relevance);
                    return (
                      <g key={idx}>
                        <circle cx={x - 4} cy={yFaith} r="3.5" fill="#059669" />
                        <line x1={x - 4} y1={chartHeight - paddingY} x2={x - 4} y2={yFaith} stroke="#059669" strokeWidth="1" strokeDasharray="2 2" className="opacity-20" />
                        <circle cx={x + 4} cy={yRel} r="3.5" fill="#7c3aed" />
                        <line x1={x + 4} y1={chartHeight - paddingY} x2={x + 4} y2={yRel} stroke="#7c3aed" strokeWidth="1" strokeDasharray="2 2" className="opacity-20" />
                        <text x={x} y={chartHeight - 4} fill="#71717a" fontSize="8" fontWeight="bold" textAnchor="middle">{day.date.substring(5)}</text>
                      </g>
                    );
                  } else {
                    const h = (val / maxChartVal) * graphHeight;
                    const y = chartHeight - paddingY - h;
                    return (
                      <g key={idx} className="group">
                        <rect x={x - barWidth / 2} y={y} width={barWidth} height={Math.max(2, h)} fill={color} fillOpacity="0.75" rx="2" className="transition-all hover:fill-opacity-100" />
                        <text x={x} y={chartHeight - 4} fill="#71717a" fontSize="8" fontWeight="bold" textAnchor="middle">{day.date.substring(5)}</text>
                      </g>
                    );
                  }
                })}

                {/* connect lines */}
                {chartMetric === 'scores' && dailyMetrics.length > 1 && (
                  <>
                    <path
                      d={dailyMetrics.map((day, idx) => {
                        const x = paddingX + (graphWidth / (dailyMetrics.length)) * idx + (graphWidth / (dailyMetrics.length)) / 2;
                        const y = paddingY + graphHeight * (1 - day.avg_faithfulness);
                        return `${idx === 0 ? 'M' : 'L'} ${x - 4} ${y}`;
                      }).join(' ')}
                      fill="none"
                      stroke="#059669"
                      strokeWidth="2"
                    />
                    <path
                      d={dailyMetrics.map((day, idx) => {
                        const x = paddingX + (graphWidth / (dailyMetrics.length)) * idx + (graphWidth / (dailyMetrics.length)) / 2;
                        const y = paddingY + graphHeight * (1 - day.avg_relevance);
                        return `${idx === 0 ? 'M' : 'L'} ${x + 4} ${y}`;
                      }).join(' ')}
                      fill="none"
                      stroke="#7c3aed"
                      strokeWidth="2"
                    />
                  </>
                )}
              </svg>
            </div>
          )}
        </div>

        {/* Legend */}
        {chartMetric === 'scores' && (
          <div className="flex justify-center space-x-6 text-[9px] font-bold uppercase tracking-wider pb-1">
            <div className="flex items-center space-x-1.5">
              <div className="w-2 h-2 rounded-full bg-emerald-600" />
              <span className="text-zinc-500">Groundedness</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <div className="w-2 h-2 rounded-full bg-purple-600" />
              <span className="text-zinc-500">Relevance</span>
            </div>
          </div>
        )}
      </div>

      {/* Logs Table list */}
      <div className="bg-white border border-zinc-200/80 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-4 border-b border-zinc-200 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileText size={15} className="text-zinc-650" />
            <h2 className="text-[10px] font-bold text-[#18181b] uppercase tracking-wider">Audit Telemetry logs</h2>
          </div>
          <span className="text-[9px] font-bold text-zinc-500 uppercase bg-zinc-50 px-2.5 py-1 rounded-full border border-zinc-200">
            {logs.length} logged events
          </span>
        </div>

        {logs.length === 0 ? (
          <div className="py-20 text-center">
            <MessageSquare size={28} className="mx-auto text-zinc-350 mb-2" />
            <p className="text-xs font-bold text-zinc-400">No events logged yet</p>
          </div>
        ) : (
          <div className="overflow-x-auto hide-scrollbar">
            <table className="w-full text-left border-collapse select-text">
              <thead>
                <tr className="border-b border-zinc-250 bg-zinc-50/20 text-[9px] font-bold text-zinc-450 uppercase tracking-wider">
                  <th className="py-3 px-5">Query Details</th>
                  <th className="py-3 px-4">Latency</th>
                  <th className="py-3 px-4">Context Hits</th>
                  <th className="py-3 px-4">Groundedness</th>
                  <th className="py-3 px-4">Relevance</th>
                  <th className="py-3 px-4">Document</th>
                  <th className="py-3 px-5 text-right">Feedback</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-zinc-100 text-xs">
                {logs.map((log) => {
                  const isExpanded = expandedLogId === log.id;
                  const isUp = log.user_feedback === 1;
                  const isDown = log.user_feedback === -1;

                  return (
                    <React.Fragment key={log.id}>
                      <tr 
                        onClick={() => toggleExpandLog(log.id)}
                        className={`hover:bg-zinc-50/50 transition-colors cursor-pointer ${isExpanded ? 'bg-zinc-50/40' : ''}`}
                      >
                        <td className="py-3 px-5 max-w-[200px]">
                          <div className="flex items-center space-x-1.5">
                            <span className="text-xs font-bold text-[#18181b] truncate block">{log.query}</span>
                            {isExpanded ? <ChevronUp size={11} className="text-zinc-455 shrink-0" /> : <ChevronDown size={11} className="text-zinc-455 shrink-0" />}
                          </div>
                          <span className="text-[8.5px] text-zinc-400 font-bold block mt-0.5">{new Date(log.created_at).toLocaleString()}</span>
                        </td>
                        <td className="py-3 px-4 font-mono text-zinc-500">{log.latency_ms} ms</td>
                        <td className="py-3 px-4 text-zinc-500">{log.retrieved_chunks_count} blocks</td>
                        <td className="py-3 px-4">
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border ${getScoreColor(log.faithfulness_score)}`}>
                            {log.faithfulness_score !== null ? log.faithfulness_score.toFixed(2) : 'N/A'}
                          </span>
                        </td>
                        <td className="py-3 px-4">
                          <span className={`text-[9px] font-bold px-2 py-0.5 rounded-full border ${getScoreColor(log.answer_relevance_score)}`}>
                            {log.answer_relevance_score !== null ? log.answer_relevance_score.toFixed(2) : 'N/A'}
                          </span>
                        </td>
                        <td className="py-3 px-4 text-zinc-600 max-w-[120px] truncate" title={log.document_name || 'N/A'}>
                          {log.document_name || <span className="text-zinc-400 italic">None</span>}
                        </td>
                        <td className="py-3 px-5 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end space-x-1">
                            <button
                              onClick={() => handleToggleFeedback(log.id, log.user_feedback, 1)}
                              disabled={feedbackLoadingId === log.id}
                              className={`p-1 rounded-lg border transition-colors cursor-pointer ${isUp ? 'text-emerald-700 bg-emerald-50 border-emerald-100' : 'text-zinc-450 hover:text-zinc-700 bg-white border-zinc-200'}`}
                              title="Thumbs Up"
                            >
                              <ThumbsUp size={10} />
                            </button>
                            <button
                              onClick={() => handleToggleFeedback(log.id, log.user_feedback, -1)}
                              disabled={feedbackLoadingId === log.id}
                              className={`p-1 rounded-lg border transition-colors cursor-pointer ${isDown ? 'text-rose-700 bg-rose-50 border-rose-100' : 'text-zinc-450 hover:text-zinc-700 bg-white border-zinc-200'}`}
                              title="Thumbs Down"
                            >
                              <ThumbsDown size={10} />
                            </button>
                          </div>
                        </td>
                      </tr>

                      <AnimatePresence>
                        {isExpanded && (
                          <tr className="bg-zinc-50/20">
                            <td colSpan="7" className="p-0">
                              <motion.div 
                                initial={{ height: 0, opacity: 0 }}
                                animate={{ height: 'auto', opacity: 1 }}
                                exit={{ height: 0, opacity: 0 }}
                                transition={{ duration: 0.15 }}
                                className="px-6 py-4 text-xs text-zinc-600 space-y-3 border-b border-zinc-150 overflow-hidden"
                              >
                                <div className="space-y-1">
                                  <span className="text-[9px] font-bold text-zinc-400 uppercase tracking-wider">Query Text</span>
                                  <p className="bg-zinc-50/50 border border-zinc-200 p-3 rounded-xl text-[#18181b] font-semibold">{log.query}</p>
                                </div>
                                <div className="space-y-1">
                                  <span className="text-[9px] font-bold text-zinc-400 uppercase tracking-wider">Generated Answer</span>
                                  <p className="bg-zinc-50/50 border border-zinc-200 p-3 rounded-xl text-zinc-800 leading-relaxed whitespace-pre-wrap">{log.answer}</p>
                                </div>
                              </motion.div>
                            </td>
                          </tr>
                        )}
                      </AnimatePresence>
                    </React.Fragment>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

    </div>
  );
};

export default EvaluationDashboard;
