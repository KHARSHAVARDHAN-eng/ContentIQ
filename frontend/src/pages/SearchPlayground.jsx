import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Search, Brain, FileText, ArrowRight, CornerDownRight, Sparkles, AlertCircle, HelpCircle } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const SearchPlayground = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);

  const sampleQueries = [
    "What is the core theme of this document?",
    "Show me the key project milestones",
    "Are there any compliance risks mentioned?",
    "Summarize the financial performance metrics"
  ];

  const handleSearch = async (e, customQuery = null) => {
    if (e) e.preventDefault();
    const activeQuery = customQuery !== null ? customQuery : query;
    const cleanQuery = activeQuery.strip ? activeQuery.strip() : activeQuery.trim();
    if (!cleanQuery) return;

    if (customQuery !== null) {
      setQuery(customQuery);
    }

    setIsLoading(true);
    setError('');
    setSearched(true);

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/search`,
        { query: cleanQuery },
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      );
      setResults(response.data.chunks || []);
    } catch (err) {
      console.error("Semantic search failed:", err);
      setError(err.response?.data?.detail || 'An error occurred during semantic retrieval.');
    } finally {
      setIsLoading(false);
    }
  };

  const getScoreColor = (score) => {
    if (score >= 0.8) return 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/10';
    if (score >= 0.7) return 'text-amber-400 bg-amber-500/10 border border-amber-500/10';
    return 'text-rose-400 bg-rose-500/10 border border-rose-500/10';
  };

  return (
    <div className="space-y-6 animate-fade-in font-sans">
      
      {/* Title & Description Grid Header */}
      <div className="space-y-2">
        <h1 className="text-2xl md:text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 via-purple-300 to-cyan-300 bg-clip-text text-transparent">
          Semantic Search Playground
        </h1>
        <p className="text-xs md:text-sm text-slate-400 max-w-2xl leading-relaxed">
          Explore vector matching in real-time. Input questions in plain language to vectorize the query on-the-fly, run similarity comparison in Qdrant, and fetch matching text passages.
        </p>
      </div>

      {/* Primary search container */}
      <div className="bg-slate-900/60 backdrop-blur-md border border-slate-900 rounded-3xl p-6 shadow-sm space-y-4">
        <form onSubmit={(e) => handleSearch(e)} className="relative flex items-center">
          <div className="absolute left-4.5 text-slate-500">
            <Search size={20} className="animate-pulse" />
          </div>
          <input
            id="playground-query-input"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search matching document details (e.g. 'What is the refund policy?')"
            className="w-full bg-slate-950/60 border border-slate-800 hover:border-slate-700/80 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/20 rounded-2xl py-4 pl-13 pr-32 text-slate-100 placeholder-slate-650 outline-none transition-all duration-300 text-xs md:text-sm shadow-inner"
          />
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="absolute right-2 px-4 py-2.5 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-650 text-white rounded-xl text-xs font-bold transition-all duration-300 shadow-md cursor-pointer flex items-center space-x-1.5"
          >
            <span>Run Retrieval</span>
            <ArrowRight size={12} />
          </button>
        </form>

        {/* Suggested Queries Chips */}
        <div className="flex flex-wrap items-center gap-2 pt-1.5">
          <span className="text-[10px] font-bold text-slate-550 uppercase mr-1">Suggestions:</span>
          {sampleQueries.map((q, idx) => (
            <button
              key={idx}
              onClick={(e) => handleSearch(e, q)}
              className="text-[10px] font-semibold bg-slate-950/40 hover:bg-slate-900 border border-slate-850 hover:border-indigo-500/30 text-slate-450 hover:text-indigo-400 px-3 py-1.5 rounded-full transition-all cursor-pointer"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {/* Error indicator */}
      {error && (
        <div className="flex items-start space-x-3 p-4 bg-rose-500/5 border border-rose-500/15 text-rose-450 rounded-2xl text-xs font-medium animate-fade-in">
          <AlertCircle size={18} className="shrink-0 mt-0.5" />
          <p className="leading-relaxed">{error}</p>
        </div>
      )}

      {/* Results viewport */}
      <div className="space-y-4">
        {isLoading ? (
          /* Modern loading skeleton blocks */
          <div className="space-y-4">
            {[1, 2, 3].map((idx) => (
              <div key={idx} className="bg-slate-900/40 border border-slate-900 p-5 rounded-2xl space-y-4 animate-pulse">
                <div className="flex items-center justify-between">
                  <div className="h-3.5 w-48 bg-slate-800 rounded-full"></div>
                  <div className="h-6 w-16 bg-slate-800 rounded-full"></div>
                </div>
                <div className="space-y-2">
                  <div className="h-3 w-full bg-slate-800 rounded-full"></div>
                  <div className="h-3 w-4/5 bg-slate-800 rounded-full"></div>
                </div>
              </div>
            ))}
          </div>
        ) : searched && results.length === 0 ? (
          /* Empty state */
          <div className="text-center py-16 border border-dashed border-slate-850 rounded-3xl bg-slate-900/10 max-w-lg mx-auto space-y-4 animate-fade-in">
            <HelpCircle size={36} className="mx-auto text-slate-750" />
            <div>
              <p className="text-xs font-bold text-slate-300">No matching chunks retrieved</p>
              <p className="text-[10px] text-slate-500 mt-1 max-w-[280px] mx-auto leading-relaxed">
                Similarity matches fell below retrieval score thresholds. Try adjusting vocabulary queries or indexing additional content.
              </p>
            </div>
          </div>
        ) : !searched ? (
          /* Initial helper greeting */
          <div className="p-5 bg-slate-900/20 border border-slate-900 rounded-3xl flex items-start space-x-4 max-w-2xl">
            <Brain size={22} className="text-indigo-400 mt-0.5 shrink-0 animate-pulse" />
            <div className="space-y-1.5">
              <h4 className="text-xs font-bold text-slate-200">Similarity Metric Explained</h4>
              <p className="text-[11px] text-slate-400 leading-relaxed">
                Platform retrieval utilizes a Cosine Similarity index calculation. The semantic query maps onto high-dimensional math grids, ranking matching text coordinates by their alignment distance. This returns ideas rather than literal keyword matches.
              </p>
            </div>
          </div>
        ) : (
          /* Result rows listing */
          <div className="space-y-4 animate-fade-in">
            <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest pl-1">
              Similarity Search Hits ({results.length})
            </h3>
            
            <div className="space-y-3">
              {results.map((hit, index) => (
                <div
                  key={index}
                  className="bg-slate-900/60 border border-slate-900 hover:border-slate-850 p-5 rounded-2xl space-y-3 transition-all duration-350 shadow-sm relative overflow-hidden group"
                >
                  <div className="absolute inset-y-0 left-0 w-1 bg-gradient-to-b from-indigo-500 to-cyan-500 transform scale-y-0 group-hover:scale-y-100 transition-transform duration-300"></div>
                  
                  <div className="flex items-center justify-between gap-3 relative z-10">
                    <div className="flex items-center space-x-2.5 overflow-hidden">
                      <FileText size={14} className="text-indigo-400 shrink-0" />
                      <span className="text-xs font-semibold text-slate-200 group-hover:text-indigo-400 transition-colors truncate max-w-[150px] sm:max-w-xs">
                        {hit.document_name}
                      </span>
                      <span className="text-slate-650 text-[10px]">•</span>
                      <span className="text-[10px] text-slate-500 font-bold">Page {hit.page_number}</span>
                    </div>

                    <div className="flex items-center space-x-2 shrink-0">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wide ${getScoreColor(hit.score)}`}>
                        {(hit.score * 100).toFixed(0)}% Match
                      </span>
                      
                      <Link
                        to={`/documents/${hit.document_id}`}
                        className="p-1 bg-slate-950 border border-slate-850 hover:border-indigo-500/30 hover:bg-indigo-500/10 rounded-lg text-slate-500 hover:text-indigo-400 transition-all cursor-pointer"
                        title="View page metadata"
                      >
                        <ArrowRight size={12} />
                      </Link>
                    </div>
                  </div>

                  {/* snippet block */}
                  <div className="flex items-start space-x-2.5 text-slate-350 leading-relaxed text-xs bg-slate-950/40 p-4 rounded-xl border border-slate-900/60 font-sans relative z-10 select-text whitespace-pre-wrap">
                    <CornerDownRight size={14} className="text-indigo-500 shrink-0 mt-0.5" />
                    <p>{hit.chunk_text}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchPlayground;
