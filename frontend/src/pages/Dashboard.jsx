import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { FileUp, Search, FileText, CheckCircle2, AlertCircle, Loader2, Sparkles, Eye, Trash2 } from 'lucide-react';
import { motion } from 'framer-motion';
import DocumentDrawer from '../components/DocumentDrawer';

import { API_URL } from '../config';

const Dashboard = () => {
  const { user } = useAuth();
  const [isUploading, setIsUploading] = useState(false);
  const [uploadSuccess, setUploadSuccess] = useState(false);
  const [uploadedFileName, setUploadedFileName] = useState('');
  const [uploadError, setUploadError] = useState('');
  
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [previewDocumentId, setPreviewDocumentId] = useState(null);

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
      const token = localStorage.getItem('token');
      const response = await axios.post(`${API_URL}/documents/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      setUploadSuccess(true);
      setDocuments(prev => [response.data, ...prev]);
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

  const handleDeleteDocument = async (docId, docName) => {
    if (!window.confirm(`Are you sure you want to delete "${docName}" from your workspace?`)) return;
    try {
      await axios.delete(`${API_URL}/documents/${docId}`);
      setDocuments(prev => prev.filter(d => d.id !== docId));
    } catch (err) {
      console.error("Failed to delete document:", err);
      alert(err.response?.data?.detail || "Failed to delete document.");
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

  const filteredDocuments = documents.filter(doc => 
    doc.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const totalDocs = documents.length;
  const readyDocs = documents.filter(d => ['INDEXED', 'EMBEDDED', 'Completed'].includes(d.status)).length;
  const processingDocs = documents.filter(d => !['INDEXED', 'EMBEDDED', 'Completed', 'FAILED'].includes(d.status)).length;
  const failedDocs = documents.filter(d => d.status === 'FAILED').length;

  const getStatusBadge = (status) => {
    switch (status) {
      case 'INDEXED':
      case 'Completed':
      case 'EMBEDDED':
        return (
          <span className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-100">
            <span className="w-1 h-1 bg-emerald-500 rounded-full"></span>
            <span>Indexed</span>
          </span>
        );
      case 'FAILED':
        return (
          <span className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-rose-50 text-rose-700 border border-rose-100">
            <span>Failed</span>
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center space-x-1.5 px-2 py-0.5 rounded-full text-[10px] font-semibold bg-amber-50 text-amber-700 border border-amber-100 animate-pulse">
            <Loader2 size={10} className="animate-spin text-amber-655 shrink-0" />
            <span className="truncate">Parsing...</span>
          </span>
        );
    }
  };

  const containerVariants = {
    hidden: { opacity: 0 },
    show: {
      opacity: 1,
      transition: {
        staggerChildren: 0.03
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 5 },
    show: { opacity: 1, y: 0, transition: { type: 'spring', stiffness: 260, damping: 24 } }
  };

  return (
    <div className="space-y-6 font-sans">
      
      {/* Welcome & Overview Header */}
      <div className="border border-[#E5DDD0] bg-[#FCFAF6] rounded-2xl p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 shadow-sm">
        <div className="space-y-1">
          <div className="inline-flex items-center space-x-1.5 bg-[#F8F4EC] border border-[#E5DDD0] text-zinc-650 font-bold px-3 py-1 rounded-full text-[9px] uppercase tracking-wider">
            <Sparkles size={10} className="text-[#10b981]" />
            <span>RAG Ingestion Workspace</span>
          </div>
          <h2 className="text-lg font-bold text-[#111111] tracking-tight">
            Welcome, {user?.email?.split('@')[0]}
          </h2>
          <p className="text-zinc-550 text-xs max-w-2xl leading-relaxed">
            Manage your index repository. Add documents, parse content, review semantic chunks, and inspect Qdrant vectors.
          </p>
        </div>
      </div>

      {/* Metrics Dashboard Cards */}
      <motion.div 
        variants={containerVariants}
        initial="hidden"
        animate="show"
        className="grid grid-cols-2 md:grid-cols-4 gap-4"
      >
        {[
          { label: 'Total Index', value: totalDocs, icon: FileText, color: 'text-zinc-850', bg: 'bg-zinc-100 border-zinc-200' },
          { label: 'Ready / Chunks', value: readyDocs, icon: CheckCircle2, color: 'text-emerald-700', bg: 'bg-emerald-50 border-emerald-100' },
          { label: 'Ingesting', value: processingDocs, icon: Loader2, color: 'text-amber-700', bg: 'bg-amber-50 border-amber-100', spin: processingDocs > 0 },
          { label: 'Failures', value: failedDocs, icon: AlertCircle, color: 'text-rose-700', bg: 'bg-rose-50 border-rose-100' }
        ].map((stat, i) => (
          <motion.div 
            key={i} 
            variants={itemVariants}
            className="border border-[#E5DDD0] rounded-2xl p-4 flex items-center justify-between bg-[#FCFAF6] shadow-sm hover:shadow-md transition-all duration-200 card-hover-effect"
          >
            <div className="space-y-1">
              <span className="text-[9px] font-bold text-zinc-400 uppercase tracking-wider">{stat.label}</span>
              <p className={`text-lg font-bold ${stat.color}`}>{stat.value}</p>
            </div>
            <div className="p-1.5 bg-[#F8F4EC] border border-[#E5DDD0] rounded-lg text-zinc-550">
              <stat.icon size={14} className={stat.spin ? 'animate-spin' : ''} />
            </div>
          </motion.div>
        ))}
      </motion.div>

      {/* Workspace columns */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* Upload widget column */}
        <div className="lg:col-span-1">
          <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-5 space-y-4 shadow-sm">
            <div>
              <h3 className="text-[10px] font-bold text-[#111111] uppercase tracking-wider">Analyze Document</h3>
              <p className="text-[10.5px] text-zinc-550 mt-1 leading-relaxed">
                Choose PDF, DOCX, TXT, PNG, or JPG. Files are automatically chunked and vectorized.
              </p>
            </div>

            {/* Ingestion Drop widget */}
            <div className="relative border border-dashed border-[#E5DDD0] hover:border-zinc-400 rounded-xl p-6 transition-all duration-300 flex flex-col items-center justify-center text-center cursor-pointer group bg-[#FCFAF6]/60">
              <input
                id="workspace-file-uploader"
                type="file"
                disabled={isUploading}
                onChange={handleUpload}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                accept=".pdf,.docx,.txt,.jpg,.jpeg,.png"
              />
              {isUploading ? (
                <div className="space-y-2 flex flex-col items-center">
                  <Loader2 className="animate-spin text-zinc-650" size={20} />
                  <p className="text-[10.5px] font-bold text-zinc-800">Uploading document...</p>
                  <p className="text-[9px] text-zinc-400 animate-pulse">Running Ingestion Pipeline</p>
                </div>
              ) : (
                <div className="space-y-2">
                  <div className="mx-auto w-8 h-8 rounded-lg bg-[#F8F4EC] border border-[#E5DDD0] flex items-center justify-center text-zinc-600 group-hover:scale-[1.02] transition-transform">
                    <FileUp size={14} />
                  </div>
                  <div>
                    <p className="text-[10.5px] font-bold text-[#111111]">Choose document file</p>
                    <p className="text-[9px] text-zinc-400 mt-0.5">Drag source here or click</p>
                  </div>
                </div>
              )}
            </div>

            {uploadSuccess && (
              <div className="flex items-start space-x-2.5 p-3 bg-emerald-50/60 border border-emerald-200 rounded-xl animate-fade-in">
                <CheckCircle2 className="text-emerald-700 shrink-0 mt-0.5" size={13} />
                <div className="overflow-hidden">
                  <p className="text-[10px] font-bold text-emerald-800">Success</p>
                  <p className="text-[9px] text-emerald-750 mt-0.5 truncate">{uploadedFileName}</p>
                </div>
              </div>
            )}

            {uploadError && (
              <div className="flex items-start space-x-2.5 p-3 bg-rose-50/60 border border-rose-200 rounded-xl animate-fade-in">
                <AlertCircle className="text-rose-700 shrink-0 mt-0.5" size={13} />
                <div className="overflow-hidden">
                  <p className="text-[10px] font-bold text-rose-800">Upload Failed</p>
                  <p className="text-[9px] text-rose-750 mt-0.5 leading-relaxed">{uploadError}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Documents table list */}
        <div className="lg:col-span-2">
          <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-5 shadow-sm space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
              <div>
                <h3 className="text-[10px] font-bold text-[#111111] uppercase tracking-wider">Indexed Documents</h3>
                <p className="text-[10.5px] text-[#666666] mt-0.5">Index registry logs</p>
              </div>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" size={12} />
                <input
                  id="dashboard-search-registry"
                  type="text"
                  placeholder="Search index database..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-[#F8F4EC]/60 pl-8.5 pr-4 py-1.5 border border-[#E5DDD0] rounded-xl text-[10.5px] text-[#111111] placeholder-zinc-400 focus:outline-none focus:border-zinc-400 focus:bg-white w-full sm:w-48 transition-colors"
                />
              </div>
            </div>

            {isLoadingDocs ? (
              <div className="py-16 flex flex-col items-center justify-center space-y-3">
                <Loader2 className="animate-spin text-zinc-450" size={20} />
                <p className="text-[10px] text-zinc-450 font-bold uppercase tracking-widest animate-pulse">Loading list...</p>
              </div>
            ) : filteredDocuments.length === 0 ? (
              <div className="py-16 text-center border border-dashed border-[#E5DDD0] rounded-xl bg-[#FCFAF6]/60">
                <FileText size={28} className="mx-auto text-zinc-300 mb-2" />
                <p className="text-xs font-bold text-zinc-500">No documents found</p>
                <p className="text-[9.5px] text-zinc-400 mt-0.5">Ingest new files to add context details.</p>
              </div>
            ) : (
              <div className="overflow-x-auto hide-scrollbar">
                <table className="w-full text-left border-collapse select-text">
                  <thead>
                    <tr className="border-b border-[#E5DDD0]/80 text-[#666666] text-[9px] font-bold uppercase tracking-wider">
                      <th className="pb-2 pl-1">Document Name</th>
                      <th className="pb-2 px-3">Size</th>
                      <th className="pb-2 px-3 hidden sm:table-cell">OCR Acc</th>
                      <th className="pb-2 px-3">Status</th>
                      <th className="pb-2 text-right pr-1">Preview</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E5DDD0]/60 text-xs">
                    {filteredDocuments.map((doc) => (
                      <tr key={doc.id} className="hover:bg-[#F8F4EC]/40 transition-colors group">
                        <td className="py-2.5 pl-1 font-semibold text-[#111111] max-w-[150px] sm:max-w-[200px]">
                          <div className="flex items-center space-x-2">
                            <FileText size={13} className="text-zinc-450 shrink-0" />
                            <span className="truncate block" title={doc.name}>
                              {doc.name}
                            </span>
                          </div>
                        </td>
                        <td className="py-2.5 px-3 text-[#666666] font-medium">{doc.size}</td>
                        <td className="py-2.5 px-3 hidden sm:table-cell font-mono text-[10px]">
                          {doc.ocr_confidence !== null && doc.ocr_confidence !== undefined ? (
                            <span className="text-[#111111] font-bold">{(doc.ocr_confidence * 100).toFixed(0)}%</span>
                          ) : (
                            <span className="text-zinc-400 italic">N/A</span>
                          )}
                        </td>
                        <td className="py-2.5 px-3">{getStatusBadge(doc.status)}</td>
                        <td className="py-2.5 text-right pr-1 flex items-center justify-end space-x-1.5">
                          <button 
                            onClick={() => setPreviewDocumentId(doc.id)}
                            className="inline-flex items-center justify-center p-1.5 bg-[#FCFAF6] border border-[#E5DDD0] hover:border-zinc-400 rounded-lg text-zinc-650 hover:text-[#111111] transition-all cursor-pointer btn-press-active shadow-sm"
                            title="Inspect extraction splits"
                          >
                            <Eye size={11} />
                          </button>
                          <button 
                            onClick={() => handleDeleteDocument(doc.id, doc.name)}
                            className="inline-flex items-center justify-center p-1.5 bg-[#FCFAF6] border border-[#E5DDD0] hover:bg-rose-50 hover:border-rose-300 rounded-lg text-zinc-500 hover:text-rose-600 transition-all cursor-pointer btn-press-active shadow-sm"
                            title="Delete document"
                          >
                            <Trash2 size={11} />
                          </button>
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

      {/* Slide-over document viewer */}
      <DocumentDrawer 
        documentId={previewDocumentId} 
        onClose={() => setPreviewDocumentId(null)} 
      />

    </div>
  );
};

export default Dashboard;
