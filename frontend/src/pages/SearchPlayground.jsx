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

  const handleSearch = async (e) => {
    e.preventDefault();
    const cleanQuery = query.strip ? query.strip() : query.trim();
    if (!cleanQuery) return;

    setIsLoading(true);
    setError('');
    setSearched(true);

    try {
      // Retrieve JWT token
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
    if (score >= 0.8) return 'text-emerald-400 bg-emerald-500/10 border border-emerald-500/20';
    if (score >= 0.7) return 'text-amber-400 bg-amber-500/10 border border-amber-500/20';
    return 'text-rose-400 bg-rose-500/10 border border-rose-500/20';
  };

  return (
    <div className="space-y-8 animate-fade-in font-sans">
      {/* Title Header */}
      <div className="space-y-2">
        <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-indigo-400 via-purple-400 to-cyan-400 bg-clip-text text-transparent">
          Semantic Search Playground
        </h1>
        <p className="text-sm text-slate-400 max-w-2xl leading-relaxed">
          Ask questions in plain English. DocumentIQ will encode your search phrase and query the Qdrant vector database to retrieve the most semantically relevant text fragments instantly.
        </p>
      </div>

      {/* Search Bar Panel */}
      <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 shadow-xl">
        <form onSubmit={handleSearch} className="relative flex items-center">
          <div className="absolute left-4.5 text-slate-500">
            <Search size={22} className="animate-pulse" />
          </div>
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type your question here (e.g. 'What are the document extraction specifications?')"
            className="w-full bg-slate-950/60 border border-slate-800 hover:border-slate-700/80 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-2xl py-4.5 pl-14 pr-32 text-slate-100 placeholder-slate-500 outline-none transition-all duration-300 font-medium text-sm md:text-base shadow-inner"
          />
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="absolute right-2 px-5 py-3 bg-gradient-to-r from-indigo-600 to-indigo-500 hover:from-indigo-500 hover:to-indigo-400 disabled:from-slate-800 disabled:to-slate-800 disabled:text-slate-600 text-white rounded-xl text-sm font-semibold transition-all duration-300 shadow-md cursor-pointer flex items-center space-x-1.5"
          >
            <span>Ask RAG</span>
            <ArrowRight size={14} />
          </button>
        </form>
      </div>

      {/* Error alert */}
      {error && (
        <div className="flex items-center space-x-3 p-4 bg-rose-500/10 border border-rose-500/25 text-rose-400 rounded-2xl text-sm font-medium">
          <AlertCircle size={20} className="shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {/* Search results list container */}
      <div className="space-y-6">
        {isLoading ? (
          // Loading Skeleton state
          <div className="space-y-4">
            {[1, 2, 3].map((idx) => (
              <div key={idx} className="bg-slate-900/40 border border-slate-850 p-6 rounded-3xl space-y-4 animate-pulse">
                <div className="flex items-center justify-between">
                  <div className="h-4 w-40 bg-slate-800 rounded-full"></div>
                  <div className="h-6 w-16 bg-slate-800 rounded-full"></div>
                </div>
                <div className="space-y-2">
                  <div className="h-4 w-full bg-slate-800 rounded-full"></div>
                  <div className="h-4 w-5/6 bg-slate-800 rounded-full"></div>
                </div>
              </div>
            ))}
          </div>
        ) : searched && results.length === 0 ? (
          // Empty state
          <div className="text-center py-16 border border-dashed border-slate-800 rounded-3xl bg-slate-900/20 max-w-xl mx-auto space-y-4">
            <HelpCircle size={44} className="mx-auto text-slate-600 animate-bounce" />
            <div>
              <p className="text-sm font-semibold text-slate-300">No matching text fragments retrieved</p>
              <p className="text-xs text-slate-500 mt-1.5 max-w-sm mx-auto leading-relaxed">
                We couldn't find matches with high vector similarity. Try phrasing your question differently or upload new documents first.
              </p>
            </div>
          </div>
        ) : !searched ? (
          // Initial greeting helper
          <div className="p-6 bg-slate-900/30 border border-slate-850 rounded-3xl flex items-start space-x-4 max-w-2xl">
            <Brain size={24} className="text-indigo-400 mt-0.5 shrink-0 animate-pulse" />
            <div className="space-y-2">
              <h4 className="text-sm font-bold text-slate-200">How does semantic search work?</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Unlike traditional keyword lookup (which searches for exact word matches), semantic search maps queries into vector spaces. It compares search intent to document context, bringing back matching ideas even if they use completely different wording.
              </p>
            </div>
          </div>
        ) : (
          // Retrieved fragments
          <div className="space-y-4">
            <h3 className="text-xs font-bold text-slate-500 uppercase tracking-widest pl-1">
              retrieved matches (ordered by similarity score)
            </h3>
            
            <div className="space-y-4">
              {results.map((hit, index) => (
                <div
                  key={index}
                  className="bg-slate-900 border border-slate-800/80 hover:border-slate-750 p-6 rounded-3xl space-y-4 transition-all duration-300 shadow-md group relative overflow-hidden"
                >
                  {/* Decorative glowing background on hover */}
                  <div className="absolute inset-0 bg-gradient-to-r from-indigo-500/5 to-cyan-500/0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none"></div>

                  <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 relative z-10">
                    {/* Document origin */}
                    <div className="flex items-center space-x-2">
                      <FileText size={16} className="text-indigo-400" />
                      <span className="text-sm font-semibold text-slate-200 group-hover:text-slate-100 transition-colors">
                        {hit.document_name}
                      </span>
                      <span className="text-slate-600 text-xs">•</span>
                      <span className="text-xs text-slate-400 font-medium">Page {hit.page_number}</span>
                    </div>

                    {/* Similarity Score Badge */}
                    <div className="flex items-center space-x-3 shrink-0">
                      <span className={`px-2.5 py-1 rounded-full text-xs font-bold tracking-wide ${getScoreColor(hit.score)}`}>
                        {Math.round(hit.score * 100)}% Match
                      </span>
                      
                      {/* Nav link to document details page */}
                      <Link
                        to={`/documents/${hit.document_id}`}
                        className="p-1.5 bg-slate-950 border border-slate-800 hover:border-indigo-500/30 hover:bg-indigo-500/10 rounded-lg text-slate-400 hover:text-indigo-400 transition-all cursor-pointer"
                        title="View Document Details"
                      >
                        <ArrowRight size={14} />
                      </Link>
                    </div>
                  </div>

                  {/* Retrieved text split snippet */}
                  <div className="flex items-start space-x-2 text-slate-350 leading-relaxed text-sm bg-slate-950/40 p-4 rounded-2xl border border-slate-850/60 font-sans relative z-10">
                    <CornerDownRight size={16} className="text-indigo-500 shrink-0 mt-0.5" />
                    <p className="select-text whitespace-pre-wrap">{hit.chunk_text}</p>
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
