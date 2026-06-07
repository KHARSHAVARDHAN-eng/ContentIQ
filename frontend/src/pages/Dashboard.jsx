import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { FileUp, Search, FileText, CheckCircle2, AlertCircle, Loader2, Sparkles, Database, TrendingUp, Zap } from 'lucide-react';

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
  useEffect(() => {
    const fetchDocuments = async () => {
      try {
        const response = await axios.get(`${API_URL}/documents`);
        setDocuments(response.data);
      } catch (err) {
        console.error("Failed to load documents:", err);
      } finally {
        setIsLoadingDocs(false);
      }
    };
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
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Failed to upload document.';
      setUploadError(errMsg);
      console.error("Upload error:", err);
    } finally {
      setIsUploading(false);
    }
  };

  // Filter documents by search query
  const filteredDocuments = documents.filter(doc => 
    doc.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Calculate dynamic stats based on actual data
  const totalDocs = documents.length;
  const completedDocs = documents.filter(d => d.status === 'READY_FOR_EMBEDDINGS').length;
  const failedDocs = documents.filter(d => d.status === 'FAILED').length;

  return (
    <div className="space-y-8 animate-fade-in">
      {/* Welcome banner */}
      <div className="flex flex-col md:flex-row md:items-center md:justify-between bg-slate-900 border border-slate-800 rounded-3xl p-6 md:p-8 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-80 h-full bg-gradient-to-l from-indigo-500/10 to-transparent pointer-events-none"></div>
        <div className="space-y-2 relative z-10">
          <div className="flex items-center space-x-2 text-indigo-400 font-semibold text-sm">
            <Sparkles size={16} />
            <span>AI intelligence active</span>
          </div>
          <h2 className="text-3xl font-extrabold text-white">Hello, {user?.email?.split('@')[0]}</h2>
          <p className="text-slate-400 max-w-xl">
            Upload document files and get instant AI-extracted summaries, entity recognitions, and sentiment scores.
          </p>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-5">
        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Total Documents</p>
            <p className="text-2xl font-bold text-slate-200">{totalDocs}</p>
          </div>
          <div className="p-3 bg-indigo-500/10 rounded-xl text-indigo-400">
            <FileText size={20} />
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Completed</p>
            <p className="text-2xl font-bold text-emerald-400">{completedDocs}</p>
          </div>
          <div className="p-3 bg-emerald-500/10 rounded-xl text-emerald-400">
            <CheckCircle2 size={20} />
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Failed</p>
            <p className="text-2xl font-bold text-rose-400">{failedDocs}</p>
          </div>
          <div className="p-3 bg-rose-500/10 rounded-xl text-rose-400">
            <AlertCircle size={20} />
          </div>
        </div>

        <div className="bg-slate-900 border border-slate-800 p-5 rounded-2xl flex items-center justify-between">
          <div className="space-y-1">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider">System State</p>
            <p className="text-2xl font-bold text-cyan-400">Online</p>
          </div>
          <div className="p-3 bg-cyan-500/10 rounded-xl text-cyan-400">
            <Database size={20} />
          </div>
        </div>
      </div>

      {/* Main Dashboard Section */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        {/* Upload Column */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6 space-y-6">
            <div>
              <h3 className="text-lg font-bold text-slate-200">Analyze Document</h3>
              <p className="text-xs text-slate-500 mt-1">Upload PDF, DOCX, or TXT format</p>
            </div>

            <div className="relative border-2 border-dashed border-slate-850 hover:border-indigo-500/50 rounded-2xl p-8 transition-colors flex flex-col items-center justify-center text-center cursor-pointer group bg-slate-950/40">
              <input
                type="file"
                disabled={isUploading}
                onChange={handleUpload}
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                accept=".pdf,.docx,.txt"
              />
              {isUploading ? (
                <div className="space-y-3 flex flex-col items-center">
                  <Loader2 className="animate-spin text-indigo-500" size={32} />
                  <p className="text-sm font-medium text-slate-300">Uploading file...</p>
                  <p className="text-xs text-slate-500 animate-pulse">Running NLP pipelines</p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="mx-auto w-12 h-12 rounded-xl bg-indigo-600/10 flex items-center justify-center text-indigo-400 group-hover:scale-110 transition-transform">
                    <FileUp size={24} />
                  </div>
                  <div>
                    <p className="text-sm font-semibold text-slate-300">Choose file to process</p>
                    <p className="text-xs text-slate-600 mt-1">Drag and drop or click here</p>
                  </div>
                </div>
              )}
            </div>

            {uploadSuccess && (
              <div className="flex items-start space-x-3 p-4 bg-emerald-500/5 border border-emerald-500/10 rounded-2xl">
                <CheckCircle2 className="text-emerald-500 shrink-0 mt-0.5" size={18} />
                <div className="overflow-hidden">
                  <p className="text-sm font-semibold text-emerald-400">Success!</p>
                  <p className="text-xs text-slate-400 mt-0.5 truncate max-w-[200px]">{uploadedFileName} uploaded & analyzed.</p>
                </div>
              </div>
            )}

            {uploadError && (
              <div className="flex items-start space-x-3 p-4 bg-rose-500/5 border border-rose-500/10 rounded-2xl">
                <AlertCircle className="text-rose-500 shrink-0 mt-0.5" size={18} />
                <div>
                  <p className="text-sm font-semibold text-rose-400">Upload Failed</p>
                  <p className="text-xs text-slate-400 mt-0.5">{uploadError}</p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Documents Table */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-900 border border-slate-800 rounded-3xl p-6">
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-lg font-bold text-slate-200">Recent Documents</h3>
                <p className="text-xs text-slate-500 mt-1">Status of analyzed files</p>
              </div>
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-600" size={16} />
                <input
                  type="text"
                  placeholder="Search files..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="bg-slate-950 pl-9 pr-4 py-1.5 border border-slate-850 rounded-xl text-xs text-slate-300 placeholder-slate-600 focus:outline-none focus:border-indigo-500/50"
                />
              </div>
            </div>

            {isLoadingDocs ? (
              <div className="py-20 flex flex-col items-center justify-center space-y-4">
                <Loader2 className="animate-spin text-indigo-500" size={32} />
                <p className="text-xs text-slate-500">Retrieving document records...</p>
              </div>
            ) : filteredDocuments.length === 0 ? (
              <div className="py-20 text-center border border-dashed border-slate-800 rounded-2xl bg-slate-950/20">
                <FileText size={40} className="mx-auto text-slate-700 mb-3" />
                <p className="text-sm font-medium text-slate-400">No documents found</p>
                <p className="text-xs text-slate-600 mt-1">Upload a document to run AI parsing and extraction</p>
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left border-collapse">
                  <thead>
                    <tr className="border-b border-slate-800 text-slate-500 text-xs font-semibold uppercase tracking-wider">
                      <th className="pb-3 pl-2">Name</th>
                      <th className="pb-3">Size</th>
                      <th className="pb-3">Uploaded</th>
                      <th className="pb-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60 text-sm">
                    {filteredDocuments.map((doc) => (
                      <tr key={doc.id} className="hover:bg-slate-850/40 transition-colors group">
                        <td className="py-3.5 pl-2 font-medium text-slate-300 flex items-center space-x-3">
                          <FileText size={16} className="text-indigo-400" />
                          <Link to={`/documents/${doc.id}`} className="hover:text-indigo-400 transition-colors truncate max-w-[220px] cursor-pointer">
                            {doc.name}
                          </Link>
                        </td>
                        <td className="py-3.5 text-slate-400 text-xs">{doc.size}</td>
                        <td className="py-3.5 text-slate-400 text-xs">
                          {new Date(doc.created_at).toLocaleDateString()}
                        </td>
                        <td className="py-3.5">
                          {(doc.status === "READY_FOR_EMBEDDINGS" || doc.status === "EMBEDDED" || doc.status === "INDEXED" || doc.status === "Completed") && (
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                              <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full animate-pulse"></span>
                              <span>Completed</span>
                            </span>
                          )}
                          {doc.status === "FAILED" && (
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-rose-500/10 text-rose-400 border border-rose-500/20">
                              <AlertCircle size={10} />
                              <span>Failed</span>
                            </span>
                          )}
                          {(doc.status === "PROCESSING" || doc.status === "TEXT_EXTRACTED" || doc.status === "CHUNKED" || doc.status === "EMBEDDING_GENERATION" || doc.status === "INDEXING") && (
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
                              <Loader2 size={10} className="animate-spin" />
                              <span>Processing</span>
                            </span>
                          )}
                          {doc.status === "UPLOADED" && (
                            <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-xs font-medium bg-slate-500/10 text-slate-400 border border-slate-500/20">
                              <span>Queued</span>
                            </span>
                          )}

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
