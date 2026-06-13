import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { X, FileText, Layers, Binary, HardDrive, Calendar, Cpu, Sparkles, Loader2, CheckCircle, AlertTriangle, Clock, Copy, Check } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const DocumentDrawer = ({ documentId, onClose }) => {
  const [doc, setDoc] = useState(null);
  const [chunksData, setChunksData] = useState(null);
  const [embStats, setEmbStats] = useState(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeTab, setActiveTab] = useState('text'); // 'text', 'chunks', 'embeddings'
  const [copied, setCopied] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!documentId) {
      setDoc(null);
      setChunksData(null);
      setEmbStats(null);
      return;
    }

    const fetchAllData = async () => {
      setIsLoading(true);
      setError('');
      try {
        const token = localStorage.getItem('token');
        const headers = { Authorization: `Bearer ${token}` };

        // Fetch preview details
        const detailsResp = await axios.get(`${API_URL}/documents/${documentId}/preview`, { headers });
        setDoc(detailsResp.data);

        // Fetch chunks
        try {
          const chunksResp = await axios.get(`${API_URL}/documents/${documentId}/chunks`, { headers });
          setChunksData(chunksResp.data);
        } catch (e) {
          console.error("Failed to load chunks:", e);
        }

        // Fetch embedding stats
        try {
          const statsResp = await axios.get(`${API_URL}/documents/${documentId}/embedding-stats`, { headers });
          setEmbStats(statsResp.data);
        } catch (e) {
          console.error("Failed to load embedding stats:", e);
        }

      } catch (err) {
        console.error("Failed to load document info:", err);
        setError("Failed to retrieve document details.");
      } finally {
        setIsLoading(false);
      }
    };

    fetchAllData();
  }, [documentId]);

  const handleCopyText = () => {
    if (!doc?.extracted_text_preview) return;
    navigator.clipboard.writeText(doc.extracted_text_preview);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getStatusBadge = (status) => {
    switch (status) {
      case 'INDEXED':
      case 'Completed':
      case 'EMBEDDED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100">
            <CheckCircle size={10} />
            <span>Indexed</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-100">
            <AlertTriangle size={10} />
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-100 animate-pulse">
            <Clock className="animate-spin" size={10} />
            <span>Processing</span>
          </span>
        );
    }
  };

  return (
    <AnimatePresence>
      {documentId && (
        <>
          {/* Backdrop Overlay */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 0.15 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black z-40 cursor-default"
          />

          {/* Slide-over Drawer Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 28, stiffness: 220 }}
            className="fixed top-0 right-0 h-full w-full max-w-md md:max-w-xl bg-white border-l border-zinc-200 shadow-2xl z-50 flex flex-col overflow-hidden"
          >
            {/* Drawer Header */}
            <div className="p-4.5 border-b border-zinc-150 flex items-center justify-between bg-zinc-50/50">
              <div className="flex items-center space-x-3 overflow-hidden">
                <div className="p-2 bg-zinc-100 rounded-lg text-zinc-650 shrink-0">
                  <FileText size={16} />
                </div>
                <div className="overflow-hidden">
                  <h3 className="text-xs font-bold text-[#18181b] truncate pr-2" title={doc?.filename || 'Document Info'}>
                    {doc?.filename || 'Loading Document...'}
                  </h3>
                  <p className="text-[9px] text-zinc-500 font-bold uppercase tracking-wider mt-0.5">
                    {doc ? `ID: #${doc.id}` : 'Retrieving...'}
                  </p>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 hover:bg-zinc-200/60 rounded-lg text-zinc-500 hover:text-zinc-800 transition-colors cursor-pointer btn-press-active"
              >
                <X size={15} />
              </button>
            </div>

            {/* Error or Loader */}
            {isLoading ? (
              <div className="flex-1 flex flex-col items-center justify-center space-y-3">
                <Loader2 className="animate-spin text-zinc-650" size={24} />
                <p className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest animate-pulse">Loading Metadata...</p>
              </div>
            ) : error ? (
              <div className="flex-1 p-6 text-center space-y-3 flex flex-col items-center justify-center">
                <AlertTriangle size={32} className="text-rose-600" />
                <p className="text-zinc-700 text-xs font-semibold">{error}</p>
                <button
                  onClick={onClose}
                  className="px-4 py-2 bg-[#18181b] hover:bg-zinc-800 text-white rounded-xl text-xs font-bold transition-all"
                >
                  Close Drawer
                </button>
              </div>
            ) : doc ? (
              <div className="flex-1 flex flex-col overflow-hidden">
                {/* Meta details list */}
                <div className="p-4.5 border-b border-zinc-150 bg-[#fafafa] grid grid-cols-2 sm:grid-cols-4 gap-4 text-[10px] font-semibold text-zinc-500">
                  <div className="space-y-1">
                    <span className="text-[8.5px] uppercase font-bold text-zinc-400 block tracking-wider">Status</span>
                    {getStatusBadge(doc.status)}
                  </div>
                  <div className="space-y-1">
                    <span className="text-[8.5px] uppercase font-bold text-zinc-400 block tracking-wider">File Size</span>
                    <span className="text-[#18181b] block mt-0.5">{doc.size}</span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-[8.5px] uppercase font-bold text-zinc-400 block tracking-wider">Total Pages</span>
                    <span className="text-[#18181b] block mt-0.5">{doc.page_count} pages</span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-[8.5px] uppercase font-bold text-zinc-400 block tracking-wider">OCR Avg Acc</span>
                    <span className="text-[#18181b] block mt-0.5 font-bold">
                      {doc.ocr_confidence !== null && doc.ocr_confidence !== undefined 
                        ? `${(doc.ocr_confidence * 100).toFixed(1)}%` 
                        : 'N/A'}
                    </span>
                  </div>
                </div>

                {/* Tabs navigations */}
                <div className="px-4.5 pt-2 flex items-center justify-between border-b border-zinc-150">
                  <div className="flex space-x-4">
                    {[
                      { id: 'text', label: 'Extracted Text' },
                      { id: 'chunks', label: 'Semantic Chunks' },
                      { id: 'embeddings', label: 'Embedding Stats' }
                    ].map((t) => (
                      <button
                        key={t.id}
                        onClick={() => setActiveTab(t.id)}
                        className={`pb-2.5 text-[9.5px] font-bold uppercase tracking-wider border-b-2 transition-all cursor-pointer ${
                          activeTab === t.id
                            ? 'border-[#18181b] text-[#18181b] font-extrabold'
                            : 'border-transparent text-zinc-450 hover:text-zinc-700'
                        }`}
                      >
                        {t.label}
                      </button>
                    ))}
                  </div>
                  <span className="text-[8.5px] text-zinc-450 font-bold uppercase tracking-wider">
                    {activeTab === 'text' && 'Text preview'}
                    {activeTab === 'chunks' && `${chunksData?.total_chunks || 0} blocks`}
                    {activeTab === 'embeddings' && 'Qdrant parameters'}
                  </span>
                </div>

                {/* Viewport Panels */}
                <div className="flex-1 overflow-y-auto p-4.5 select-text hide-scrollbar">
                  {activeTab === 'text' && (
                    <div className="relative h-full flex flex-col">
                      {doc.extracted_text_preview ? (
                        <>
                          <div className="absolute right-2.5 top-2.5 z-10">
                            <button
                              onClick={handleCopyText}
                              className="p-1.5 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-lg text-zinc-500 hover:text-zinc-800 transition-all cursor-pointer shadow-sm btn-press-active"
                              title="Copy text preview"
                            >
                              {copied ? <Check size={12} className="text-emerald-600" /> : <Copy size={12} />}
                            </button>
                          </div>
                          <div className="flex-1 bg-zinc-50/50 border border-zinc-150 rounded-xl p-4 font-mono text-[10.5px] leading-relaxed text-zinc-800 whitespace-pre-wrap overflow-y-auto min-h-[300px]">
                            {doc.extracted_text_preview}
                          </div>
                        </>
                      ) : (
                        <div className="flex-1 flex flex-col items-center justify-center py-20 text-zinc-400 italic text-xs">
                          No text preview available.
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'chunks' && (
                    <div className="space-y-4">
                      {!chunksData || chunksData.chunks.length === 0 ? (
                        <div className="py-20 text-center border border-dashed border-zinc-200 rounded-xl bg-zinc-50/50">
                          <Layers size={24} className="mx-auto text-zinc-400 mb-2" />
                          <p className="text-xs font-bold text-zinc-700">No chunks available yet</p>
                          <p className="text-[9.5px] text-zinc-500 mt-1">Chunking runs automatically after text parsing.</p>
                        </div>
                      ) : (
                        <div className="space-y-3 pb-3">
                          {chunksData.chunks.map((chunk, idx) => (
                            <div key={chunk.id || idx} className="bg-white border border-zinc-200 p-3.5 rounded-xl space-y-1.5 hover:border-zinc-350 transition-all">
                              <div className="flex items-center justify-between text-[8.5px] font-bold text-zinc-500 uppercase">
                                <span>Block #{idx + 1}</span>
                                <span className="flex space-x-2">
                                  <span>Page {chunk.page_number}</span>
                                  <span>•</span>
                                  <span>{chunk.chunk_length} chars</span>
                                </span>
                              </div>
                              <div className="text-[10.5px] leading-relaxed text-zinc-800 p-2.5 bg-zinc-50/50 rounded-lg border border-zinc-150">
                                {chunk.chunk_text}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  )}

                  {activeTab === 'embeddings' && (
                    <div className="space-y-4 pb-3">
                      {!embStats ? (
                        <div className="py-20 text-center border border-dashed border-zinc-200 rounded-xl bg-zinc-50/50">
                          <Binary size={24} className="mx-auto text-zinc-400 mb-2" />
                          <p className="text-xs font-bold text-zinc-700">Embedding stats not available</p>
                        </div>
                      ) : (
                        <div className="space-y-4">
                          <div className="grid grid-cols-2 gap-3">
                            <div className="bg-zinc-50/50 border border-zinc-200 p-3.5 rounded-xl">
                              <p className="text-[8px] text-zinc-400 font-bold uppercase tracking-wider font-sans">Vector Model</p>
                              <p className="text-[11px] font-bold text-[#18181b] mt-0.5">{embStats.model_name}</p>
                            </div>
                            <div className="bg-zinc-50/50 border border-zinc-200 p-3.5 rounded-xl">
                              <p className="text-[8px] text-zinc-400 font-bold uppercase tracking-wider font-sans">Dimensions</p>
                              <p className="text-[11px] font-bold text-[#18181b] mt-0.5">{embStats.vector_dimension} dimensions</p>
                            </div>
                          </div>

                          <div className="bg-white border border-zinc-200 p-4 rounded-xl space-y-2.5">
                            <div className="flex items-center justify-between text-[11px]">
                              <div>
                                <h4 className="font-bold text-[#18181b]">Vector Indexing Progress</h4>
                                <p className="text-[9.5px] text-zinc-500 mt-0.5">Chunks pushed to Qdrant collection</p>
                              </div>
                              <span className="font-extrabold text-[#18181b]">
                                {embStats.total_chunks > 0 ? Math.round((embStats.embedded_chunks / embStats.total_chunks) * 100) : 0}%
                              </span>
                            </div>

                            <div className="w-full bg-zinc-100 h-1.5 rounded-full overflow-hidden">
                              <div 
                                className="bg-[#18181b] h-full rounded-full transition-all duration-300"
                                style={{ width: `${embStats.total_chunks > 0 ? (embStats.embedded_chunks / embStats.total_chunks) * 100 : 0}%` }}
                              ></div>
                            </div>

                            <div className="flex justify-between text-[8.5px] text-zinc-400 font-bold uppercase tracking-wider">
                              <span>{embStats.embedded_chunks} vectorized</span>
                              <span>{embStats.total_chunks} total</span>
                            </div>
                          </div>

                          <div className="p-3.5 bg-emerald-50/40 border border-emerald-100 rounded-xl flex items-start space-x-2.5">
                            <Sparkles size={14} className="text-emerald-700 shrink-0 mt-0.5" />
                            <div className="space-y-0.5">
                              <h4 className="text-[10px] font-bold text-emerald-800 uppercase tracking-wider">Semantic Index Details</h4>
                              <p className="text-[10px] text-emerald-950 leading-relaxed">
                                Document chunks are vectorized into a dense 384-dimensional vector space using sentence transformers. These vector representations are then indexed in Qdrant collections to support rapid semantic search.
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            ) : null}
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};

export default DocumentDrawer;
