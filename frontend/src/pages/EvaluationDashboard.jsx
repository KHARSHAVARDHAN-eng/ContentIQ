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

      // Fetch stats
      const statsResp = await axios.get(`${API_URL}/evaluations/stats`, { headers });
      setStats(statsResp.data);

      // Fetch logs
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

      // Update local logs state
      setLogs((prevLogs) =>
        prevLogs.map((log) => (log.id === evalId ? { ...log, user_feedback: newValue } : log))
      );

      // Update aggregate stats locally to avoid refetching
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
    if (score === null || score === undefined) return 'text-slate-500 bg-slate-500/10 border-slate-500/10';
    if (score >= 0.8) return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/10';
    if (score >= 0.5) return 'text-amber-400 bg-amber-500/10 border-amber-500/10';
    return 'text-rose-455 bg-rose-500/10 border-rose-500/15';
  };

  const toggleExpandLog = (id) => {
    setExpandedLogId(expandedLogId === id ? null : id);
  };

  if (isLoading && !stats) {
    return (
      <div className="flex flex-col items-center justify-center py-32 space-y-4">
        <RefreshCw className="h-8 w-8 text-indigo-500 animate-spin" />
        <p className="text-slate-400 text-xs font-semibold tracking-wider uppercase animate-pulse">Compiling RAG analytics...</p>
      </div>
    );
  }

  const dailyMetrics = stats?.daily_metrics || [];
  
  // Chart Math
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
      maxChartVal = 1.0; // Scores are always 0.0 to 1.0
    }
  }

  return (
    <div className="space-y-6 pb-12 font-sans select-none animate-fade-in">
      
      {/* Header section */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 via-purple-300 to-cyan-300 bg-clip-text text-transparent">
            Evaluation Console
          </h1>
          <p className="text-xs md:text-sm text-slate-400 font-medium mt-1">
            Audit ground truth RAG precision, answer relevance ratios, end-to-end latencies, and telemetry signals.
          </p>
        </div>
        <button
          id="evaluations-refresh-btn"
          onClick={fetchData}
          disabled={isLoading}
          className="flex items-center justify-center space-x-2 py-2.5 px-4 bg-slate-900 hover:bg-slate-850 border border-slate-900 hover:border-slate-800 rounded-2xl text-xs font-bold text-slate-200 transition-all cursor-pointer shadow-md shrink-0"
        >
          <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
          <span>Refresh Console</span>
        </button>
      </div>

      {error && (
        <div className="p-4 bg-rose-500/5 border border-rose-500/15 rounded-2xl text-rose-455 flex items-start space-x-3 text-xs leading-relaxed animate-fade-in">
          <AlertCircle size={18} className="shrink-0 mt-0.5" />
          <p>{error}</p>
        </div>
      )}

      {/* Metrics Grid dashboard */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        
        {/* Total queries */}
        <div className="bg-slate-900/60 backdrop-blur-md border border-slate-900 rounded-2xl p-4.5 flex flex-col justify-between shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[9px] font-bold uppercase tracking-wider">Volume</span>
            <div className="p-2 bg-indigo-500/10 rounded-xl text-indigo-400">
              <MessageSquare size={14} />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-2xl font-extrabold text-slate-100">{stats?.total_queries || 0}</span>
            <p className="text-[9px] text-slate-550 font-bold mt-1">Total query items</p>
          </div>
        </div>

        {/* Avg Latency */}
        <div className="bg-slate-900/60 backdrop-blur-md border border-slate-900 rounded-2xl p-4.5 flex flex-col justify-between shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[9px] font-bold uppercase tracking-wider">Latency</span>
            <div className="p-2 bg-cyan-500/10 rounded-xl text-cyan-400">
              <Clock size={14} />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-2xl font-extrabold text-slate-100">
              {stats?.avg_latency_ms ? `${stats.avg_latency_ms} ms` : '0 ms'}
            </span>
            <p className="text-[9px] text-slate-550 font-bold mt-1">Avg response delay</p>
          </div>
        </div>

        {/* Groundedness */}
        <div className="bg-slate-900/60 backdrop-blur-md border border-slate-900 rounded-2xl p-4.5 flex flex-col justify-between shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[9px] font-bold uppercase tracking-wider">Groundedness</span>
            <div className="p-2 bg-emerald-500/10 rounded-xl text-emerald-400">
              <ShieldCheck size={14} />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-2xl font-extrabold text-slate-100">
              {stats?.avg_faithfulness ? (stats.avg_faithfulness * 100).toFixed(0) + '%' : '0%'}
            </span>
            <div className="w-full bg-slate-950 h-1 rounded-full mt-2 overflow-hidden">
              <div 
                className="bg-emerald-500 h-full rounded-full" 
                style={{ width: `${(stats?.avg_faithfulness || 0) * 100}%` }}
              />
            </div>
            <p className="text-[9px] text-slate-550 font-bold mt-1">Faithful to context</p>
          </div>
        </div>

        {/* Relevance */}
        <div className="bg-slate-900/60 backdrop-blur-md border border-slate-900 rounded-2xl p-4.5 flex flex-col justify-between shadow-sm">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[9px] font-bold uppercase tracking-wider">Relevance</span>
            <div className="p-2 bg-purple-500/10 rounded-xl text-purple-400">
              <Sparkles size={14} />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-2xl font-extrabold text-slate-100">
              {stats?.avg_relevance ? (stats.avg_relevance * 100).toFixed(0) + '%' : '0%'}
            </span>
            <div className="w-full bg-slate-950 h-1 rounded-full mt-2 overflow-hidden">
              <div 
                className="bg-purple-500 h-full rounded-full" 
                style={{ width: `${(stats?.avg_relevance || 0) * 100}%` }}
              />
            </div>
            <p className="text-[9px] text-slate-550 font-bold mt-1">Aligns with intent</p>
          </div>
        </div>

        {/* Feedback Rate */}
        <div className="bg-slate-900/60 backdrop-blur-md border border-slate-900 rounded-2xl p-4.5 flex flex-col justify-between shadow-sm col-span-2 md:col-span-1">
          <div className="flex items-center justify-between text-slate-500">
            <span className="text-[9px] font-bold uppercase tracking-wider">Feedback</span>
            <div className="p-2 bg-amber-500/10 rounded-xl text-amber-400">
              <ThumbsUp size={14} />
            </div>
          </div>
          <div className="mt-4">
            <span className="text-2xl font-extrabold text-slate-100">
              {stats?.positive_feedback_pct ? `${stats.positive_feedback_pct}%` : '0%'}
            </span>
            <p className="text-[9px] text-slate-555 font-bold mt-1">
              {stats?.thumbs_up_count || 0} Up / {stats?.thumbs_down_count || 0} Down
            </p>
          </div>
        </div>

      </div>

      {/* SVG Analytics trends line chart */}
      <div className="bg-slate-900/60 backdrop-blur-md border border-slate-900 rounded-3xl p-5 shadow-sm space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-slate-900/50 pb-3">
          <div className="flex items-center space-x-2.5">
            <Activity size={16} className="text-indigo-400" />
            <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Performance Trends</h2>
          </div>
          
          {/* selectors */}
          <div className="flex bg-slate-950 p-1 rounded-xl border border-slate-900 self-start">
            {[
              { id: 'queries', label: 'Volume' },
              { id: 'latency', label: 'Latency' },
              { id: 'scores', label: 'Accuracy Scores' }
            ].map((metric) => (
              <button
                key={metric.id}
                onClick={() => setChartMetric(metric.id)}
                className={`px-3 py-1 rounded-lg text-[10px] font-bold uppercase tracking-wide transition-all cursor-pointer ${
                  chartMetric === metric.id ? 'bg-indigo-650/25 text-indigo-400' : 'text-slate-500 hover:text-slate-350'
                }`}
              >
                {metric.label}
              </button>
            ))}
          </div>
        </div>

        {/* SVG Wrapper */}
        <div className="w-full overflow-x-auto py-2 hide-scrollbar">
          {dailyMetrics.length === 0 ? (
            <div className="h-32 flex flex-col items-center justify-center text-slate-600">
              <BarChart3 size={28} className="text-slate-800 mb-2" />
              <p className="text-[11px] font-bold">No historical data recorded yet</p>
            </div>
          ) : (
            <div className="min-w-[720px] flex justify-center">
              <svg 
                viewBox={`0 0 ${chartWidth} ${chartHeight}`} 
                width={chartWidth} 
                height={chartHeight}
                className="overflow-visible"
              >
                <defs>
                  <linearGradient id="gradient-queries" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#6366f1" stopOpacity="0.4"/>
                    <stop offset="100%" stopColor="#6366f1" stopOpacity="0.0"/>
                  </linearGradient>
                  <linearGradient id="gradient-latency" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="#06b6d4" stopOpacity="0.4"/>
                    <stop offset="100%" stopColor="#06b6d4" stopOpacity="0.0"/>
                  </linearGradient>
                </defs>

                {/* Grid markings */}
                {[0, 0.25, 0.5, 0.75, 1].map((ratio, i) => {
                  const y = paddingY + graphHeight * (1 - ratio);
                  const displayVal = (maxChartVal * ratio).toFixed(chartMetric === 'scores' ? 2 : 0);
                  return (
                    <g key={i} className="opacity-40">
                      <line 
                        x1={paddingX} 
                        y1={y} 
                        x2={chartWidth - paddingX} 
                        y2={y} 
                        stroke="#1e293b" 
                        strokeWidth="1"
                        strokeDasharray="4 4" 
                      />
                      <text 
                        x={paddingX - 12} 
                        y={y + 3} 
                        fill="#475569" 
                        fontSize="8" 
                        fontWeight="bold"
                        textAnchor="end"
                      >
                        {displayVal}
                      </text>
                    </g>
                  );
                })}

                {/* Bars / Lines */}
                {dailyMetrics.map((day, idx) => {
                  const x = paddingX + (graphWidth / (dailyMetrics.length)) * idx + (graphWidth / (dailyMetrics.length)) / 2;
                  const barWidth = Math.max(10, Math.min(26, (graphWidth / dailyMetrics.length) * 0.4));
                  
                  let val = 0;
                  let color = '#6366f1';
                  
                  if (chartMetric === 'queries') {
                    val = day.total_queries;
                  } else if (chartMetric === 'latency') {
                    val = day.avg_latency;
                    color = '#06b6d4';
                  }

                  if (chartMetric === 'scores') {
                    const yFaith = paddingY + graphHeight * (1 - day.avg_faithfulness);
                    const yRel = paddingY + graphHeight * (1 - day.avg_relevance);

                    return (
                      <g key={idx}>
                        <circle cx={x - 4} cy={yFaith} r="3" fill="#10b981" />
                        <line x1={x - 4} y1={chartHeight - paddingY} x2={x - 4} y2={yFaith} stroke="#10b981" strokeWidth="1" strokeDasharray="2 2" className="opacity-20" />

                        <circle cx={x + 4} cy={yRel} r="3" fill="#a855f7" />
                        <line x1={x + 4} y1={chartHeight - paddingY} x2={x + 4} y2={yRel} stroke="#a855f7" strokeWidth="1" strokeDasharray="2 2" className="opacity-20" />

                        <text 
                          x={x} 
                          y={chartHeight - 4} 
                          fill="#475569" 
                          fontSize="8" 
                          fontWeight="bold"
                          textAnchor="middle"
                        >
                          {day.date.substring(5)}
                        </text>
                      </g>
                    );
                  } else {
                    const h = (val / maxChartVal) * graphHeight;
                    const y = chartHeight - paddingY - h;

                    return (
                      <g key={idx} className="group">
                        <rect 
                          x={x - barWidth / 2} 
                          y={y} 
                          width={barWidth} 
                          height={Math.max(2, h)} 
                          fill={color}
                          fillOpacity="0.8"
                          rx="3"
                          className="transition-all hover:fill-opacity-100"
                        />
                        {/* Tooltip on hover */}
                        <g className="opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity duration-200">
                          <rect
                            x={x - 30}
                            y={y - 24}
                            width="60"
                            height="18"
                            fill="#0b1120"
                            stroke={color}
                            strokeWidth="1"
                            rx="4"
                          />
                          <text
                            x={x}
                            y={y - 12}
                            fill="#f8fafc"
                            fontSize="8"
                            fontWeight="bold"
                            textAnchor="middle"
                          >
                            {val.toFixed(chartMetric === 'queries' ? 0 : 1)}
                          </text>
                        </g>
                        <text 
                          x={x} 
                          y={chartHeight - 4} 
                          fill="#475569" 
                          fontSize="8" 
                          fontWeight="bold"
                          textAnchor="middle"
                        >
                          {day.date.substring(5)}
                        </text>
                      </g>
                    );
                  }
                })}

                {/* Score lines connection paths */}
                {chartMetric === 'scores' && dailyMetrics.length > 1 && (
                  <>
                    <path
                      d={dailyMetrics.map((day, idx) => {
                        const x = paddingX + (graphWidth / (dailyMetrics.length)) * idx + (graphWidth / (dailyMetrics.length)) / 2;
                        const y = paddingY + graphHeight * (1 - day.avg_faithfulness);
                        return `${idx === 0 ? 'M' : 'L'} ${x - 4} ${y}`;
                      }).join(' ')}
                      fill="none"
                      stroke="#10b981"
                      strokeWidth="1.5"
                      className="opacity-70"
                    />
                    <path
                      d={dailyMetrics.map((day, idx) => {
                        const x = paddingX + (graphWidth / (dailyMetrics.length)) * idx + (graphWidth / (dailyMetrics.length)) / 2;
                        const y = paddingY + graphHeight * (1 - day.avg_relevance);
                        return `${idx === 0 ? 'M' : 'L'} ${x + 4} ${y}`;
                      }).join(' ')}
                      fill="none"
                      stroke="#a855f7"
                      strokeWidth="1.5"
                      className="opacity-70"
                    />
                  </>
                )}
              </svg>
            </div>
          )}
        </div>

        {/* Legend */}
        {chartMetric === 'scores' && (
          <div className="flex justify-center space-x-6 text-[10px] font-bold uppercase tracking-wider pb-1">
            <div className="flex items-center space-x-1.5">
              <div className="w-2 h-2 rounded-full bg-emerald-500" />
              <span className="text-slate-400">Groundedness (Faithfulness)</span>
            </div>
            <div className="flex items-center space-x-1.5">
              <div className="w-2 h-2 rounded-full bg-purple-500" />
              <span className="text-slate-400">Query Relevance</span>
            </div>
          </div>
        )}
      </div>

      {/* Telemetry log audits table */}
      <div className="bg-slate-900/60 backdrop-blur-md border border-slate-900 rounded-3xl overflow-hidden shadow-sm">
        <div className="p-5 border-b border-slate-900 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <FileText size={16} className="text-indigo-400" />
            <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider">RAG Telemetry Logs</h2>
          </div>
          <span className="text-[10px] font-bold text-slate-500 uppercase bg-slate-950 px-2.5 py-1 rounded-full border border-slate-900">
            {logs.length} events logged
          </span>
        </div>

        {logs.length === 0 ? (
          <div className="py-20 text-center">
            <MessageSquare size={32} className="mx-auto text-slate-755 mb-2.5" />
            <p className="text-xs font-bold text-slate-450">No chat events logged</p>
            <p className="text-[10px] text-slate-600 mt-1 max-w-[280px] mx-auto leading-relaxed">
              Log events will record automatically when queries are sent in the assistant page.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse select-text">
              <thead>
                <tr className="border-b border-slate-900 bg-slate-950/20 text-[10px] font-bold text-slate-500 uppercase tracking-wider">
                  <th className="py-3.5 px-5">Query details</th>
                  <th className="py-3.5 px-4">Latency</th>
                  <th className="py-3.5 px-4">Context Hits</th>
                  <th className="py-3.5 px-4">Groundedness</th>
                  <th className="py-3.5 px-4">Relevance</th>
                  <th className="py-3.5 px-4">Document</th>
                  <th className="py-3.5 px-5 text-right">Feedback</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-950/60 text-xs">
                {logs.map((log) => {
                  const isExpanded = expandedLogId === log.id;
                  const isUp = log.user_feedback === 1;
                  const isDown = log.user_feedback === -1;

                  return (
                    <React.Fragment key={log.id}>
                      <tr 
                        onClick={() => toggleExpandLog(log.id)}
                        className={`hover:bg-slate-950/40 transition-colors cursor-pointer ${
                          isExpanded ? 'bg-slate-950/40' : ''
                        }`}
                      >
                        {/* Query Preview */}
                        <td className="py-3.5 px-5 max-w-[220px]">
                          <div className="flex items-center space-x-2">
                            <span className="text-xs font-semibold text-slate-200 truncate block">
                              {log.query}
                            </span>
                            {isExpanded ? <ChevronUp size={11} className="text-slate-550 shrink-0" /> : <ChevronDown size={11} className="text-slate-555 shrink-0" />}
                          </div>
                          <span className="text-[9px] text-slate-550 font-bold block mt-0.5">
                            {new Date(log.created_at).toLocaleString()}
                          </span>
                        </td>

                        {/* Latency */}
                        <td className="py-3.5 px-4 font-mono text-slate-350">
                          {log.latency_ms} ms
                        </td>

                        {/* Retrieved Chunks count */}
                        <td className="py-3.5 px-4 text-slate-350">
                          {log.retrieved_chunks_count} chunks
                        </td>

                        {/* Groundedness score */}
                        <td className="py-3.5 px-4">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getScoreColor(log.faithfulness_score)}`}>
                            {log.faithfulness_score !== null ? log.faithfulness_score.toFixed(2) : 'N/A'}
                          </span>
                        </td>

                        {/* Relevance score */}
                        <td className="py-3.5 px-4">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border ${getScoreColor(log.answer_relevance_score)}`}>
                            {log.answer_relevance_score !== null ? log.answer_relevance_score.toFixed(2) : 'N/A'}
                          </span>
                        </td>

                        {/* Associated Document */}
                        <td className="py-3.5 px-4 text-slate-450 max-w-[120px] truncate" title={log.document_name || 'N/A'}>
                          {log.document_name || <span className="text-slate-600 italic">None</span>}
                        </td>

                        {/* Feedback action */}
                        <td className="py-3.5 px-5 text-right" onClick={(e) => e.stopPropagation()}>
                          <div className="flex items-center justify-end space-x-1.5">
                            <button
                              onClick={() => handleToggleFeedback(log.id, log.user_feedback, 1)}
                              disabled={feedbackLoadingId === log.id}
                              className={`p-1 rounded-lg transition-colors cursor-pointer border ${
                                isUp 
                                  ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/25' 
                                  : 'text-slate-650 hover:text-slate-450 bg-slate-950/40 border-slate-900'
                              }`}
                              title="Good Answer"
                            >
                              <ThumbsUp size={10} />
                            </button>
                            <button
                              onClick={() => handleToggleFeedback(log.id, log.user_feedback, -1)}
                              disabled={feedbackLoadingId === log.id}
                              className={`p-1 rounded-lg transition-colors cursor-pointer border ${
                                isDown 
                                  ? 'text-rose-400 bg-rose-500/10 border-rose-500/25' 
                                  : 'text-slate-655 hover:text-slate-455 bg-slate-950/40 border-slate-900'
                              }`}
                              title="Bad Answer"
                            >
                              <ThumbsDown size={10} />
                            </button>
                          </div>
                        </td>
                      </tr>

                      {/* Expanded Details Row */}
                      {isExpanded && (
                        <tr className="bg-slate-950/35 border-b border-slate-950/50">
                          <td colSpan="7" className="py-4 px-6 text-xs text-slate-350 select-text leading-relaxed space-y-3">
                            <div className="space-y-1">
                              <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wide">Query Text:</span>
                              <p className="bg-slate-950/50 border border-slate-900 p-3 rounded-xl text-slate-200 font-semibold">{log.query}</p>
                            </div>
                            <div className="space-y-1">
                              <span className="text-[10px] font-bold text-indigo-400 uppercase tracking-wide">RAG Generated Answer:</span>
                              <p className="bg-slate-950/50 border border-slate-900 p-3 rounded-xl text-slate-300 whitespace-pre-wrap leading-relaxed">{log.answer}</p>
                            </div>
                          </td>
                        </tr>
                      )}
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
