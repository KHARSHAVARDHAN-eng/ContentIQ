import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { FileUp, Search, FileText, CheckCircle2, AlertCircle, Loader2, Sparkles, Database, ArrowRight, Eye, ShieldAlert, Binary } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const Dashboard = () => {
  const { user } = useAuth();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [uploadError, setUploadError] = useState('');
  
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  // Fetch documents on mount
  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API_URL}/documents`);
      setDocuments(response.data || []);
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading(true);
    setUploadSuccess(false);
    setUploadError('');
    setUploadedFileName(file.name);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await axios.post(`${API_URL}/documents/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data'
        }
      });
      setUploadSuccess(true);
      // Prepend newly created document record
      setDocuments(prev => [response.data, ...prev]);
      // Refetch after 1 second to update ingestion state
      setTimeout(() => {
        fetchDocuments();
      }, 1000);
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Failed to upload document.';
      setUploadError(errMsg);
      console.error("Upload error:", err);
    } finally {
      setIsUploading(false);
    }
  };

  // Poll for processing documents
  useEffect(() => {
    const activeProcessing = documents.some(d => 
      !['INDEXED', 'EMBEDDED', 'FAILED', 'Completed'].includes(d.status)
    );
    if (!activeProcessing) return;

    const timer = setInterval(() => {
      fetchDocuments();
    }, 3000);
    return () => clearInterval(timer);
  }, [documents]);

  // Filter documents by search query
  const filteredDocuments = documents.filter(doc => 
    doc.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Calculate dynamic stats
  const totalDocs = documents.length;
  const readyDocs = documents.filter(d => ['INDEXED', 'EMBEDDED', 'Completed'].includes(d.status)).length;
  const failedDocs = documents.filter(d => d.status === 'FAILED').length;
  const processingDocs = totalDocs - readyDocs - failedDocs;

  const getStatusBadge = (status) => {
    switch (status) {
      case 'INDEXED':
      case 'Completed':
      case 'EMBEDDED':
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/10">
            <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></span>
            <span>Indexed</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-rose-500/10 text-rose-450 border border-rose-500/15">
            <AlertCircle size={10} />
            <span>Failed</span>
          </span>
        );
      case 'OCR_PENDING':
      case 'OCR_PROCESSING':
      case 'OCR_COMPLETED':
      case 'TEXT_EXTRACTED':
      case 'CHUNKED':
      case 'EMBEDDING_GENERATION':
      case 'INDEXING':
      case 'PROCESSING':
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/15 animate-pulse">
            <Loader2 size={10} className="animate-spin" />
            <span>Parsing ({status.replace('_', ' ')})</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-[10px] font-bold bg-slate-800 text-slate-400 border border-slate-700/60">
            <span>Queued</span>
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 animate-fade-in font-sans">
      
      {/* Welcome Banner Card */}
      <div className="relative overflow-hidden bg-slate-900 border border-slate-900/60 rounded-3xl p-6 md:p-8 flex flex-col md:flex-row md:items-center md:justify-between gap-6 shadow-xl">
        <div className="absolute top-0 right-0 w-[40%] h-full bg-gradient-to-l from-indigo-500/5 via-cyan-500/0 to-transparent pointer-events-none"></div>
        <div className="space-y-2 relative z-10">
          <div className="inline-flex items-center space-x-2 bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 font-semibold px-3 py-1 rounded-full text-xs">
            <Sparkles size={12} className="animate-pulse" />
            <span>NLP Extraction Active</span>
          </div>
          <h2 className="text-2xl md:text-3xl font-extrabold text-slate-100 tracking-tight">
            Hello, <span className="bg-gradient-to-r from-indigo-400 to-cyan-300 bg-clip-text text-transparent">{user?.email?.split('@')[0]}</span>
          </h2>
          <p className="text-slate-400 text-sm max-w-xl leading-relaxed">
            Manage your index workspace. Upload PDF, DOCX, or scan images to run OCR, generate vector embeddings, and search document semantics.
          </p>
        </div>
        
        {/* Quick action or logo reflection */}
        <div className="hidden lg:block relative z-10 bg-slate-950/40 p-4 border border-slate-900 rounded-2xl">
          <Database size={36} className="text-indigo-500/65" />
        </div>
      </div>

      {/* Stats Counter Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {[
          { label: 'Total Index', value: totalDocs, color: 'text-slate-100', icon: FileText, bg: 'bg-indigo-500/10 text-indigo-400' },
          { label: 'Ready / Chunks', value: readyDocs, color: 'text-emerald-400', icon: CheckCircle2, bg: 'bg-emerald-500/10 text-emerald-400' },
          { label: 'Ingesting', value: processingDocs, color: 'text-amber-400', icon: Loader2, bg: 'bg-amber-500/10 text-amber-400', spin: processingDocs > 0 },
          { label: 'Failures', value: failedDocs, color: 'text-rose-450', icon: AlertCircle, bg: 'bg-rose-500/10 text-rose-450' }
        ].map((stat, i) => (
          <div key={i} className="bg-slate-900/60 backdrop-blur-md border border-slate-900 rounded-2xl p-4 flex items-center justify-between shadow-sm">
            <div className="space-y-1">
              <span className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">{stat.label}</span>
              <p className={`text-xl font-bold ${stat.color}`}>{stat.value}</p>
            </div>
            <div className={`p-2.5 rounded-xl ${stat.bg}`}>
              <stat.icon size={18} className={stat.spin ? 'animate-spin' : ''} />
            </div>
          </div>
        ))}
      </div>

      {/* Workspace split panels */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Upload Action Column */}
        <div className="lg:col-span-1 space-y-4">
          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-900 rounded-3xl p-5 space-y-5 shadow-sm">
            <div>
              <h3 className="text-sm font-bold text-slate-200">Analyze Document</h3>
              <p className="text-[11px] text-slate-500 mt-1 leading-relaxed">Supported formats: PDF, DOCX, TXT, JPG, PNG. Scanned documents will invoke EasyOCR automatically.</p>
            </div>

            {/* Drag & Drop widget */}
            <div className="relative border border-dashed border-slate-800 hover:border-indigo-500/50 rounded-2xl p-6 transition-all duration-300 flex flex-col items-center justify-center text-center cursor-pointer group bg-slate-950/20">
              <input
                id="doc-file-upload-input"
                type="file"
                disabled={isUploading}
                onChange={handleUpload}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                accept=".pdf,.docx,.txt,.jpg,.jpeg,.png"
              />
              {isUploading ? (
                <div className="space-y-3 flex flex-col items-center">
                  <Loader2 className="animate-spin text-indigo-500" size={28} />
                  <p className="text-xs font-semibold text-slate-300">Sending to backend...</p>
                  <p className="text-[10px] text-slate-500 animate-pulse">Running Ingestion Pipeline</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="mx-auto w-10 h-10 rounded-xl bg-indigo-500/10 flex items-center justify-center text-indigo-400 group-hover:scale-105 transition-transform">
                    <FileUp size={20} />
                  </div>
                  <div>
                    <p className="text-xs font-bold text-slate-300">Choose document source</p>
                    <p className="text-[10px] text-slate-500 mt-1">Drag file here or click</p>
                  </div>
                </div>
              )}
            </div>

            {uploadSuccess && (
              <div className="flex items-start space-x-3 p-3 bg-emerald-500/5 border border-emerald-500/15 rounded-xl animate-fade-in">
                <CheckCircle2 className="text-emerald-400 shrink-0 mt-0.5" size={16} />
                <div className="overflow-hidden">
                  <p className="text-xs font-bold text-emerald-400">Upload Success</p>
                  <p className="text-[10px] text-slate-400 mt-0.5 truncate">{uploadedFileName}</p>
                </div>
              </div>
            )}

            {uploadError && (
              <div className="flex items-start space-x-3 p-3 bg-rose-500/5 border border-rose-500/15 rounded-xl animate-fade-in">
                <AlertCircle className="text-rose-400 shrink-0 mt-0.5" size={16} />
                <div>
                  <p className="text-xs font-bold text-rose-450">Ingestion Error</p>
                  <p className="text-[10px] text-slate-400 mt-0.5 leading-relaxed">{uploadError}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Documents Table List Column */}
        <div className="lg:col-span-2 space-y-4">
          <div className="bg-slate-900/60 backdrop-blur-md border border-slate-900 rounded-3xl p-5 shadow-sm">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-4">
              <div>
                <h3 className="text-sm font-bold text-slate-200">Workspace Documents</h3>
                <p className="text-[11px] text-slate-500 mt-1">Audit list of indexed vector chunks</p>
              </div>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" size={14} />
                <input
                  id="dashboard-search-files"
                  type="text"
                  placeholder="Search index database..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-slate-950 pl-9 pr-4 py-1.5 border border-slate-800 rounded-xl text-[11px] text-slate-300 placeholder-slate-650 focus:outline-none focus:border-indigo-500/50 w-full sm:w-56 transition-colors"
                />
              </div>
            </div>

            {isLoadingDocs ? (
              <div className="py-16 flex flex-col items-center justify-center space-y-3">
                <Loader2 className="animate-spin text-indigo-500" size={24} />
                <p className="text-xs text-slate-500 font-medium">Loading document registries...</p>
              </div>
            ) : filteredDocuments.length === 0 ? (
              <div className="py-16 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-950/20">
                <FileText size={36} className="mx-auto text-slate-700 mb-3" />
                <p className="text-xs font-bold text-slate-400">No documents indexed in this query</p>
                <p className="text-[10px] text-slate-600 mt-1 max-w-[280px] mx-auto leading-relaxed">
                  Start by dragging a file onto the analyst widget to process embeddings.
                </p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse select-text">
                  <thead>
                    <tr className="border-b border-slate-800/80 text-slate-500 text-[10px] font-bold uppercase tracking-wider">
                      <th className="pb-3 pl-1">Document Registry</th>
                      <th className="pb-3 px-3">Size</th>
                      <th className="pb-3 px-3 hidden sm:table-cell">OCR Acc</th>
                      <th className="pb-3 px-3">Status</th>
                      <th className="pb-3 text-right pr-1">Action</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-900/60 text-xs">
                    {filteredDocuments.map((doc) => (
                      <tr key={doc.id} className="hover:bg-slate-950/45 transition-colors group">
                        {/* Title details */}
                        <td className="py-3.5 pl-1 font-semibold text-slate-300 max-w-[180px] sm:max-w-[240px]">
                          <div className="flex items-center space-x-2.5">
                            <FileText size={14} className="text-indigo-400 shrink-0" />
                            <span className="truncate block" title={doc.name}>
                              {doc.name}
                            </span>
                          </div>
                        </td>
                        
                        {/* Size */}
                        <td className="py-3.5 px-3 text-slate-450 font-medium">{doc.size}</td>
                        
                        {/* OCR Confidence score */}
                        <td className="py-3.5 px-3 hidden sm:table-cell font-mono">
                          {doc.ocr_confidence !== null && doc.ocr_confidence !== undefined ? (
                            <span className="text-indigo-400 font-semibold">{(doc.ocr_confidence * 100).toFixed(0)}%</span>
                          ) : (
                            <span className="text-slate-600 italic">N/A</span>
                          )}
                        </td>
                        
                        {/* Status badge */}
                        <td className="py-3.5 px-3">
                          {getStatusBadge(doc.status)}
                        </td>

                        {/* Navigation link action */}
                        <td className="py-3.5 text-right pr-1">
                          <Link 
                            to={`/documents/${doc.id}`}
                            className="inline-flex items-center justify-center p-1.5 bg-slate-950 border border-slate-850 hover:border-indigo-500/30 hover:bg-indigo-500/10 rounded-lg text-slate-450 hover:text-indigo-400 transition-all cursor-pointer"
                            title="Inspect extraction splits"
                          >
                            <Eye size={12} />
                          </Link>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
};

export default Dashboard;
