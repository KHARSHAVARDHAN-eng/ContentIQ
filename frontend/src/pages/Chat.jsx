import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { Send, Brain, FileText, CornerDownRight, ListOrdered, CheckCircle2, Loader2, Sparkles, HelpCircle, ShieldAlert, ThumbsUp, ThumbsDown, MessageSquare, Plus, Trash2, Edit3, Check, X, ChevronRight } from 'lucide-react';

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

  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editTitle, setEditTitle] = useState('');

  const samplePrompts = [
    "Summarize the main points of my uploaded documents",
    "Identify any deadlines or milestones",
    "What are the major compliance or risk concerns?"
  ];

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

  const fetchSessions = async () => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/conversations/sessions`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      setSessions(response.data || []);
    } catch (err) {
      console.error("Failed to load sessions:", err);
    }
  };

  useEffect(() => {
    fetchDocuments();
    fetchSessions();
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, isLoading]);

  const handleSend = async (e, customInput = null) => {
    if (e) e.preventDefault();
    const activeInput = customInput !== null ? customInput : input;
    const cleanInput = activeInput.trim();
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
        { question: cleanInput, session_id: currentSessionId },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      const botMessage = {
        id: `bot-${Date.now()}`,
        sender: 'bot',
        text: response.data.answer,
        citations: response.data.citations || [],
        evaluation_id: response.data.evaluation_id
      };

      if (response.data.session_id) {
        setCurrentSessionId(response.data.session_id);
        fetchSessions();
      }

      setMessages((prev) => [...prev, botMessage]);
      setActiveMessageId(botMessage.id); // Focus citations for latest response
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

  const handleFeedback = async (messageId, evaluationId, feedbackValue) => {
    try {
      const token = localStorage.getItem('token');
      const currentMsg = messages.find(m => m.id === messageId);
      const newValue = currentMsg?.feedback === feedbackValue ? 0 : feedbackValue;

      await axios.post(
        `${API_URL}/evaluations/${evaluationId}/feedback`,
        { feedback: newValue },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      setMessages((prev) =>
        prev.map((m) =>
          m.id === messageId ? { ...m, feedback: newValue } : m
        )
      );
    } catch (err) {
      console.error("Failed to submit feedback:", err);
    }
  };

  const handleSelectSession = async (sessionId) => {
    try {
      const token = localStorage.getItem('token');
      const response = await axios.get(`${API_URL}/conversations/sessions/${sessionId}/messages`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      const loadedMessages = response.data.map(m => ({
        id: m.id,
        sender: m.sender,
        text: m.text,
        citations: m.citations || [],
        evaluation_id: null,
      }));
      
      setMessages(loadedMessages.length > 0 ? loadedMessages : [
        {
          id: 'welcome',
          sender: 'bot',
          text: 'Hello! I am your DocumentIQ Assistant. Ask me anything about your uploaded documents, and I will answer with citations grounded in the source text.',
          citations: []
        }
      ]);
      setCurrentSessionId(sessionId);
    } catch (err) {
      console.error("Failed to load session messages:", err);
    }
  };

  const handleNewChat = () => {
    setCurrentSessionId(null);
    setMessages([
      {
        id: 'welcome',
        sender: 'bot',
        text: 'Hello! I am your DocumentIQ Assistant. Ask me anything about your uploaded documents, and I will answer with citations grounded in the source text.',
        citations: []
      }
    ]);
  };

  const handleRenameSession = async (sessionId, newTitle) => {
    if (!newTitle.trim()) return;
    try {
      const token = localStorage.getItem('token');
      await axios.put(
        `${API_URL}/conversations/sessions/${sessionId}`,
        { title: newTitle },
        { headers: { Authorization: `Bearer ${token}` } }
      );
      setEditingSessionId(null);
      fetchSessions();
    } catch (err) {
      console.error("Failed to rename session:", err);
    }
  };

  const handleDeleteSession = async (sessionId, e) => {
    e.stopPropagation();
    try {
      const token = localStorage.getItem('token');
      await axios.delete(`${API_URL}/conversations/sessions/${sessionId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (currentSessionId === sessionId) {
        handleNewChat();
      }
      fetchSessions();
    } catch (err) {
      console.error("Failed to delete session:", err);
    }
  };

  const getActiveCitations = () => {
    const activeMsg = messages.find((m) => m.id === activeMessageId);
    return activeMsg ? activeMsg.citations : [];
  };

  return (
    <div className="h-[calc(100vh-8.5rem)] flex gap-5 font-sans overflow-hidden -m-4 md:-m-6 relative z-10 select-none">
      
      {/* LEFT PANE: Sessions List & Core Index status */}
      <aside className="w-60 bg-slate-900/40 backdrop-blur-md border-r border-slate-900 flex flex-col shrink-0 hidden lg:flex rounded-l-3xl overflow-hidden">
        
        {/* Sessions Sidebar Header */}
        <div className="p-4 border-b border-slate-900 bg-slate-900/60 flex items-center justify-between shrink-0">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center space-x-1.5">
            <MessageSquare size={12} className="text-indigo-400" />
            <span>Chat Sessions</span>
          </h3>
          <button 
            id="chat-new-session-btn"
            onClick={handleNewChat}
            className="p-1 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-slate-200 transition-colors cursor-pointer"
            title="Start New Chat"
          >
            <Plus size={14} />
          </button>
        </div>

        {/* Sessions Scroll List */}
        <div className="h-[45%] overflow-y-auto p-3 space-y-1.5 border-b border-slate-900 bg-slate-950/20 shrink-0">
          {sessions.length === 0 ? (
            <div className="py-10 text-center px-4">
              <MessageSquare size={18} className="mx-auto text-slate-800 mb-2" />
              <p className="text-[10px] text-slate-550 font-bold">No chat history.</p>
            </div>
          ) : (
            sessions.map((sess) => {
              const isSelected = sess.id === currentSessionId;
              const isEditing = sess.id === editingSessionId;
              
              return (
                <div 
                  key={sess.id}
                  onClick={() => !isEditing && handleSelectSession(sess.id)}
                  className={`group relative flex items-center justify-between p-2.5 rounded-xl border transition-all cursor-pointer ${
                    isSelected 
                      ? 'bg-indigo-600/10 border-indigo-500/20 text-indigo-400 font-semibold' 
                      : 'bg-transparent border-transparent text-slate-400 hover:text-slate-350 hover:bg-slate-900/40'
                  }`}
                >
                  {isEditing ? (
                    <div className="flex items-center space-x-1 w-full" onClick={e => e.stopPropagation()}>
                      <input
                        type="text"
                        value={editTitle}
                        onChange={e => setEditTitle(e.target.value)}
                        className="bg-slate-950 border border-slate-800 focus:border-indigo-500 text-[10px] px-1.5 py-0.5 rounded outline-none text-slate-200 w-full"
                        onKeyDown={e => e.key === 'Enter' && handleRenameSession(sess.id, editTitle)}
                      />
                      <button 
                        onClick={() => handleRenameSession(sess.id, editTitle)}
                        className="p-0.5 text-emerald-400 cursor-pointer"
                      >
                        <Check size={11} />
                      </button>
                      <button 
                        onClick={() => setEditingSessionId(null)}
                        className="p-0.5 text-slate-500 cursor-pointer"
                      >
                        <X size={11} />
                      </button>
                    </div>
                  ) : (
                    <>
                      <span className="text-[11px] truncate max-w-[130px]">{sess.title}</span>
                      <div className="opacity-0 group-hover:opacity-100 flex items-center space-x-1 absolute right-2 bg-slate-900/90 rounded pl-1">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setEditingSessionId(sess.id);
                            setEditTitle(sess.title);
                          }}
                          className="p-0.5 text-slate-500 hover:text-indigo-400 cursor-pointer"
                          title="Rename"
                        >
                          <Edit3 size={11} />
                        </button>
                        <button
                          onClick={(e) => handleDeleteSession(sess.id, e)}
                          className="p-0.5 text-slate-500 hover:text-rose-450 cursor-pointer"
                          title="Delete"
                        >
                          <Trash2 size={11} />
                        </button>
                      </div>
                    </>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Core Index Status Section */}
        <div className="p-4 border-b border-slate-900 bg-slate-900/60 shrink-0">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center space-x-1.5">
            <FileText size={12} className="text-indigo-400" />
            <span>Indexed Context</span>
          </h3>
        </div>
        <div className="flex-1 overflow-y-auto p-3 space-y-2 bg-slate-950/20">
          {documents.length === 0 ? (
            <div className="py-8 text-center px-4">
              <FileText size={20} className="mx-auto text-slate-800 mb-2" />
              <p className="text-[10px] text-slate-650 leading-relaxed font-bold">No documents uploaded.</p>
            </div>
          ) : (
            documents.map((doc) => (
              <div 
                key={doc.id}
                className="bg-slate-900/30 border border-slate-900 p-2.5 rounded-xl space-y-1.5"
              >
                <p className="text-[10px] font-bold text-slate-350 truncate" title={doc.name}>
                  {doc.name}
                </p>
                <div className="flex items-center justify-between text-[9px] text-slate-550 border-t border-slate-900/40 pt-1">
                  <span>Pages: {doc.page_count}</span>
                  <span className={doc.status === 'INDEXED' ? 'text-emerald-400' : 'text-amber-400 animate-pulse'}>
                    {doc.status}
                  </span>
                </div>
              </div>
            ))
          )}
        </div>
      </aside>

      {/* CENTER PANE: Conversation Window */}
      <main className="flex-1 bg-slate-900/60 border border-slate-900 rounded-3xl flex flex-col overflow-hidden relative shadow-inner">
        
        {/* Chat window Header bar */}
        <div className="p-4 border-b border-slate-900 bg-slate-900/65 flex items-center justify-between shrink-0 z-10">
          <div className="flex items-center space-x-2.5">
            <div className="p-2 bg-indigo-500/10 rounded-xl text-indigo-400 shadow-inner">
              <Brain size={16} className="animate-pulse" />
            </div>
            <div>
              <h2 className="text-xs font-bold text-slate-200 uppercase tracking-wider">Grounded Copilot</h2>
              <p className="text-[10px] text-slate-500 font-semibold mt-0.5">Gemini 1.5 Flash + Qdrant similarity scores</p>
            </div>
          </div>
          {isLoading && (
            <div className="flex items-center space-x-1.5 px-3 py-1 bg-indigo-500/10 rounded-full border border-indigo-500/10 text-indigo-400 animate-pulse">
              <Loader2 size={11} className="animate-spin" />
              <span className="text-[9px] font-bold uppercase tracking-wider">AI Thinking</span>
            </div>
          )}
        </div>

        {/* Message Thread viewports */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-5 select-text hide-scrollbar">
          {messages.map((msg) => (
            <div 
              key={msg.id}
              onClick={() => msg.sender === 'bot' && msg.citations.length > 0 && setActiveMessageId(msg.id)}
              className={`flex flex-col max-w-[85%] ${
                msg.sender === 'user' ? 'ml-auto items-end animate-slide-up' : 'mr-auto items-start animate-fade-in'
              }`}
            >
              {/* Message text bubble */}
              <div className={`p-4 rounded-2xl leading-relaxed text-xs md:text-sm ${
                msg.sender === 'user'
                  ? 'bg-indigo-600 text-white rounded-tr-none shadow-md shadow-indigo-650/15'
                  : `bg-slate-950/45 border ${
                      msg.id === activeMessageId 
                        ? 'border-indigo-500/40 bg-slate-900/80 shadow-[0_0_20px_-3px_rgba(99,102,241,0.08)]' 
                        : 'border-slate-900 hover:border-slate-850'
                    } text-slate-350 rounded-tl-none cursor-pointer transition-all`
              }`}>
                <p className="whitespace-pre-wrap">{msg.text}</p>
              </div>

              {/* Citations View trigger & feedback logs */}
              {msg.sender === 'bot' && msg.id !== 'welcome' && (
                <div className="flex items-center space-x-3 mt-2 ml-1">
                  {msg.citations && msg.citations.length > 0 && (
                    <button 
                      onClick={() => setActiveMessageId(msg.id)}
                      className="inline-flex items-center space-x-1.5 text-[10px] font-bold text-indigo-400 hover:text-indigo-300 transition-colors uppercase tracking-wider cursor-pointer"
                    >
                      <Sparkles size={11} className="text-indigo-400" />
                      <span>Context ({msg.citations.length} hits)</span>
                    </button>
                  )}
                  {msg.evaluation_id && (
                    <div className={`flex items-center space-x-1.5 ${msg.citations && msg.citations.length > 0 ? 'border-l border-slate-800 pl-3' : ''}`}>
                      <button
                        onClick={() => handleFeedback(msg.id, msg.evaluation_id, 1)}
                        className={`p-1 rounded-lg transition-colors cursor-pointer border ${
                          msg.feedback === 1 
                            ? 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20' 
                            : 'text-slate-650 hover:text-slate-400 hover:bg-slate-850/40 border-transparent'
                        }`}
                        title="Good Answer"
                      >
                        <ThumbsUp size={11} />
                      </button>
                      <button
                        onClick={() => handleFeedback(msg.id, msg.evaluation_id, -1)}
                        className={`p-1 rounded-lg transition-colors cursor-pointer border ${
                          msg.feedback === -1 
                            ? 'text-rose-455 bg-rose-500/10 border-rose-500/20' 
                            : 'text-slate-655 hover:text-slate-400 hover:bg-slate-855/40 border-transparent'
                        }`}
                        title="Bad Answer"
                      >
                        <ThumbsDown size={11} />
                      </button>
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
          
          {/* Default suggestion box on Welcome screen */}
          {messages.length === 1 && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-6 max-w-xl mx-auto">
              {samplePrompts.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(null, prompt)}
                  className="p-3 bg-slate-950/40 hover:bg-slate-900/60 border border-slate-900 hover:border-indigo-500/20 text-left text-[11px] text-slate-400 hover:text-slate-200 rounded-xl transition-all cursor-pointer leading-relaxed shadow-sm"
                >
                  {prompt}
                  <ChevronRight size={10} className="inline-block ml-1 text-slate-600 group-hover:text-indigo-400" />
                </button>
              ))}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input box Form footer */}
        <div className="p-4 border-t border-slate-900 bg-slate-900/65 shrink-0 z-10">
          <form onSubmit={handleSend} className="relative flex items-center">
            <input
              id="chat-query-input"
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask a question about indexed sources..."
              className="w-full bg-slate-950/70 border border-slate-850 hover:border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500/25 rounded-2xl py-3.5 pl-4 pr-16 text-slate-200 placeholder-slate-650 outline-none transition-all duration-300 text-xs md:text-sm shadow-inner"
              disabled={isLoading}
            />
            <button
              id="chat-send-submit-btn"
              type="submit"
              disabled={isLoading || !input.trim()}
              className="absolute right-2 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 disabled:bg-slate-850 disabled:text-slate-650 text-white rounded-xl text-xs font-bold transition-all cursor-pointer flex items-center space-x-1 shadow-md"
            >
              <Send size={12} />
            </button>
          </form>
        </div>
      </main>

      {/* RIGHT PANE: Citations panel */}
      <aside className="w-80 bg-slate-900/40 backdrop-blur-md border-l border-slate-900 flex flex-col shrink-0 hidden xl:flex rounded-r-3xl overflow-hidden">
        <div className="p-4 border-b border-slate-900 bg-slate-900/60">
          <h3 className="text-[10px] font-bold text-slate-500 uppercase tracking-widest flex items-center space-x-1.5">
            <Sparkles size={12} className="text-indigo-400" />
            <span>Retrieved context</span>
          </h3>
        </div>
        
        <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-slate-950/20 select-text hide-scrollbar">
          {getActiveCitations().length === 0 ? (
            <div className="py-24 text-center px-4">
              <HelpCircle size={28} className="mx-auto text-slate-755 mb-2.5" />
              <p className="text-[10px] text-slate-550 font-bold leading-relaxed">No active citations</p>
              <p className="text-[9px] text-slate-650 mt-1 max-w-[180px] mx-auto leading-relaxed">
                Click "Context" under any bot reply bubble to display its reference source chunks.
              </p>
            </div>
          ) : (
            <div className="space-y-3 pb-4 animate-fade-in">
              {/* grounded indicator */}
              <div className="p-2.5 bg-indigo-500/5 border border-indigo-500/10 rounded-xl flex items-center space-x-2">
                <CheckCircle2 size={14} className="text-indigo-400 shrink-0" />
                <span className="text-[9px] text-indigo-300 font-bold uppercase tracking-wider">Source Grounded</span>
              </div>

              {getActiveCitations().map((citation, index) => (
                <div 
                  key={index}
                  className="bg-slate-900 border border-slate-900/80 hover:border-slate-850 p-4 rounded-xl space-y-2.5 transition-colors shadow-sm"
                >
                  <div className="flex items-center justify-between text-[9px] font-bold text-indigo-400 uppercase">
                    <span className="flex items-center space-x-1">
                      <ListOrdered size={10} />
                      <span>Source #{index + 1}</span>
                    </span>
                    <span className="text-slate-500">
                      Page {citation.page_number}
                    </span>
                  </div>
                  
                  <div className="text-[10.5px] leading-relaxed text-slate-350 p-2.5 bg-slate-950/50 rounded-lg border border-slate-900/60 font-sans">
                    <div className="flex items-start space-x-1">
                      <CornerDownRight size={10} className="text-indigo-500 shrink-0 mt-0.5" />
                      <p>{citation.chunk_text}</p>
                    </div>
                  </div>
                  
                  <div className="text-[9px] text-slate-500 flex items-center justify-between border-t border-slate-900/40 pt-1.5 font-medium">
                    <span className="truncate max-w-[130px]" title={citation.document_name}>
                      {citation.document_name}
                    </span>
                    <span>Score: {(hit => hit ? (hit.score * 100).toFixed(0) + '%' : 'N/A')()}</span>
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
