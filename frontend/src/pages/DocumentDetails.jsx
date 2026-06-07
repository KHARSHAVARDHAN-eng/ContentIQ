import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import { ArrowLeft, FileText, Calendar, HardDrive, Cpu, AlertTriangle, CheckCircle, Clock, Sparkles, Layers, ListOrdered, Binary, ShieldAlert } from 'lucide-react';

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
    if (!doc || doc.status === 'EMBEDDED' || doc.status === 'FAILED') return;

    const interval = setInterval(() => {
      fetchDetails();
      fetchChunks();
      fetchEmbeddingStats();
    }, 2000);

    return () => clearInterval(interval);
  }, [doc]);

  if (isLoading) {
    return (
      <div className="flex h-64 items-center justify-center text-slate-400">
        <div className="flex flex-col items-center space-y-3">
          <div className="h-10 w-10 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
          <p className="text-sm font-medium">Retrieving extraction data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-rose-500/10 border border-rose-500/20 rounded-2xl p-6 text-center max-w-xl mx-auto space-y-4">
        <AlertTriangle size={36} className="mx-auto text-rose-400" />
        <p className="text-rose-400 font-semibold">{error}</p>
        <Link to="/dashboard" className="inline-flex items-center space-x-2 text-sm text-indigo-400 hover:text-indigo-300">
          <ArrowLeft size={16} />
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
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle size={12} />
            <span>Ready / Indexed</span>
          </span>
        );
      case 'EMBEDDED':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle size={12} />
            <span>Embedded</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-rose-500/10 text-rose-400 border border-rose-500/20">
            <AlertTriangle size={12} />
            <span>Failed</span>
          </span>
        );
      case 'INDEXING':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 animate-pulse">
            <Clock className="animate-spin" size={12} />
            <span>Indexing Qdrant</span>
          </span>
        );
      case 'EMBEDDING_GENERATION':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20 animate-pulse">
            <Clock className="animate-spin" size={12} />
            <span>Vector Hashing</span>
          </span>
        );
      case 'READY_FOR_EMBEDDINGS':
      case 'TEXT_EXTRACTED':
      case 'CHUNKED':
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
            <Clock className="animate-spin" size={12} />
            <span>{status === 'READY_FOR_EMBEDDINGS' ? 'Embedding Queue' : status === 'CHUNKED' || status === 'TEXT_EXTRACTED' ? 'Chunking Text' : 'Extracting Text'}</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full text-xs font-semibold bg-slate-500/10 text-slate-400 border border-slate-500/20">
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
      {/* Header Back Button */}
      <div>
        <Link to="/dashboard" className="inline-flex items-center space-x-2 text-sm text-slate-400 hover:text-slate-200 transition-colors font-medium">
          <ArrowLeft size={16} />
          <span>Back to Workspace</span>
        </Link>
      </div>

      {/* Grid: Document Metadata & Preview Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Metadata Left Sidebar */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-6">
            <div className="flex items-center space-x-3.5 pb-4 border-b border-slate-800">
              <div className="p-3 bg-indigo-500/10 rounded-2xl text-indigo-400">
                <FileText size={24} />
              </div>
              <div className="overflow-hidden">
                <h3 className="font-bold text-slate-100 truncate max-w-[200px]" title={doc.filename}>{doc.filename}</h3>
                <p className="text-xs text-slate-500">ID: #{doc.id}</p>
              </div>
            </div>

            <div className="space-y-4 text-sm">
              <div className="flex items-center justify-between">
                <span className="text-slate-500">Status</span>
                {getStatusBadge(doc.status)}
              </div>
              
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-slate-400">
                  <HardDrive size={16} />
                  <span>Size</span>
                </div>
                <span className="font-semibold text-slate-200">{doc.size}</span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-slate-400">
                  <Calendar size={16} />
                  <span>Uploaded</span>
                </div>
                <span className="font-semibold text-slate-200">
                  {new Date(doc.created_at).toLocaleDateString()}
                </span>
              </div>

              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-2 text-slate-400">
                  <Cpu size={16} />
                  <span>Pages</span>
                </div>
                <span className="font-semibold text-slate-200">{doc.page_count}</span>
              </div>

              {chunksData && (
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-2 text-slate-400">
                    <Layers size={16} />
                    <span>Chunks</span>
                  </div>
                  <span className="font-semibold text-slate-200">{chunksData.total_chunks}</span>
                </div>
              )}
            </div>

            {/* Prompt for processing */}
            {doc.status !== 'EMBEDDED' && doc.status !== 'FAILED' && (
              <div className="p-4 bg-indigo-500/5 border border-indigo-500/10 rounded-2xl flex items-start space-x-2.5">
                <Sparkles size={16} className="text-indigo-400 shrink-0 mt-0.5 animate-pulse" />
                <p className="text-xs text-indigo-300/80 leading-relaxed">
                  DocumentIQ RAG pipelines are extracting text, creating semantic splits, and vectorizing layouts. Please wait.
                </p>
              </div>
            )}
          </div>
        </div>

        {/* Text Viewport Right Content */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 flex flex-col h-[600px]">
            {/* Tab navigation */}
            <div className="pb-2 border-b border-slate-800 mb-4 flex items-center justify-between">
              <div className="flex space-x-6">
                <button
                  onClick={() => setActiveTab('text')}
                  className={`pb-2.5 text-sm font-semibold border-b-2 transition-all cursor-pointer ${
                    activeTab === 'text'
                      ? 'border-indigo-500 text-indigo-400 font-bold'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Extracted Text
                </button>
                <button
                  onClick={() => setActiveTab('chunks')}
                  className={`pb-2.5 text-sm font-semibold border-b-2 transition-all cursor-pointer ${
                    activeTab === 'chunks'
                      ? 'border-indigo-500 text-indigo-400 font-bold'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  AI Chunks
                </button>
                <button
                  onClick={() => setActiveTab('embeddings')}
                  className={`pb-2.5 text-sm font-semibold border-b-2 transition-all cursor-pointer ${
                    activeTab === 'embeddings'
                      ? 'border-indigo-500 text-indigo-400 font-bold'
                      : 'border-transparent text-slate-400 hover:text-slate-200'
                  }`}
                >
                  Embeddings
                </button>
              </div>
              <span className="text-xs text-slate-500">
                {activeTab === 'text'
                  ? 'Preview max 10k chars'
                  : activeTab === 'chunks'
                  ? `${chunksData?.total_chunks || 0} chunks generated`
                  : `Model: ${embStats?.model_name || 'SentenceTransformer'}`}
              </span>
            </div>

            {/* Tab Contents */}
            <div className="flex-1 overflow-y-auto">
              {activeTab === 'text' ? (
                <div className="bg-slate-950/60 border border-slate-850 rounded-2xl p-5 font-mono text-sm leading-relaxed text-slate-300 h-full select-text whitespace-pre-wrap">
                  {doc.extracted_text_preview}
                </div>
              ) : activeTab === 'chunks' ? (
                /* Chunks Tab Content */
                <div className="space-y-6 h-full">
                  {isLoadingChunks ? (
                    <div className="py-20 flex flex-col items-center justify-center space-y-3 text-slate-500">
                      <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
                      <p className="text-xs">Computing semantic splits...</p>
                    </div>
                  ) : !chunksData || chunksData.chunks.length === 0 ? (
                    <div className="py-20 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-950/20">
                      <Layers size={40} className="mx-auto text-slate-700 mb-3 animate-pulse" />
                      <p className="text-sm font-medium text-slate-400">No chunks available yet</p>
                      <p className="text-xs text-slate-600 mt-1">Chunking runs automatically after text extraction completes.</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {/* Chunk statistics summary */}
                      <div className="grid grid-cols-3 gap-4 bg-slate-950/40 border border-slate-850 p-4 rounded-2xl">
                        <div className="text-center space-y-1">
                          <p className="text-xs text-slate-500 font-medium">Page Count</p>
                          <p className="text-lg font-bold text-slate-200">{chunksData.page_count}</p>
                        </div>
                        <div className="text-center border-x border-slate-800 space-y-1">
                          <p className="text-xs text-slate-500 font-medium">Total Chunks</p>
                          <p className="text-lg font-bold text-slate-200">{chunksData.total_chunks}</p>
                        </div>
                        <div className="text-center space-y-1">
                          <p className="text-xs text-slate-500 font-medium">Avg Chunk Size</p>
                          <p className="text-lg font-bold text-slate-200">{chunksData.average_chunk_size} ch</p>
                        </div>
                      </div>

                      {/* Chunk mapping lists */}
                      <div className="space-y-3">
                        {chunksData.chunks.map((chunk) => (
                          <div key={chunk.id} className="bg-slate-950/60 border border-slate-850 hover:border-slate-800/80 p-5 rounded-2xl space-y-3 transition-colors">
                            <div className="flex items-center justify-between text-xs font-semibold text-indigo-400/90 tracking-wide uppercase">
                              <span className="flex items-center space-x-1">
                                <ListOrdered size={12} />
                                <span>Chunk #{chunk.chunk_index + 1}</span>
                              </span>
                              <span className="flex items-center space-x-3 text-slate-500">
                                <span>Page {chunk.page_number}</span>
                                <span>•</span>
                                <span>{chunk.chunk_length} characters</span>
                              </span>
                            </div>
                            <div className="text-sm leading-relaxed text-slate-300 whitespace-pre-wrap select-text font-sans p-3 bg-slate-900/40 rounded-xl border border-slate-850/60">
                              {chunk.chunk_text}
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                /* Embeddings Tab Content */
                <div className="space-y-6 h-full">
                  {isLoadingStats ? (
                    <div className="py-20 flex flex-col items-center justify-center space-y-3 text-slate-500">
                      <div className="h-8 w-8 animate-spin rounded-full border-4 border-indigo-500 border-t-transparent"></div>
                      <p className="text-xs">Connecting embedding model...</p>
                    </div>
                  ) : !embStats ? (
                    <div className="py-20 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-950/20">
                      <Binary size={40} className="mx-auto text-slate-700 mb-3" />
                      <p className="text-sm font-medium text-slate-400">Embedding stats not available</p>
                    </div>
                  ) : (
                    <div className="space-y-6">
                      
                      {/* Embeddings Overview Grid Cards */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="bg-slate-950/40 border border-slate-850 p-5 rounded-2xl space-y-1">
                          <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Vector Model Name</p>
                          <p className="text-lg font-bold text-slate-200">{embStats.model_name}</p>
                        </div>
                        <div className="bg-slate-950/40 border border-slate-850 p-5 rounded-2xl space-y-1">
                          <p className="text-xs text-slate-500 font-semibold uppercase tracking-wider">Vector Dimensions</p>
                          <p className="text-lg font-bold text-indigo-400">{embStats.vector_dimension} float32</p>
                        </div>
                      </div>

                      {/* Progress bar visualizer */}
                      <div className="bg-slate-950/40 border border-slate-850 p-6 rounded-3xl space-y-4">
                        <div className="flex items-center justify-between">
                          <div>
                            <h4 className="font-bold text-slate-200">Embedding Progress</h4>
                            <p className="text-xs text-slate-500 mt-1">Chunk vectorization state</p>
                          </div>
                          <span className="text-lg font-extrabold text-slate-200">{getEmbeddingsProgress()}%</span>
                        </div>

                        {/* Outer Bar */}
                        <div className="w-full bg-slate-950 h-3 rounded-full overflow-hidden border border-slate-850">
                          <div 
                            className="bg-gradient-to-r from-indigo-500 to-cyan-500 h-full rounded-full transition-all duration-500"
                            style={{ width: `${getEmbeddingsProgress()}%` }}
                          ></div>
                        </div>

                        <div className="flex items-center justify-between text-xs text-slate-400 pt-1">
                          <span>{embStats.embedded_chunks} chunks vectorized</span>
                          <span>{embStats.total_chunks} total chunks</span>
                        </div>
                      </div>

                      {/* Model configuration note */}
                      <div className="p-5 bg-indigo-500/5 border border-indigo-500/10 rounded-2xl flex items-start space-x-3.5">
                        <Sparkles className="text-indigo-400 shrink-0 mt-0.5" size={18} />
                        <div className="space-y-1">
                          <h5 className="text-xs font-bold text-indigo-300">Intelligent Vectorization</h5>
                          <p className="text-xs text-indigo-300/80 leading-relaxed">
                            Every semantic text chunk was passed through the <strong>all-MiniLM-L6-v2</strong> sentence-transformer model. Vector float outputs are processed on CPU and stored in local volatile registries, while dimensions and mappings are recorded inside relational tables.
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
