import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, FileText, Calendar, HardDrive, Cpu, AlertTriangle, CheckCircle, Clock, Sparkles, Layers, ListOrdered, Binary, Copy, Check, Loader2 } from 'lucide-react';
import { motion } from 'framer-motion';

import { API_URL } from '../config';

const DocumentDetails = () => {
  const { id } = useParams();
  const [doc, setDoc] = useState(null);
  const [chunksData, setChunksData] = useState(null);
  const [embStats, setEmbStats] = useState(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isLoadingChunks, setIsLoadingChunks] = useState(true);
  const [isLoadingStats, setIsLoadingStats] = useState(true);
  const [error, setError] = useState('');
  const [activeTab, setActiveTab] = useState('text'); // 'text', 'chunks', or 'embeddings'
  const [copied, setCopied] = useState(false);

  const fetchDetails = async () => {
    try {
      const response = await axios.get(`${API_URL}/documents/${id}/preview`);
      setDoc(response.data);
      setError('');
    } catch (err) {
      console.error("Failed to load document details:", err);
      setError(err.response?.data?.detail || 'Failed to load details.');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchChunks = async () => {
    try {
      const response = await axios.get(`${API_URL}/documents/${id}/chunks`);
      setChunksData(response.data);
    } catch (err) {
      console.error("Failed to load document chunks:", err);
    } finally {
      setIsLoadingChunks(false);
    }
  };

  const fetchEmbeddingStats = async () => {
    try {
      const response = await axios.get(`${API_URL}/documents/${id}/embedding-stats`);
      setEmbStats(response.data);
    } catch (err) {
      console.error("Failed to load embedding stats:", err);
    } finally {
      setIsLoadingStats(false);
    }
  };

  useEffect(() => {
    fetchDetails();
    fetchChunks();
    fetchEmbeddingStats();
  }, [id]);

  useEffect(() => {
    if (!doc || ['INDEXED', 'EMBEDDED', 'FAILED', 'Completed'].includes(doc.status)) return;

    const interval = setInterval(() => {
      fetchDetails();
      fetchChunks();
      fetchEmbeddingStats();
    }, 2000);

    return () => clearInterval(interval);
  }, [doc]);

  const handleCopyText = () => {
    if (!doc?.extracted_text_preview) return;
    navigator.clipboard.writeText(doc.extracted_text_preview);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  if (isLoading) {
    return (
      <div className="flex h-96 items-center justify-center text-zinc-400">
        <div className="flex flex-col items-center space-y-3">
          <Loader2 className="animate-spin text-zinc-650" size={24} />
          <p className="text-[9px] font-bold uppercase tracking-widest text-zinc-450 animate-pulse">Retrieving details...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-50 border border-rose-100 rounded-2xl p-6 text-center max-w-xl mx-auto space-y-4 animate-fade-in mt-12 shadow-sm">
        <AlertTriangle size={28} className="mx-auto text-rose-700" />
        <p className="text-rose-700 font-semibold text-xs leading-relaxed">{error}</p>
        <Link to="/dashboard" className="inline-flex items-center space-x-1.5 text-[9.5px] font-bold text-[#18181b] hover:underline uppercase tracking-wider">
          <ArrowLeft size={12} />
          <span>Back to Workspace</span>
        </Link>
      </div>
    );
  }

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

  const getEmbeddingsProgress = () => {
    if (!embStats || embStats.total_chunks === 0) return 0;
    return Math.round((embStats.embedded_chunks / embStats.total_chunks) * 100);
  };

  return (
    <div className="space-y-4 font-sans">
      
      {/* Return Navigation Link */}
      <div>
        <Link to="/dashboard" className="inline-flex items-center space-x-1.5 text-[9px] font-bold text-zinc-500 hover:text-[#18181b] transition-colors uppercase tracking-wider">
          <ArrowLeft size={12} />
          <span>Back to Workspace</span>
        </Link>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left column: properties summary card */}
        <div className="lg:col-span-1">
          <div className="bg-white border border-zinc-200/80 rounded-3xl p-5 space-y-5 shadow-sm">
            <div className="flex items-center space-x-3 pb-3 border-b border-zinc-150">
              <div className="p-2.5 bg-zinc-50 border border-zinc-200 rounded-xl text-zinc-605">
                <FileText size={18} />
              </div>
              <div className="overflow-hidden">
                <h2 className="text-xs font-bold text-[#18181b] truncate" title={doc.filename}>{doc.filename}</h2>
                <p className="text-[9px] text-zinc-500 font-bold uppercase mt-0.5">ID: #{doc.id}</p>
              </div>
            </div>

            {/* Property list */}
            <div className="space-y-3.5 text-[10.5px] font-semibold text-zinc-650">
              <div className="flex items-center justify-between">
                <span>Ingestion Status</span>
                {getStatusBadge(doc.status)}
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-1.5 text-zinc-450">
                  <HardDrive size={13} />
                  <span>Size</span>
                </div>
                <span className="text-[#18181b]">{doc.size}</span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-1.5 text-zinc-455">
                  <Calendar size={13} />
                  <span>Index Date</span>
                </div>
                <span className="text-[#18181b]">
                  {new Date(doc.created_at).toLocaleDateString()}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-1.5 text-zinc-455">
                  <Cpu size={13} />
                  <span>Pages</span>
                </div>
                <span className="text-[#18181b]">{doc.page_count} pages</span>
              </div>

              {chunksData && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1.5 text-zinc-455">
                    <Layers size={13} />
                    <span>Chunks</span>
                  </div>
                  <span className="text-[#18181b]">{chunksData.total_chunks} blocks</span>
                </div>
              )}

              {doc.ocr_confidence !== null && doc.ocr_confidence !== undefined && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-1.5 text-zinc-455">
                    <Sparkles size={13} />
                    <span>OCR Avg Acc</span>
                  </div>
                  <span className="text-[#18181b] font-bold">{(doc.ocr_confidence * 100).toFixed(1)}%</span>
                </div>
              )}
            </div>

            {!['INDEXED', 'EMBEDDED', 'Completed', 'FAILED'].includes(doc.status) && (
              <div className="p-3.5 bg-amber-50/40 border border-amber-100 rounded-xl flex items-start space-x-2.5 animate-pulse">
                <Sparkles size={13} className="text-amber-700 shrink-0 mt-0.5" />
                <p className="text-[10px] text-amber-800 leading-relaxed font-medium">
                  Generating dense vector descriptors and pushing chunks into Qdrant collections. Preview updates will automatically refresh.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Right column: Tabbed Viewport */}
        <div className="lg:col-span-2">
          <div className="bg-white border border-zinc-200/80 rounded-3xl p-5 flex flex-col h-[520px] shadow-sm">
            {/* Tabs navigations */}
            <div className="pb-3 border-b border-zinc-150 flex items-center justify-between">
              <div className="flex space-x-5">
                {[
                  { id: 'text', label: 'Extracted Text' },
                  { id: 'chunks', label: 'Semantic Chunks' },
                  { id: 'embeddings', label: 'Embedding Stats' }
                ].map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setActiveTab(t.id)}
                    className={`pb-2 text-[9.5px] font-bold uppercase tracking-wider border-b-2 transition-all cursor-pointer ${
                      activeTab === t.id
                        ? 'border-[#18181b] text-[#18181b] font-extrabold'
                        : 'border-transparent text-zinc-450 hover:text-zinc-700'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              
              <span className="text-[9px] text-zinc-450 font-bold uppercase tracking-wider">
                {activeTab === 'text' && 'Text preview'}
                {activeTab === 'chunks' && `${chunksData?.total_chunks || 0} blocks`}
                {activeTab === 'embeddings' && `all-MiniLM-L6-v2`}
              </span>
            </div>

            {/* Viewport page panels */}
            <div className="flex-1 overflow-y-auto mt-4 hide-scrollbar select-text">
              {activeTab === 'text' && (
                <div className="relative h-full flex flex-col">
                  {doc.extracted_text_preview ? (
                    <>
                      <div className="absolute right-3.5 top-3.5 z-10">
                        <button
                          onClick={handleCopyText}
                          className="p-2 bg-white hover:bg-zinc-50 border border-zinc-200 rounded-xl text-zinc-500 hover:text-zinc-800 transition-all cursor-pointer btn-press-active shadow-sm"
                          title="Copy text preview"
                        >
                          {copied ? <Check size={13} className="text-emerald-600" /> : <Copy size={13} />}
                        </button>
                      </div>
                      <div className="flex-1 bg-zinc-50/50 border border-zinc-150 rounded-2xl p-4.5 font-mono text-[10.5px] leading-relaxed text-[#18181b] whitespace-pre-wrap overflow-y-auto min-h-[300px]">
                        {doc.extracted_text_preview}
                      </div>
                    </>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center py-20 text-zinc-400 italic text-xs">
                      No extracted text is currently available.
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'chunks' && (
                <div className="space-y-4">
                  {isLoadingChunks ? (
                    <div className="py-20 flex flex-col items-center justify-center space-y-2 text-zinc-500">
                      <Loader2 className="animate-spin text-zinc-650" size={20} />
                      <p className="text-[10px] font-bold uppercase tracking-wider">Analyzing splits...</p>
                    </div>
                  ) : !chunksData || chunksData.chunks.length === 0 ? (
                    <div className="py-20 text-center border border-dashed border-zinc-200 rounded-2xl bg-zinc-50/50">
                      <Layers size={28} className="mx-auto text-zinc-400 mb-2.5" />
                      <p className="text-xs font-bold text-zinc-650">No chunks available yet</p>
                      <p className="text-[10px] text-zinc-500 mt-1">Chunking runs automatically after text parsing completes.</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* block info grid */}
                      <div className="grid grid-cols-3 gap-4 bg-zinc-50 border border-zinc-200 p-4 rounded-xl text-center font-semibold text-zinc-655 text-[10.5px]">
                        <div>
                          <p className="text-[8.5px] text-zinc-450 font-bold uppercase tracking-wider">Pages</p>
                          <p className="text-xs font-bold text-[#18181b] mt-0.5">{chunksData.page_count}</p>
                        </div>
                        <div className="border-x border-zinc-200">
                          <p className="text-[8.5px] text-zinc-450 font-bold uppercase tracking-wider">Total Chunks</p>
                          <p className="text-xs font-bold text-[#18181b] mt-0.5">{chunksData.total_chunks}</p>
                        </div>
                        <div>
                          <p className="text-[8.5px] text-zinc-450 font-bold uppercase tracking-wider">Avg Size</p>
                          <p className="text-xs font-bold text-[#18181b] mt-0.5">{chunksData.average_chunk_size} ch</p>
                        </div>
                      </div>

                      {/* lists */}
                      <div className="space-y-3 pb-3">
                        {chunksData.chunks.map((chunk, index) => (
                          <div key={chunk.id || index} className="bg-white border border-zinc-200 p-4 rounded-xl space-y-2 hover:border-zinc-350 transition-all">
                            <div className="flex items-center justify-between text-[9px] font-bold text-zinc-500 uppercase">
                              <span className="flex items-center space-x-1">
                                <ListOrdered size={11} />
                                <span>Chunk #{index + 1}</span>
                              </span>
                              <span className="text-zinc-455 flex space-x-2">
                                <span>Page {chunk.page_number}</span>
                                <span>•</span>
                                <span>{chunk.chunk_length} chars</span>
                              </span>
                            </div>
                            <div className="text-[10.5px] leading-relaxed text-zinc-850 p-3 bg-zinc-50/50 rounded-lg border border-zinc-150">
                              {chunk.chunk_text}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'embeddings' && (
                <div className="space-y-4 pb-3">
                  {isLoadingStats ? (
                    <div className="py-20 flex flex-col items-center justify-center space-y-2">
                      <Loader2 className="animate-spin text-zinc-650" size={20} />
                      <p className="text-[10px] font-bold uppercase">Resolving dimensions...</p>
                    </div>
                  ) : !embStats ? (
                    <div className="py-20 text-center border border-dashed border-zinc-200 rounded-2xl bg-zinc-50/30">
                      <Binary size={28} className="mx-auto text-zinc-400 mb-2.5" />
                      <p className="text-xs font-bold text-zinc-650">Embedding stats not available</p>
                    </div>
                  ) : (
                    <div className="space-y-5">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-zinc-50/50 border border-zinc-200 p-4 rounded-xl">
                          <p className="text-[8.5px] text-zinc-450 font-bold uppercase tracking-wider font-sans">Vector Model</p>
                          <p className="text-xs font-bold text-[#18181b] mt-0.5">{embStats.model_name}</p>
                        </div>
                        <div className="bg-zinc-50/50 border border-zinc-200 p-4 rounded-xl">
                          <p className="text-[8.5px] text-zinc-450 font-bold uppercase tracking-wider font-sans">Dimensions</p>
                          <p className="text-xs font-bold text-[#18181b] mt-0.5">{embStats.vector_dimension} dimensions</p>
                        </div>
                      </div>

                      {/* Vector Progress panel */}
                      <div className="bg-white border border-zinc-200 p-5 rounded-2xl space-y-3.5">
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="text-xs font-bold text-[#18181b]">Vector Indexing Progress</h4>
                            <p className="text-[10px] text-zinc-500 mt-0.5">Chunks pushed to Qdrant collection</p>
                          </div>
                          <span className="text-xs font-extrabold text-[#18181b]">{getEmbeddingsProgress()}%</span>
                        </div>

                        <div className="w-full bg-zinc-100 h-2 rounded-full overflow-hidden">
                          <div 
                            className="bg-[#18181b] h-full rounded-full transition-all duration-300"
                            style={{ width: `${getEmbeddingsProgress()}%` }}
                          ></div>
                        </div>

                        <div className="flex justify-between text-[9px] text-zinc-450 font-bold uppercase tracking-wider">
                          <span>{embStats.embedded_chunks} chunks vectorized</span>
                          <span>{embStats.total_chunks} total</span>
                        </div>
                      </div>

                      {/* Callout */}
                      <div className="p-4 bg-emerald-50/40 border border-emerald-100 rounded-2xl flex items-start space-x-3">
                        <Sparkles size={15} className="text-emerald-700 shrink-0 mt-0.5" />
                        <div>
                          <h4 className="text-xs font-bold text-emerald-800">Intelligent Semantic Indexing</h4>
                          <p className="text-[11px] text-emerald-950 mt-1 leading-relaxed">
                            Text chunks are processed through sentence transformers to construct 384-dimensional dense vectors. These vectors are mapped onto the SQLite relational documents schema and indexed in Qdrant collections to support rapid cosine similarity searches.
                          </p>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>

      </div>
    </div>
  );
};

export default DocumentDetails;
