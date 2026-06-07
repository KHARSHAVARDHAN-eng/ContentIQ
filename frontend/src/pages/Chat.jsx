import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Brain, FileText, CornerDownRight, ListOrdered, CheckCircle2, Loader2, Sparkles, HelpCircle, ShieldAlert } from 'lucide-react';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const Chat = () => {
  const [documents, setDocuments] = useState([]);
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      sender: 'bot',
      text: 'Hello! I am your DocumentIQ Assistant. Ask me anything about your uploaded documents, and I will answer with citations grounded in the source text.',
      citations: []
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState('');
  const [activeMessageId, setActiveMessageId] = useState('welcome');

  const messagesEndRef = useRef(null);

  const fetchDocuments = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/documents/`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setDocuments(response.data || []);
    } catch (err) {
      console.error("Failed to load documents:", err);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async (e) => {
    e.preventDefault();
    const cleanInput = input.trim();
    if (!cleanInput || isLoading) return;

    const userMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: cleanInput,
      citations: []
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);
    setError('');

    try {
      const token = localStorage.getItem('token');
      const response = await axios.post(
        `${API_URL}/chat`,
        { question: cleanInput },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const botMessage = {
        id: `bot-${Date.now()}`,
        sender: 'bot',
        text: response.data.answer,
        citations: response.data.citations || []
      };

      setMessages((prev) => [...prev, botMessage]);
      setActiveMessageId(botMessage.id); // Automatically focus citations for latest response
    } catch (err) {
      console.error("Failed to generate chat response:", err);
      setError(err.response?.data?.detail || 'RAG generation failed.');
      
      const errorMessage = {
        id: `error-${Date.now()}`,
        sender: 'bot',
        text: 'Sorry, I encountered an error processing that request. Please verify your connection or retry.',
        citations: []
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const getActiveCitations = () => {
    const activeMsg = messages.find((m) => m.id === activeMessageId);
    return activeMsg ? activeMsg.citations : [];
  };

  return (
    <div className="h-[calc(100vh-8.5rem)] flex gap-6 font-sans select-none overflow-hidden -m-4 md:-m-6">
      
      {/* LEFT PANE: Indexed Documents List */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col shrink-0 hidden lg:flex rounded-3xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-1.5">
            <FileText size={14} className="text-indigo-400" />
            <span>Indexed Context</span>
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2 bg-slate-950/20">
          {documents.length === 0 ? (
            <div className="py-12 text-center px-4">
              <FileText size={28} className="mx-auto text-slate-700 mb-2.5" />
              <p className="text-xs text-slate-500 font-semibold leading-relaxed">No indexed documents found.</p>
              <p className="text-[10px] text-slate-600 mt-1 leading-relaxed">Upload documents in the workspace to start chatting.</p>
            </div>
          ) : (
            documents.map((doc) => (
              <div 
                key={doc.id}
                className="bg-slate-900/50 hover:bg-slate-900 border border-slate-850 hover:border-slate-800 p-3.5 rounded-2xl space-y-2 transition-all"
              >
                <div className="flex items-start space-x-2.5 overflow-hidden">
                  <FileText size={15} className="text-indigo-400 shrink-0 mt-0.5" />
                  <div className="overflow-hidden">
                    <p className="text-xs font-bold text-slate-200 truncate" title={doc.name}>
                      {doc.name}
                    </p>
                    <p className="text-[10px] text-slate-500 mt-0.5">{doc.size}</p>
                  </div>
                </div>
                <div className="flex items-center justify-between pt-1 border-t border-slate-850/60">
                  <span className="text-[9px] text-slate-500 font-medium">Status</span>
                  <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded ${
                    doc.status === 'INDEXED' 
                      ? 'text-emerald-400 bg-emerald-500/10' 
                      : doc.status === 'FAILED' 
                      ? 'text-rose-400 bg-rose-500/10' 
                      : 'text-amber-400 bg-amber-500/10 animate-pulse'
                  }`}>
                    {doc.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* CENTER PANE: Conversation View */}
      <main className="flex-1 bg-slate-900 border border-slate-800 rounded-3xl flex flex-col overflow-hidden relative shadow-xl">
        
        {/* Chat Pane Header */}
        <div className="p-4 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-indigo-500/10 rounded-xl text-indigo-400">
              <Brain size={18} className="animate-pulse" />
            </div>
            <div>
              <h2 className="text-sm font-bold text-slate-200">Grounded Copilot</h2>
              <p className="text-[10px] text-slate-500 font-medium mt-0.5">Gemini 1.5 Flash + Qdrant RAG</p>
            </div>
          </div>
          {isLoading && (
            <div className="flex items-center space-x-1 px-3 py-1 bg-indigo-500/10 rounded-full border border-indigo-500/20 text-indigo-400 animate-pulse">
              <Loader2 size={10} className="animate-spin" />
              <span className="text-[9px] font-semibold tracking-wide uppercase">AI Thinking</span>
            </div>
          )}
        </div>

        {/* Message Thread viewport */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4 select-text">
          {messages.map((msg) => (
            <div 
              key={msg.id}
              onClick={() => msg.sender === 'bot' && msg.citations.length > 0 && setActiveMessageId(msg.id)}
              className={`flex flex-col max-w-[85%] ${
                msg.sender === 'user' ? 'ml-auto items-end' : 'mr-auto items-start'
              }`}
            >
              <div className={`p-4 rounded-3xl leading-relaxed text-sm ${
                msg.sender === 'user'
                  ? 'bg-indigo-600 text-white rounded-br-none shadow-md'
                  : `bg-slate-950/60 border ${
                      msg.id === activeMessageId 
                        ? 'border-indigo-500 bg-slate-900/80 shadow-indigo-500/5 shadow-lg' 
                        : 'border-slate-850 hover:border-slate-800/80'
                    } text-slate-300 rounded-bl-none cursor-pointer transition-all`
              }`}>
                <p className="whitespace-pre-wrap">{msg.text}</p>
              </div>

              {/* Citations Indicator link */}
              {msg.sender === 'bot' && msg.citations.length > 0 && (
                <div className="flex items-center space-x-1.5 mt-1.5 ml-2">
                  <Sparkles size={11} className="text-indigo-400 animate-pulse" />
                  <button 
                    onClick={() => setActiveMessageId(msg.id)}
                    className="text-[10px] font-bold text-indigo-400 hover:text-indigo-300 transition-colors uppercase tracking-wider cursor-pointer"
                  >
                    View Context ({msg.citations.length} sources)
                  </button>
                </div>
              )}
            </div>
          ))}
          <div ref={messagesEndRef} />
        </div>

        {/* Submit Form panel */}
        <div className="p-4 border-t border-slate-800 bg-slate-900/60 backdrop-blur-md shrink-0">
          <form onSubmit={handleSend} className="relative flex items-center">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about your documents..."
              className="w-full bg-slate-950/70 border border-slate-800 hover:border-slate-700/80 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/20 rounded-2xl py-3.5 pl-4 pr-16 text-slate-100 placeholder-slate-500 outline-none transition-all duration-300 font-medium text-xs md:text-sm"
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className="absolute right-2 px-3.5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-800 disabled:text-slate-600 text-white rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center space-x-1"
            >
              <Send size={12} />
            </button>
          </form>
        </div>
      </main>

      {/* RIGHT PANE: Citation Details panel */}
      <aside className="w-80 bg-slate-900 border-l border-slate-800 flex flex-col shrink-0 hidden xl:flex rounded-3xl overflow-hidden">
        <div className="p-4 border-b border-slate-800 bg-slate-900/60 backdrop-blur-md">
          <h3 className="text-xs font-bold text-slate-400 uppercase tracking-widest flex items-center space-x-1.5">
            <Sparkles size={14} className="text-indigo-400" />
            <span>Retrieved Sources</span>
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-950/20 select-text">
          {getActiveCitations().length === 0 ? (
            <div className="py-24 text-center px-4">
              <HelpCircle size={32} className="mx-auto text-slate-800 mb-3" />
              <p className="text-xs text-slate-500 font-semibold leading-relaxed">No sources to display</p>
              <p className="text-[10px] text-slate-600 mt-1 max-w-[200px] mx-auto leading-relaxed">
                Click on any document assistant reply with citations to view grounding context.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              <div className="p-3 bg-indigo-500/5 border border-indigo-500/10 rounded-2xl flex items-center space-x-2.5">
                <CheckCircle2 size={16} className="text-indigo-400 shrink-0" />
                <p className="text-[10px] text-indigo-300 font-semibold uppercase tracking-wider leading-relaxed">
                  Strictly Grounded Context
                </p>
              </div>

              {getActiveCitations().map((citation, index) => (
                <div 
                  key={index}
                  className="bg-slate-900 border border-slate-800 hover:border-slate-750 p-4.5 rounded-2xl space-y-3 transition-colors shadow-sm"
                >
                  <div className="flex items-center justify-between text-[10px] font-semibold text-indigo-450 uppercase tracking-wide">
                    <span className="flex items-center space-x-1">
                      <ListOrdered size={10} />
                      <span>Source #{index + 1}</span>
                    </span>
                    <span className="text-slate-500 text-[9px] font-bold">
                      Page {citation.page_number}
                    </span>
                  </div>
                  <div className="text-[11px] leading-relaxed text-slate-350 p-3 bg-slate-950/50 rounded-xl border border-slate-850/60 font-sans">
                    <div className="flex items-start space-x-1">
                      <CornerDownRight size={12} className="text-indigo-500 shrink-0 mt-0.5" />
                      <p>{citation.chunk_text}</p>
                    </div>
                  </div>
                  <div className="text-[9px] text-slate-500 flex items-center justify-between border-t border-slate-850/50 pt-2 font-medium">
                    <span className="truncate max-w-[150px]" title={citation.document_name}>
                      {citation.document_name}
                    </span>
                    <span>Idx: {citation.chunk_index}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </aside>

    </div>
  );
};

export default Chat;
