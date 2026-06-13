import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { 
  Send, Brain, FileText, Loader2, Sparkles, ThumbsUp, ThumbsDown, 
  MessageSquare, Plus, Trash2, Edit3, Check, X, ChevronRight, 
  BookOpen, ChevronLeft, Paperclip, CornerDownRight 
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import DocumentDrawer from '../components/DocumentDrawer';

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
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [previewDocumentId, setPreviewDocumentId] = useState(null);

  const messagesEndRef = useRef(null);

  const [sessions, setSessions] = useState([]);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [editingSessionId, setEditingSessionId] = useState(null);
  const [editTitle, setEditTitle] = useState('');
  const [isUploading, setIsUploading] = useState(false);

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
      setActiveMessageId(botMessage.id);
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

  const handleFileUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    setIsUploading(true);
    const formData = new FormData();
    formData.append("file", file);

    try {
      const token = localStorage.getItem('token');
      await axios.post(`${API_URL}/documents/upload`, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
          Authorization: `Bearer ${token}`
        }
      });
      fetchDocuments();
    } catch (err) {
      console.error("Upload failed in chat:", err);
    } finally {
      setIsUploading(false);
    }
  };

  const renderAnswerText = (text, citations = []) => {
    if (!citations || citations.length === 0) return text;
    
    // Match [1], [2], etc.
    const parts = text.split(/(\[\d+\])/g);
    return parts.map((part, idx) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const citationIdx = parseInt(match[1], 10) - 1;
        const citation = citations[citationIdx];
        if (citation) {
          return (
            <button
              key={idx}
              type="button"
              onClick={() => setPreviewDocumentId(citation.document_id)}
              className="inline-flex items-center justify-center w-4.5 h-4.5 rounded-full bg-emerald-50 hover:bg-emerald-100 border border-emerald-150 text-[9px] font-bold text-emerald-700 cursor-pointer mx-0.5 select-none align-middle btn-press-active"
              title={`${citation.document_name} - Page ${citation.page_number}`}
            >
              {match[1]}
            </button>
          );
        }
      }
      return part;
    });
  };

  const hasThreadMessages = messages.length > 1;

  return (
    <div className="h-[calc(100vh-8.5rem)] flex gap-6 font-sans overflow-hidden -m-4 md:-m-6 relative z-10 select-none">
      
      {/* LEFT PANEL: Collapsible Chat Sessions Sidebar */}
      <AnimatePresence initial={false}>
        {!sidebarCollapsed && (
          <motion.aside 
            initial={{ width: 0, opacity: 0 }}
            animate={{ width: 220, opacity: 1 }}
            exit={{ width: 0, opacity: 0 }}
            transition={{ type: 'spring', damping: 28, stiffness: 220 }}
            className="bg-[#FCFAF6] border-r border-[#E5DDD0] flex flex-col shrink-0 rounded-l-2xl overflow-hidden shadow-sm"
          >
            {/* Sidebar header */}
            <div className="p-4 border-b border-[#E5DDD0]/80 bg-[#FCFAF6] flex items-center justify-between shrink-0">
              <h3 className="text-[9px] font-bold text-zinc-400 uppercase tracking-widest flex items-center space-x-1.5">
                <MessageSquare size={11} className="text-zinc-650" />
                <span>Chat History</span>
              </h3>
              <button 
                id="chat-start-new-session"
                onClick={handleNewChat}
                className="p-1 hover:bg-[#F8F4EC] rounded-lg text-zinc-600 hover:text-[#111111] border border-[#E5DDD0] bg-white transition-all cursor-pointer btn-press-active shadow-sm"
                title="New Chat"
              >
                <Plus size={12} />
              </button>
            </div>

            {/* Sessions list */}
            <div className="flex-1 overflow-y-auto p-3 space-y-1.5 hide-scrollbar bg-[#FCFAF6]/60">
              {sessions.length === 0 ? (
                <div className="py-12 text-center px-4">
                  <MessageSquare size={16} className="mx-auto text-zinc-300 mb-2" />
                  <p className="text-[9px] text-zinc-450 font-bold">No threads yet</p>
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
                          ? 'bg-white border-[#E5DDD0] text-[#111111] font-bold shadow-sm' 
                          : 'bg-transparent border-transparent text-zinc-655 hover:text-[#111111] hover:bg-[#F8F4EC]/40'
                      }`}
                    >
                      {isEditing ? (
                        <div className="flex items-center space-x-1 w-full" onClick={e => e.stopPropagation()}>
                          <input
                            type="text"
                            value={editTitle}
                            onChange={e => setEditTitle(e.target.value)}
                            className="bg-white border border-[#E5DDD0] focus:border-[#111111] text-[10px] px-1.5 py-0.5 rounded outline-none text-[#111111] w-full"
                            onKeyDown={e => e.key === 'Enter' && handleRenameSession(sess.id, editTitle)}
                            autoFocus
                          />
                          <button 
                            onClick={() => handleRenameSession(sess.id, editTitle)}
                            className="p-0.5 text-emerald-600 cursor-pointer"
                          >
                            <Check size={11} />
                          </button>
                          <button 
                            onClick={() => setEditingSessionId(null)}
                            className="p-0.5 text-zinc-450 cursor-pointer"
                          >
                            <X size={11} />
                          </button>
                        </div>
                      ) : (
                        <>
                          <span className="text-[10.5px] truncate max-w-[130px]">{sess.title}</span>
                          <div className="opacity-0 group-hover:opacity-100 flex items-center space-x-0.5 absolute right-1.5 bg-[#FCFAF6] rounded pl-1.5 transition-all">
                            <button
                              onClick={(e) => {
                                e.stopPropagation();
                                setEditingSessionId(sess.id);
                                setEditTitle(sess.title);
                              }}
                              className="p-0.5 text-zinc-450 hover:text-[#111111] cursor-pointer"
                              title="Rename"
                            >
                              <Edit3 size={10} />
                            </button>
                            <button
                              onClick={(e) => handleDeleteSession(sess.id, e)}
                              className="p-0.5 text-zinc-450 hover:text-rose-600 cursor-pointer"
                              title="Delete"
                            >
                              <Trash2 size={10} />
                            </button>
                          </div>
                        </>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </motion.aside>
        )}
      </AnimatePresence>

      {/* CENTER PANE: Conversation Window */}
      <main className="flex-1 bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl flex flex-col overflow-hidden relative shadow-sm">
        
        {/* Header bar */}
        <div className="p-4 border-b border-[#E5DDD0] bg-[#FCFAF6]/80 backdrop-blur-md flex items-center justify-between shrink-0 z-10">
          <div className="flex items-center space-x-3">
            {/* Collapse toggle */}
            <button
              onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
              className="p-1.5 hover:bg-[#F8F4EC] border border-[#E5DDD0] bg-white rounded-lg text-zinc-500 hover:text-[#111111] transition-all cursor-pointer btn-press-active"
              title={sidebarCollapsed ? "Expand History" : "Collapse History"}
            >
              <ChevronLeft size={13} className={`transition-transform duration-300 ${sidebarCollapsed ? 'rotate-180' : ''}`} />
            </button>
            <div className="flex items-center space-x-2">
              <div className="p-1.5 bg-[#F8F4EC] border border-[#E5DDD0] rounded-lg text-zinc-750">
                <Brain size={14} className={isLoading ? 'animate-pulse' : ''} />
              </div>
              <div>
                <h2 className="text-[10px] font-bold text-[#111111] uppercase tracking-wider">Grounded Copilot</h2>
                <p className="text-[9px] text-[#666666] font-bold mt-0.5">Gemini RAG Inferences</p>
              </div>
            </div>
          </div>

          {isLoading && (
            <div className="flex items-center space-x-1.5 px-2.5 py-0.5 bg-emerald-50/60 rounded-full border border-emerald-250 text-emerald-700 animate-pulse">
              <Loader2 size={9} className="animate-spin" />
              <span className="text-[8.5px] font-bold uppercase tracking-wider">Thinking</span>
            </div>
          )}
        </div>

        {/* Message Thread Viewport */}
        <div className="flex-1 overflow-y-auto p-6 md:p-8 space-y-8 select-text hide-scrollbar">
          {!hasThreadMessages ? (
            /* Perplexity Initial Center Screen */
            <div className="max-w-xl mx-auto h-full flex flex-col justify-center space-y-6 min-h-[350px] animate-fade-in">
              <div className="text-center space-y-2">
                <h2 className="text-xl md:text-2xl font-extrabold tracking-tight text-[#111111] leading-snug font-bevellier">
                  What do you want to know about your documents?
                </h2>
                <p className="text-xs text-[#666666] font-semibold">
                  Ask questions to synthesize indexed documents with citation links.
                </p>
              </div>

              {/* Big Query Input Box */}
              <div className="bg-white border border-[#E5DDD0] hover:border-zinc-400 rounded-xl p-3 shadow-sm focus-within:border-[#111111] focus-within:ring-1 focus-within:ring-[#111111] transition-all relative">
                <form onSubmit={handleSend} className="space-y-3">
                  <textarea
                    id="chat-query-box"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="Ask anything..."
                    rows={2}
                    className="w-full bg-transparent resize-none text-xs md:text-sm text-[#111111] placeholder-zinc-400 outline-none p-1 font-sans"
                    disabled={isLoading}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSend(e);
                      }
                    }}
                  />
                  
                  <div className="flex items-center justify-between pt-1">
                    {/* Action chips in input box */}
                    <div className="flex items-center space-x-2">
                      {/* Attach button placeholder */}
                      <label className="flex items-center space-x-1 px-2.5 py-1.5 bg-[#FCFAF6] hover:bg-[#F8F4EC] border border-[#E5DDD0] rounded-lg text-[10px] font-semibold text-zinc-650 cursor-pointer transition-all btn-press-active">
                        <Paperclip size={11} className={isUploading ? 'animate-spin' : ''} />
                        <span>{isUploading ? 'Uploading...' : 'Attach File'}</span>
                        <input 
                          type="file" 
                          className="hidden" 
                          onChange={handleFileUpload} 
                          disabled={isUploading} 
                        />
                      </label>

                      <span className="text-[10px] font-semibold text-[#666666] bg-[#FCFAF6] border border-[#E5DDD0]/60 px-2 py-1 rounded-lg">
                        All Files
                      </span>
                    </div>

                    <button
                      id="chat-query-send-btn"
                      type="submit"
                      disabled={isLoading || !input.trim()}
                      className="p-2 bg-[#111111] hover:bg-zinc-800 disabled:bg-[#F8F4EC] disabled:text-zinc-400 text-white rounded-xl transition-all cursor-pointer flex items-center justify-center shadow-sm btn-press-active"
                    >
                      <Send size={12} />
                    </button>
                  </div>
                </form>
              </div>

              {/* Suggestion prompt cards */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 pt-2">
                {samplePrompts.map((prompt, idx) => (
                  <button
                    key={idx}
                    onClick={() => handleSend(null, prompt)}
                    className="p-3 bg-[#FCFAF6] hover:bg-white border border-[#E5DDD0] hover:border-zinc-400 text-left text-[10.5px] text-zinc-655 hover:text-[#111111] rounded-xl transition-all cursor-pointer leading-relaxed shadow-sm btn-press-active flex flex-col justify-between"
                  >
                    <span>{prompt}</span>
                    <div className="flex justify-end w-full mt-2">
                      <ChevronRight size={11} className="text-zinc-400" />
                    </div>
                  </button>
                ))}
              </div>
            </div>
          ) : (
            /* Sequential chat message blocks */
            <div className="space-y-8">
              {messages.map((msg) => (
                <div 
                  key={msg.id}
                  className="space-y-4 animate-fade-in"
                >
                  {msg.sender === 'user' ? (
                    /* User Prompt: Clean heading bold text (no speech bubble) */
                    <div className="border-b border-[#E5DDD0]/50 pb-3 mt-4">
                      <h2 className="text-base md:text-lg font-extrabold text-[#111111] tracking-tight leading-relaxed font-bevellier">
                        {msg.text}
                      </h2>
                    </div>
                  ) : (
                    /* Bot Answer block */
                    <div className="space-y-5">
                      
                      {/* Source Citation Cards Grid */}
                      {msg.citations && msg.citations.length > 0 && (
                        <div className="space-y-2">
                          <div className="flex items-center space-x-1.5 text-zinc-400 text-[9px] font-bold uppercase tracking-wider">
                            <BookOpen size={11} className="text-zinc-500" />
                            <span>Sources</span>
                          </div>
                          <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5">
                            {msg.citations.map((citation, idx) => (
                              <button
                                key={idx}
                                onClick={() => setPreviewDocumentId(citation.document_id)}
                                className="bg-[#FCFAF6] hover:bg-white border border-[#E5DDD0] hover:border-zinc-400 rounded-xl p-2.5 text-left transition-all cursor-pointer relative group flex items-start space-x-2 btn-press-active shadow-sm"
                              >
                                <FileText size={13} className="text-zinc-500 shrink-0 mt-0.5" />
                                <div className="overflow-hidden pr-3">
                                  <p className="text-[10px] font-bold text-zinc-800 truncate leading-tight">{citation.document_name}</p>
                                  <p className="text-[8.5px] text-[#666666] font-bold mt-0.5 leading-none">Page {citation.page_number} • Match</p>
                                </div>
                                <span className="absolute right-2 top-2 h-4 w-4 bg-[#F8F4EC] border border-[#E5DDD0] text-[#111111] group-hover:bg-[#111111] group-hover:text-white group-hover:border-transparent rounded-full flex items-center justify-center text-[8.5px] font-bold transition-colors">{idx + 1}</span>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {/* Editorial Answer Text with parsed Clickable Badges */}
                      <div className="flex items-start gap-3">
                        <div className="w-6 h-6 rounded-lg bg-[#A8D5F2]/20 border border-[#A8D5F2]/40 text-[#111111] flex items-center justify-center shrink-0 mt-0.5" title="Double-checked source">
                          <Check size={11} className="stroke-[3]" />
                        </div>
                        <div className="text-xs md:text-sm text-[#111111] leading-relaxed font-sans select-text whitespace-pre-wrap max-w-none flex-1 pl-1">
                          {renderAnswerText(msg.text, msg.citations)}
                        </div>
                      </div>

                      {/* Feedback action buttons */}
                      {msg.id !== 'welcome' && (
                        <div className="flex items-center space-x-4 pt-1 pb-3 border-b border-[#E5DDD0]/50">
                          {msg.evaluation_id && (
                            <div className="flex items-center space-x-1.5">
                              <button
                                onClick={() => handleFeedback(msg.id, msg.evaluation_id, 1)}
                                className={`p-1.5 rounded-lg border transition-colors cursor-pointer btn-press-active ${
                                  msg.feedback === 1 
                                    ? 'text-emerald-700 bg-emerald-50 border-emerald-100' 
                                    : 'text-zinc-400 hover:text-zinc-700 bg-white border-zinc-200'
                                }`}
                                title="Grounded"
                              >
                                <ThumbsUp size={11} />
                              </button>
                              <button
                                onClick={() => handleFeedback(msg.id, msg.evaluation_id, -1)}
                                className={`p-1.5 rounded-lg border transition-colors cursor-pointer btn-press-active ${
                                  msg.feedback === -1 
                                    ? 'text-rose-700 bg-rose-50 border-rose-100' 
                                    : 'text-zinc-400 hover:text-zinc-700 bg-white border-zinc-200'
                                }`}
                                title="Ungrounded"
                              >
                                <ThumbsDown size={11} />
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input box pinned to the bottom */}
        {hasThreadMessages && (
          <div className="p-4 border-t border-[#E5DDD0] bg-[#FCFAF6] shrink-0 z-10">
            <form onSubmit={handleSend} className="relative flex items-center max-w-2xl mx-auto">
              <input
                id="chat-query-box"
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder="Ask a follow-up..."
                className="w-full bg-white border border-[#E5DDD0] hover:border-zinc-400 focus:border-[#111111] rounded-full py-2.5 pl-4.5 pr-16 text-[#111111] placeholder-zinc-400 outline-none transition-all duration-200 text-xs md:text-sm shadow-sm font-sans"
                disabled={isLoading}
              />
              <button
                id="chat-query-send-btn"
                type="submit"
                disabled={isLoading || !input.trim()}
                className="absolute right-2 px-3 py-1.5 bg-[#111111] hover:bg-zinc-800 disabled:bg-[#F8F4EC] disabled:text-zinc-400 text-white rounded-full transition-all cursor-pointer flex items-center justify-center shadow-sm btn-press-active"
              >
                <Send size={11} />
              </button>
            </form>
          </div>
        )}
      </main>

      {/* Slide-over document viewer */}
      <DocumentDrawer 
        documentId={previewDocumentId} 
        onClose={() => setPreviewDocumentId(null)} 
      />

    </div>
  );
};

export default Chat;
