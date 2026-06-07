import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, FileText, Calendar, HardDrive, Cpu, AlertTriangle, CheckCircle, Clock, Sparkles, Layers, ListOrdered, Binary, Copy, Check } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

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

  // Poll for updates if document is not completely embedded or failed
  useEffect(() => {
    if (!doc || doc.status === 'EMBEDDED' || doc.status === 'FAILED' || doc.status === 'INDEXED' || doc.status === 'Completed') return;

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
      <div className="flex h-96 items-center justify-center text-slate-400">
        <div className="flex flex-col items-center space-y-4">
          <Loader2 className="animate-spin text-indigo-500" size={36} />
          <p className="text-xs font-semibold tracking-wider text-slate-500 uppercase">Parsing Extraction Index...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-500/5 border border-rose-500/15 rounded-3xl p-6 text-center max-w-xl mx-auto space-y-4 animate-fade-in mt-12">
        <AlertTriangle size={36} className="mx-auto text-rose-450 animate-bounce" />
        <p className="text-rose-400 font-semibold text-sm">{error}</p>
        <Link to="/dashboard" className="inline-flex items-center space-x-2 text-xs font-bold text-indigo-400 hover:text-indigo-300 uppercase tracking-wider">
          <ArrowLeft size={14} />
          <span>Back to Workspace</span>
        </Link>
      </div>
    );
  }

  const getStatusBadge = (status) => {
    switch (status) {
      case 'INDEXED':
      case 'Completed':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/10">
            <CheckCircle size={12} />
            <span>Ready / Indexed</span>
          </span>
        );
      case 'EMBEDDED':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/10">
            <CheckCircle size={12} />
            <span>Embedded</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/15">
            <AlertTriangle size={12} />
            <span>Failed</span>
          </span>
        );
      case 'INDEXING':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/15 animate-pulse">
            <Clock className="animate-spin" size={12} />
            <span>Indexing Collection</span>
          </span>
        );
      case 'EMBEDDING_GENERATION':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/15 animate-pulse">
            <Clock className="animate-spin" size={12} />
            <span>Generating Embeddings</span>
          </span>
        );
      case 'READY_FOR_EMBEDDINGS':
      case 'TEXT_EXTRACTED':
      case 'CHUNKED':
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/15 animate-pulse">
            <Clock className="animate-spin" size={12} />
            <span>Processing Splits</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-800 text-slate-400 border border-slate-700/60">
            <Clock size={12} />
            <span>Queued</span>
          </span>
        );
    }
  };

  const getEmbeddingsProgress = () => {
    if (!embStats || embStats.total_chunks === 0) return 0;
    return Math.round((embStats.embedded_chunks / embStats.total_chunks) * 100);
  };

  return (
    <div className="space-y-6 animate-fade-in font-sans">
      
      {/* Navigation Return Hook */}
      <div>
        <Link to="/dashboard" className="inline-flex items-center space-x-2 text-xs font-bold text-slate-500 hover:text-slate-300 transition-colors uppercase tracking-wider">
          <ArrowLeft size={14} />
          <span>Back to Workspace</span>
        </Link>
      </div>

      {/* Grid structure: Left Info Card & Right tabbed viewport */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Left Side: Notion Style property sheet */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-900 rounded-3xl p-6 space-y-6 shadow-sm">
            <div className="flex items-center space-x-3.5 pb-4 border-b border-slate-900/50">
              <div className="p-3 bg-indigo-500/10 rounded-2xl text-indigo-400">
                <FileText size={22} className="stroke-[2.5]" />
              </div>
              <div className="overflow-hidden">
                <h2 className="text-sm font-bold text-slate-100 truncate" title={doc.filename}>{doc.filename}</h2>
                <p className="text-[10px] text-slate-500 font-extrabold uppercase mt-0.5">Document ID: #{doc.id}</p>
              </div>
            </div>

            {/* Properties */}
            <div className="space-y-4 text-xs font-medium">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Processing Stage</span>
                {getStatusBadge(doc.status)}
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-slate-400">
                  <HardDrive size={14} />
                  <span>File Size</span>
                </div>
                <span className="text-slate-200 font-semibold">{doc.size}</span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-slate-400">
                  <Calendar size={14} />
                  <span>Index Date</span>
                </div>
                <span className="text-slate-200 font-semibold">
                  {new Date(doc.created_at).toLocaleDateString()}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-slate-400">
                  <Cpu size={14} />
                  <span>Page Count</span>
                </div>
                <span className="text-slate-200 font-semibold">{doc.page_count} pages</span>
              </div>

              {chunksData && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-slate-400">
                    <Layers size={14} />
                    <span>Chunks Created</span>
                  </div>
                  <span className="text-slate-200 font-semibold">{chunksData.total_chunks} blocks</span>
                </div>
              )}

              {doc.ocr_confidence !== null && doc.ocr_confidence !== undefined && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-slate-400">
                    <Sparkles size={14} />
                    <span>OCR Avg Acc</span>
                  </div>
                  <span className="text-indigo-400 font-bold">{(doc.ocr_confidence * 100).toFixed(1)}%</span>
                </div>
              )}
            </div>

            {/* Stage notification widgets */}
            {!['INDEXED', 'EMBEDDED', 'Completed', 'FAILED'].includes(doc.status) && (
              <div className="p-4 bg-indigo-500/5 border border-indigo-500/10 rounded-2xl flex items-start space-x-3">
                <Sparkles size={15} className="text-indigo-400 shrink-0 mt-0.5 animate-pulse" />
                <p className="text-[11px] text-indigo-300 leading-relaxed">
                  Platform is current generating semantic chunks and saving vector descriptors to Qdrant. Live updates will populate automatically.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Right Side: Preview Tabs */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-900 rounded-3xl p-5 flex flex-col h-[600px] shadow-sm">
            {/* Tab Nav Controls */}
            <div className="pb-3 border-b border-slate-900/50 flex items-center justify-between">
              <div className="flex space-x-6">
                {[
                  { id: 'text', label: 'Extracted Text' },
                  { id: 'chunks', label: 'Semantic Chunks' },
                  { id: 'embeddings', label: 'Embedding Vector' }
                ].map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setActiveTab(t.id)}
                    className={`pb-2 text-xs font-bold uppercase tracking-wider border-b-2 transition-all cursor-pointer ${
                      activeTab === t.id
                        ? 'border-indigo-500 text-indigo-400 font-extrabold'
                        : 'border-transparent text-slate-450 hover:text-slate-300'
                    }`}
                  >
                    {t.label}
                  </button>
                ))}
              </div>
              
              <span className="text-[10px] text-slate-500 font-bold uppercase">
                {activeTab === 'text' && '10k Chars preview'}
                {activeTab === 'chunks' && `${chunksData?.total_chunks || 0} items`}
                {activeTab === 'embeddings' && `model: all-MiniLM-L6-v2`}
              </span>
            </div>

            {/* Viewport content sheets */}
            <div className="flex-1 overflow-y-auto mt-4 hide-scrollbar">
              {activeTab === 'text' && (
                <div className="relative h-full flex flex-col">
                  {doc.extracted_text_preview ? (
                    <>
                      <div className="absolute right-3 top-3 z-10">
                        <button
                          onClick={handleCopyText}
                          className="p-2 bg-slate-900 hover:bg-slate-850 border border-slate-800 rounded-xl text-slate-400 hover:text-slate-200 transition-all cursor-pointer flex items-center space-x-1"
                          title="Copy text content"
                        >
                          {copied ? <Check size={14} className="text-emerald-400" /> : <Copy size={14} />}
                        </button>
                      </div>
                      <div className="flex-1 bg-slate-950/40 border border-slate-900 rounded-2xl p-5 font-mono text-xs leading-relaxed text-slate-300 whitespace-pre-wrap select-text overflow-y-auto">
                        {doc.extracted_text_preview}
                      </div>
                    </>
                  ) : (
                    <div className="flex-1 flex flex-col items-center justify-center py-20 text-slate-650 italic">
                      No extracted text content populated.
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'chunks' && (
                <div className="space-y-4">
                  {isLoadingChunks ? (
                    <div className="py-20 flex flex-col items-center justify-center space-y-3">
                      <Loader2 className="animate-spin text-indigo-500" size={24} />
                      <p className="text-xs text-slate-500 font-medium">Analyzing splits...</p>
                    </div>
                  ) : !chunksData || chunksData.chunks.length === 0 ? (
                    <div className="py-20 text-center border border-dashed border-slate-850 rounded-2xl bg-slate-950/20">
                      <Layers size={32} className="mx-auto text-slate-750 mb-3" />
                      <p className="text-xs font-bold text-slate-450">No chunks indexed</p>
                      <p className="text-[10px] text-slate-650 mt-1">Chunks generate automatically after text extraction is complete.</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* Metric cards */}
                      <div className="grid grid-cols-3 gap-4 bg-slate-950/30 border border-slate-900 p-4 rounded-2xl text-center">
                        <div className="space-y-1">
                          <p className="text-[9px] text-slate-500 font-bold uppercase tracking-wider">Pages</p>
                          <p className="text-md font-extrabold text-slate-200">{chunksData.page_count}</p>
                        </div>
                        <div className="space-y-1 border-x border-slate-850/65">
                          <p className="text-[9px] text-slate-500 font-bold uppercase tracking-wider">Total Chunks</p>
                          <p className="text-md font-extrabold text-slate-200">{chunksData.total_chunks}</p>
                        </div>
                        <div className="space-y-1">
                          <p className="text-[9px] text-slate-500 font-bold uppercase tracking-wider">Avg Length</p>
                          <p className="text-md font-extrabold text-indigo-400">{chunksData.average_chunk_size} char</p>
                        </div>
                      </div>

                      {/* Mapping scroll lists */}
                      <div className="space-y-3 pb-4">
                        {chunksData.chunks.map((chunk, index) => (
                          <div key={chunk.id || index} className="bg-slate-950/40 border border-slate-900/60 p-4.5 rounded-2xl space-y-2.5">
                            <div className="flex items-center justify-between text-[10px] font-bold text-indigo-450 uppercase">
                              <span className="flex items-center space-x-1.5">
                                <ListOrdered size={12} />
                                <span>Chunk #{index + 1}</span>
                              </span>
                              <span className="text-slate-550 flex space-x-2">
                                <span>Page {chunk.page_number}</span>
                                <span>•</span>
                                <span>{chunk.chunk_length} chars</span>
                              </span>
                            </div>
                            <div className="text-xs leading-relaxed text-slate-300 p-3 bg-slate-900/30 rounded-xl border border-slate-900/60 font-sans select-text whitespace-pre-wrap">
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
                <div className="space-y-6">
                  {isLoadingStats ? (
                    <div className="py-20 flex flex-col items-center justify-center space-y-3">
                      <Loader2 className="animate-spin text-indigo-500" size={24} />
                      <p className="text-xs text-slate-500 font-medium">Resolving dimensions...</p>
                    </div>
                  ) : !embStats ? (
                    <div className="py-20 text-center border border-dashed border-slate-850 rounded-2xl bg-slate-950/20">
                      <Binary size={32} className="mx-auto text-slate-750 mb-3" />
                      <p className="text-xs font-bold text-slate-450">Embedding stats missing</p>
                    </div>
                  ) : (
                    <div className="space-y-5">
                      <div className="grid grid-cols-2 gap-4">
                        <div className="bg-slate-950/30 border border-slate-900 p-4 rounded-xl">
                          <p className="text-[9px] text-slate-500 font-bold uppercase tracking-wider">Vector Space model</p>
                          <p className="text-xs font-bold text-slate-200 mt-1">{embStats.model_name}</p>
                        </div>
                        <div className="bg-slate-950/30 border border-slate-900 p-4 rounded-xl">
                          <p className="text-[9px] text-slate-500 font-bold uppercase tracking-wider">Dimensions</p>
                          <p className="text-xs font-bold text-indigo-400 mt-1">{embStats.vector_dimension} floats</p>
                        </div>
                      </div>

                      {/* Vector Progress panel */}
                      <div className="bg-slate-950/30 border border-slate-900 p-5 rounded-2xl space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="text-xs font-bold text-slate-200">Vector Ingestion Progress</h4>
                            <p className="text-[10px] text-slate-500 mt-0.5">Chunks pushed to Qdrant collections</p>
                          </div>
                          <span className="text-sm font-extrabold text-indigo-400">{getEmbeddingsProgress()}%</span>
                        </div>

                        <div className="w-full bg-slate-950 h-2 rounded-full overflow-hidden border border-slate-850">
                          <div 
                            className="bg-gradient-to-r from-indigo-500 to-cyan-500 h-full rounded-full transition-all duration-300"
                            style={{ width: `${getEmbeddingsProgress()}%` }}
                          ></div>
                        </div>

                        <div className="flex justify-between text-[10px] text-slate-500 font-medium">
                          <span>{embStats.embedded_chunks} chunks vectorized</span>
                          <span>{embStats.total_chunks} total</span>
                        </div>
                      </div>

                      {/* Info callout */}
                      <div className="p-4 bg-indigo-500/5 border border-indigo-500/10 rounded-2xl flex items-start space-x-3.5">
                        <Sparkles size={16} className="text-indigo-400 shrink-0 mt-0.5" />
                        <div>
                          <h4 className="text-xs font-bold text-indigo-300">Intelligent Semantic Indexing</h4>
                          <p className="text-[11px] text-indigo-300/80 mt-1 leading-relaxed">
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
