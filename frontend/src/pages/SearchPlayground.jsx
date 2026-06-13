import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { Search, Brain, FileText, ArrowRight, CornerDownRight, AlertCircle, HelpCircle, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import DocumentDrawer from '../components/DocumentDrawer';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const SearchPlayground = () => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [searched, setSearched] = useState(false);
  const [previewDocumentId, setPreviewDocumentId] = useState(null);

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
    if (score >= 0.8) return 'text-emerald-700 bg-emerald-50 border border-emerald-100';
    if (score >= 0.7) return 'text-amber-700 bg-amber-50 border border-amber-100';
    return 'text-rose-700 bg-rose-50 border border-rose-100';
  };

  return (
    <div className="space-y-6 font-sans">
      
      {/* Title description */}
      <div className="space-y-1">
        <h1 className="text-lg font-bold tracking-tight text-[#18181b]">
          Semantic Search Playground
        </h1>
        <p className="text-xs text-zinc-500 max-w-2xl leading-relaxed">
          Query the index database. Search requests are automatically vectorized to identify matching content by mathematical similarity rather than text matching.
        </p>
      </div>

      {/* Main search panel */}
      <div className="bg-white border border-zinc-200/80 rounded-3xl p-5 shadow-sm space-y-4">
        <form onSubmit={(e) => handleSearch(e)} className="relative flex items-center">
          <div className="absolute left-4 text-zinc-400">
            <Search size={16} />
          </div>
          <input
            id="playground-search-box"
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type your question here (e.g. 'What are the main compliance guidelines?')"
            className="w-full bg-zinc-50/50 border border-zinc-200 hover:border-zinc-300 focus:border-[#18181b] focus:bg-white rounded-2xl py-3.5 pl-11 pr-32 text-[#18181b] placeholder-zinc-400 outline-none transition-all duration-200 text-xs md:text-sm shadow-inner"
          />
          <button
            type="submit"
            disabled={isLoading || !query.trim()}
            className="absolute right-2 px-4 py-2 bg-[#18181b] hover:bg-zinc-800 disabled:bg-zinc-105 disabled:text-zinc-400 text-white rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center space-x-1.5 btn-press-active shadow-sm"
          >
            <span>Ask RAG</span>
            <ArrowRight size={12} />
          </button>
        </form>

        {/* Suggestion Chips */}
        <div className="flex flex-wrap items-center gap-2 pt-1">
          <span className="text-[9px] font-bold text-zinc-400 uppercase tracking-wider mr-1">Suggestions:</span>
          {sampleQueries.map((q, idx) => (
            <button
              key={idx}
              onClick={(e) => handleSearch(e, q)}
              className="text-[10px] font-semibold bg-zinc-50 hover:bg-zinc-100 border border-zinc-200 text-zinc-650 hover:text-[#18181b] px-3.5 py-1.5 rounded-full transition-all cursor-pointer shadow-sm btn-press-active"
            >
              {q}
            </button>
          ))}
        </div>
      </div>

      {error && (
        <div className="flex items-start space-x-2.5 p-4 bg-rose-50 border border-rose-100 text-rose-800 rounded-2xl text-xs font-semibold animate-fade-in shadow-sm">
          <AlertCircle size={16} className="shrink-0 mt-0.5" />
          <p className="leading-relaxed">{error}</p>
        </div>
      )}

      {/* Results area */}
      <div className="space-y-4">
        {isLoading ? (
          /* Skeletons */
          <div className="space-y-3.5">
            {[1, 2, 3].map((idx) => (
              <div key={idx} className="bg-white border border-zinc-200 p-5 rounded-2xl space-y-4 animate-pulse shadow-sm">
                <div className="flex items-center justify-between">
                  <div className="h-3.5 w-40 bg-zinc-100 rounded-full"></div>
                  <div className="h-6 w-16 bg-zinc-100 rounded-full"></div>
                </div>
                <div className="space-y-2">
                  <div className="h-3 w-full bg-zinc-100 rounded-full"></div>
                  <div className="h-3 w-5/6 bg-zinc-100 rounded-full"></div>
                </div>
              </div>
            ))}
          </div>
        ) : searched && results.length === 0 ? (
          /* Empty state */
          <div className="text-center py-16 border border-dashed border-zinc-200 rounded-3xl bg-white max-w-lg mx-auto space-y-4 shadow-sm">
            <HelpCircle size={28} className="mx-auto text-zinc-300" />
            <div>
              <p className="text-xs font-bold text-[#18181b]">No matching chunks retrieved</p>
              <p className="text-[10px] text-zinc-500 mt-1 max-w-[280px] mx-auto leading-relaxed">
                Similarity matches fell below retrieval score thresholds. Try adjusting vocabulary queries or indexing additional content.
              </p>
            </div>
          </div>
        ) : !searched ? (
          /* Greeting */
          <div className="p-5 bg-zinc-50/50 border border-zinc-200 rounded-3xl flex items-start space-x-4 max-w-2xl shadow-sm animate-fade-in">
            <Brain size={18} className="text-zinc-500 mt-0.5 shrink-0" />
            <div className="space-y-1">
              <h4 className="text-xs font-bold text-[#18181b]">Cosine Similarity Searching</h4>
              <p className="text-[10.5px] text-zinc-500 leading-relaxed font-semibold">
                Platform retrieval utilizes a Cosine Similarity index calculation. The semantic query maps onto high-dimensional vector grids, ranking matching text coordinates by their alignment distance. This returns conceptual matches rather than literal keyword matches.
              </p>
            </div>
          </div>
        ) : (
          /* Hits listing */
          <div className="space-y-3.5">
            <h3 className="text-[9px] font-bold text-zinc-450 uppercase tracking-widest pl-1">
              Retrieval Hits ({results.length})
            </h3>
            
            <motion.div 
              initial="hidden"
              animate="show"
              variants={{
                show: { transition: { staggerChildren: 0.03 } }
              }}
              className="space-y-3"
            >
              {results.map((hit, index) => (
                <motion.div
                  key={index}
                  variants={{
                    hidden: { opacity: 0, y: 5 },
                    show: { opacity: 1, y: 0 }
                  }}
                  className="bg-white border border-zinc-200 hover:border-zinc-300 p-5 rounded-2xl space-y-3 transition-all duration-200 shadow-sm relative overflow-hidden group card-hover-effect"
                >
                  <div className="flex items-center justify-between gap-3 relative z-10">
                    <div className="flex items-center space-x-2.5 overflow-hidden">
                      <FileText size={13} className="text-zinc-450 shrink-0" />
                      <span className="text-xs font-bold text-[#18181b] truncate max-w-[150px] sm:max-w-xs">
                        {hit.document_name}
                      </span>
                      <span className="text-zinc-300 text-[10px]">•</span>
                      <span className="text-[10px] text-zinc-500 font-bold">Page {hit.page_number}</span>
                    </div>

                    <div className="flex items-center space-x-2 shrink-0">
                      <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-bold tracking-wide ${getScoreColor(hit.score)}`}>
                        {(hit.score * 100).toFixed(0)}% Match
                      </span>
                      
                      <button
                        onClick={() => setPreviewDocumentId(hit.document_id)}
                        className="p-1 bg-white border border-zinc-200 hover:border-zinc-400 rounded-lg text-zinc-650 hover:text-zinc-900 transition-all cursor-pointer shadow-sm btn-press-active"
                        title="View Document Details"
                      >
                        <ArrowRight size={11} />
                      </button>
                    </div>
                  </div>

                  {/* text snippet */}
                  <div className="flex items-start space-x-2.5 text-zinc-800 leading-relaxed text-xs bg-zinc-50/50 p-4.5 rounded-xl border border-zinc-150 font-sans relative z-10 select-text whitespace-pre-wrap">
                    <CornerDownRight size={13} className="text-zinc-400 shrink-0 mt-0.5" />
                    <p>{hit.chunk_text}</p>
                  </div>
                </motion.div>
              ))}
            </motion.div>
          </div>
        )}
      </div>

      {/* Slide-over document viewer */}
      <DocumentDrawer 
        documentId={previewDocumentId} 
        onClose={() => setPreviewDocumentId(null)} 
      />

    </div>
  );
};

export default SearchPlayground;
