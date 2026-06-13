import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { 
  GraduationCap, 
  HelpCircle, 
  ChevronRight, 
  ChevronLeft, 
  RotateCw, 
  Download, 
  Trash2, 
  Check, 
  X as XIcon, 
  Sparkles, 
  AlertCircle, 
  Loader2, 
  FileText,
  Map,
  BookOpen,
  ArrowRight,
  RefreshCw,
  Trophy,
  HelpCircle as HelpIcon,
  Layers,
  ChevronDown
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const StudyTools = () => {
  const { user } = useAuth();
  const [activeTab, setActiveTab] = useState('flashcards'); // 'flashcards', 'mcqs', 'mindmaps', 'studypacks'
  const [documents, setDocuments] = useState([]);
  const [isLoadingDocs, setIsLoadingDocs] = useState(true);
  
  // Flashcards States
  const [decks, setDecks] = useState([]);
  const [selectedDeckId, setSelectedDeckId] = useState(null);
  const [selectedDocIdForFC, setSelectedDocIdForFC] = useState('');
  const [isGeneratingFC, setIsGeneratingFC] = useState(false);
  const [fcError, setFcError] = useState('');
  const [currentCardIndex, setCurrentCardIndex] = useState(0);
  const [isFlipped, setIsFlipped] = useState(false);

  // MCQ States
  const [selectedDocIdForMCQ, setSelectedDocIdForMCQ] = useState('');
  const [mcqDifficulty, setMcqDifficulty] = useState('Medium'); // 'Easy', 'Medium', 'Hard'
  const [mcqCount, setMcqCount] = useState(5);
  const [isGeneratingMCQ, setIsGeneratingMCQ] = useState(false);
  const [mcqError, setMcqError] = useState('');
  const [mcqs, setMcqs] = useState([]);
  const [quizStarted, setQuizStarted] = useState(false);
  const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
  const [selectedOption, setSelectedOption] = useState(null); // 'A', 'B', 'C', 'D'
  const [answerChecked, setAnswerChecked] = useState(false);
  const [quizScore, setQuizScore] = useState(0);
  const [quizComplete, setQuizComplete] = useState(false);
  const [quizHistory, setQuizHistory] = useState([]); // user's answers

  // Mindmap States
  const [selectedDocIdForMM, setSelectedDocIdForMM] = useState('');
  const [isGeneratingMM, setIsGeneratingMM] = useState(false);
  const [mmError, setMmError] = useState('');
  const [mindmap, setMindmap] = useState(null);
  const [collapsedNodes, setCollapsedNodes] = useState(new Set());
  const [zoom, setZoom] = useState(1);
  const [pan, setPan] = useState({ x: 0, y: 0 });
  const [isDragging, setIsDragging] = useState(false);
  const [dragStart, setDragStart] = useState({ x: 0, y: 0 });

  // Study Pack States
  const [selectedDocIdForSP, setSelectedDocIdForSP] = useState('');
  const [isGeneratingSP, setIsGeneratingSP] = useState(false);
  const [spError, setSpError] = useState('');
  const [studyPacks, setStudyPacks] = useState([]);
  const [activePack, setActivePack] = useState(null);

  // Fetch documents and flashcard decks on mount
  useEffect(() => {
    fetchDocuments();
    fetchDecks();
    fetchStudyPacks();
  }, []);

  const fetchStudyPacks = async () => {
    try {
      const response = await axios.get(`${API_URL}/study-tools/packs`);
      setStudyPacks(response.data || []);
      if (response.data && response.data.length > 0) {
        setActivePack(response.data[0]);
      }
    } catch (err) {
      console.error("Failed to load study packs:", err);
    }
  };

  const fetchDocuments = async () => {
    try {
      const response = await axios.get(`${API_URL}/documents`);
      // Filter only completed/indexed documents
      const indexedDocs = (response.data || []).filter(d => 
        ['INDEXED', 'EMBEDDED', 'Completed'].includes(d.status)
      );
      setDocuments(indexedDocs);
      if (indexedDocs.length > 0) {
        setSelectedDocIdForFC(indexedDocs[0].id.toString());
        setSelectedDocIdForMCQ(indexedDocs[0].id.toString());
        setSelectedDocIdForMM(indexedDocs[0].id.toString());
        setSelectedDocIdForSP(indexedDocs[0].id.toString());
      }
    } catch (err) {
      console.error("Failed to load documents:", err);
    } finally {
      setIsLoadingDocs(false);
    }
  };

  const fetchDecks = async () => {
    try {
      const response = await axios.get(`${API_URL}/study-tools/flashcards`);
      setDecks(response.data || []);
      if (response.data && response.data.length > 0 && !selectedDeckId) {
        setSelectedDeckId(response.data[0].id);
      }
    } catch (err) {
      console.error("Failed to load flashcard decks:", err);
    }
  };

  // ----------------------------------------------------
  // FLASHCARD ACTIONS
  // ----------------------------------------------------
  const handleGenerateFlashcards = async () => {
    if (!selectedDocIdForFC) return;
    setIsGeneratingFC(true);
    setFcError('');
    try {
      const response = await axios.post(`${API_URL}/study-tools/flashcards/generate`, {
        document_id: parseInt(selectedDocIdForFC)
      });
      setDecks(prev => [response.data, ...prev]);
      setSelectedDeckId(response.data.id);
      setCurrentCardIndex(0);
      setIsFlipped(false);
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Failed to generate flashcards.';
      setFcError(errMsg);
    } finally {
      setIsGeneratingFC(false);
    }
  };

  const handleDeleteDeck = async (deckId, e) => {
    e.stopPropagation();
    if (!window.confirm("Are you sure you want to delete this flashcard deck?")) return;
    try {
      await axios.delete(`${API_URL}/study-tools/flashcards/${deckId}`);
      setDecks(prev => prev.filter(d => d.id !== deckId));
      if (selectedDeckId === deckId) {
        const remaining = decks.filter(d => d.id !== deckId);
        setSelectedDeckId(remaining.length > 0 ? remaining[0].id : null);
        setCurrentCardIndex(0);
        setIsFlipped(false);
      }
    } catch (err) {
      console.error("Failed to delete deck:", err);
    }
  };

  const handleExportDeck = (deck) => {
    if (!deck) return;
    const dataStr = "data:text/json;charset=utf-8," + encodeURIComponent(JSON.stringify(deck, null, 2));
    const downloadAnchor = document.createElement('a');
    downloadAnchor.setAttribute("href", dataStr);
    downloadAnchor.setAttribute("download", `deck_${deck.id}_export.json`);
    document.body.appendChild(downloadAnchor);
    downloadAnchor.click();
    downloadAnchor.remove();
  };

  const selectedDeck = decks.find(d => d.id === selectedDeckId);

  const handleNextFC = () => {
    if (!selectedDeck) return;
    setIsFlipped(false);
    setTimeout(() => {
      setCurrentCardIndex(prev => (prev + 1) % selectedDeck.cards.length);
    }, 150);
  };

  const handlePrevFC = () => {
    if (!selectedDeck) return;
    setIsFlipped(false);
    setTimeout(() => {
      setCurrentCardIndex(prev => (prev - 1 + selectedDeck.cards.length) % selectedDeck.cards.length);
    }, 150);
  };

  // Keyboard navigation for Flashcards
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (activeTab !== 'flashcards' || !selectedDeck || selectedDeck.cards.length === 0) return;
      if (e.key === ' ' || e.key === 'Enter') {
        e.preventDefault();
        setIsFlipped(prev => !prev);
      } else if (e.key === 'ArrowLeft') {
        handlePrevFC();
      } else if (e.key === 'ArrowRight') {
        handleNextFC();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [activeTab, selectedDeckId, currentCardIndex]);

  // ----------------------------------------------------
  // MCQ ACTIONS
  // ----------------------------------------------------
  const handleGenerateMCQ = async () => {
    if (!selectedDocIdForMCQ) return;
    setIsGeneratingMCQ(true);
    setMcqError('');
    setMcqs([]);
    setQuizStarted(false);
    setQuizComplete(false);
    try {
      const response = await axios.post(`${API_URL}/study-tools/mcqs/generate`, {
        document_id: parseInt(selectedDocIdForMCQ),
        difficulty: mcqDifficulty,
        count: mcqCount
      });
      setMcqs(response.data.mcqs || []);
      setQuizStarted(true);
      setCurrentQuestionIndex(0);
      setSelectedOption(null);
      setAnswerChecked(false);
      setQuizScore(0);
      setQuizHistory([]);
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Failed to generate MCQs.';
      setMcqError(errMsg);
    } finally {
      setIsGeneratingMCQ(false);
    }
  };

  const handleOptionSelect = (optionLetter) => {
    if (answerChecked) return;
    setSelectedOption(optionLetter);
  };

  const handleCheckAnswer = () => {
    if (!selectedOption || answerChecked) return;
    
    const currentQuestion = mcqs[currentQuestionIndex];
    const isCorrect = selectedOption === currentQuestion.correct_answer;
    
    if (isCorrect) {
      setQuizScore(prev => prev + 1);
    }
    
    setQuizHistory(prev => [...prev, {
      questionIndex: currentQuestionIndex,
      selected: selectedOption,
      correct: currentQuestion.correct_answer,
      isCorrect
    }]);
    
    setAnswerChecked(true);
  };

  const handleNextMCQ = () => {
    if (currentQuestionIndex < mcqs.length - 1) {
      setCurrentQuestionIndex(prev => prev + 1);
      setSelectedOption(null);
      setAnswerChecked(false);
    } else {
      setQuizComplete(true);
    }
  };

  const resetQuiz = () => {
    setQuizStarted(false);
    setQuizComplete(false);
    setMcqs([]);
    setSelectedOption(null);
    setAnswerChecked(false);
  };

  // ----------------------------------------------------
  // MIND MAP ACTIONS & LOGIC
  // ----------------------------------------------------
  const handleGenerateMindMap = async () => {
    if (!selectedDocIdForMM) return;
    setIsGeneratingMM(true);
    setMmError('');
    setMindmap(null);
    setCollapsedNodes(new Set());
    setZoom(1);
    setPan({ x: 0, y: 0 });
    try {
      const response = await axios.post(`${API_URL}/study-tools/mindmaps/generate`, {
        document_id: parseInt(selectedDocIdForMM)
      });
      setMindmap(response.data);
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Failed to generate mind map.';
      setMmError(errMsg);
    } finally {
      setIsGeneratingMM(false);
    }
  };

  const toggleNodeCollapse = (nodeId) => {
    setCollapsedNodes(prev => {
      const next = new Set(prev);
      if (next.has(nodeId)) {
        next.delete(nodeId);
      } else {
        next.add(nodeId);
      }
      return next;
    });
  };

  // Zoom / Pan Handlers
  const handleMouseDown = (e) => {
    if (e.button !== 0) return; // Left click only
    setIsDragging(true);
    setDragStart({ x: e.clientX - pan.x, y: e.clientY - pan.y });
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    setPan({ x: e.clientX - dragStart.x, y: e.clientY - dragStart.y });
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleZoom = (factor) => {
    setZoom(prev => Math.min(Math.max(prev * factor, 0.4), 2.5));
  };

  const resetView = () => {
    setZoom(1);
    setPan({ x: 0, y: 0 });
  };

  // Export Mindmap
  const handleExportMindMap = (mm) => {
    if (!mm) return;
    const blob = new Blob([JSON.stringify(mm, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${mm.title.toLowerCase().replace(/\s+/g, '_')}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // Tree layout algorithm
  const layoutTree = (rootNode, collapsedSet) => {
    if (!rootNode) return { nodes: [], edges: [] };

    const nodes = [];
    const edges = [];

    const levelWidth = 260; // horizontal spacing between levels
    const leafSpacing = 90; // spacing between leaves

    const getSubtreeHeight = (node) => {
      if (collapsedSet.has(node.id) || !node.children || node.children.length === 0) {
        return 1;
      }
      return node.children.reduce((acc, child) => acc + getSubtreeHeight(child), 0);
    };

    const assignCoordinates = (node, depth, yStart) => {
      const subtreeHeight = getSubtreeHeight(node);
      const totalHeight = subtreeHeight * leafSpacing;
      const y = yStart + totalHeight / 2 - leafSpacing / 2;
      const x = depth * levelWidth + 40;

      const nodeData = {
        id: node.id,
        label: node.label,
        description: node.description,
        depth,
        x,
        y,
        isCollapsed: collapsedSet.has(node.id),
        hasChildren: node.children && node.children.length > 0
      };
      nodes.push(nodeData);

      if (!collapsedSet.has(node.id) && node.children && node.children.length > 0) {
        let currentYStart = yStart;
        node.children.forEach((child) => {
          const childHeight = getSubtreeHeight(child) * leafSpacing;
          const childCoords = assignCoordinates(child, depth + 1, currentYStart);
          edges.push({
            id: `${node.id}->${child.id}`,
            source: { x, y },
            target: { x: childCoords.x, y: childCoords.y },
            sourceId: node.id,
            targetId: child.id
          });
          currentYStart += childHeight;
        });
      }

      return { x, y };
    };

    assignCoordinates(rootNode, 0, 40);
    return { nodes, edges };
  };

  const handleGenerateStudyPack = async () => {
    if (!selectedDocIdForSP) return;
    setIsGeneratingSP(true);
    setSpError('');
    try {
      const response = await axios.post(`${API_URL}/study-tools/packs/generate`, {
        document_id: parseInt(selectedDocIdForSP)
      });
      await fetchStudyPacks();
      setActivePack(response.data);
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Failed to generate study pack.';
      setSpError(errMsg);
    } finally {
      setIsGeneratingSP(false);
    }
  };

  const handleDownloadPDF = async (pack) => {
    try {
      const response = await axios.get(`${API_URL}/study-tools/packs/${pack.id}/pdf`, {
        responseType: 'blob'
      });
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${pack.title.replace(/\s+/g, '_')}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download PDF:", err);
      alert("Failed to download PDF pack.");
    }
  };

  const handleDownloadZIP = async (pack) => {
    try {
      const response = await axios.get(`${API_URL}/study-tools/packs/${pack.id}/zip`, {
        responseType: 'blob'
      });
      const blob = new Blob([response.data], { type: 'application/zip' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `${pack.title.replace(/\s+/g, '_')}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download ZIP:", err);
      alert("Failed to download ZIP pack.");
    }
  };

  return (
    <div className="space-y-6 font-sans">
      
      {/* Header Panel */}
      <div className="border border-[#E5DDD0] bg-[#FCFAF6] rounded-2xl p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-4 shadow-sm">
        <div className="space-y-1">
          <div className="inline-flex items-center space-x-1.5 bg-[#F8F4EC] border border-[#E5DDD0] text-zinc-650 font-bold px-3 py-1 rounded-full text-[9px] uppercase tracking-wider">
            <GraduationCap size={10} className="text-zinc-655" />
            <span>Interactive Learning Space</span>
          </div>
          <h2 className="text-lg font-bold text-[#111111] tracking-tight font-bevellier">Study Tools</h2>
          <p className="text-[#666666] text-xs max-w-2xl leading-relaxed font-sans">
            Boost your retention. Instantly generate flashcards, create custom difficulty multiple-choice quizzes, and review structural concepts directly from your parsed documents.
          </p>
        </div>
      </div>

      {/* Tabs Selector Bar */}
      <div className="border border-[#E5DDD0] bg-[#FCFAF6] rounded-2xl p-1.5 flex shadow-sm">
        {[
          { id: 'flashcards', label: 'Flash Cards', icon: BookOpen },
          { id: 'mcqs', label: 'MCQ Generator', icon: HelpIcon },
          { id: 'mindmaps', label: 'Mind Maps', icon: Map },
          { id: 'studypacks', label: 'Study Packs', icon: FileText }
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id);
                setFcError('');
                setMcqError('');
                setSpError('');
              }}
              className={`flex-1 flex items-center justify-center space-x-2 py-2.5 rounded-xl text-xs font-bold transition-all duration-200 cursor-pointer ${
                isActive 
                  ? 'bg-[#111111] text-white shadow-sm'
                  : 'text-zinc-655 hover:text-[#111111] hover:bg-[#F8F4EC]/60'
              }`}
            >
              <Icon size={14} />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* ---------------------------------------------------- */}
      {/* FLASHCARDS VIEW */}
      {/* ---------------------------------------------------- */}
      {activeTab === 'flashcards' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          {/* Generation Widget / Decks Sidebar */}
          <div className="lg:col-span-4 space-y-4">
            {/* Generation Panel */}
            <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-5 shadow-sm space-y-4">
              <div>
                <h3 className="text-[10px] font-bold text-[#111111] uppercase tracking-wider">Generate Decks</h3>
                <p className="text-[10.5px] text-[#666666] mt-1 leading-relaxed">
                  Generate high-retention Q&A pairs for active recall.
                </p>
              </div>

              {isLoadingDocs ? (
                <div className="py-4 flex justify-center">
                  <Loader2 size={16} className="animate-spin text-zinc-400" />
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center p-4 border border-dashed border-[#E5DDD0] rounded-xl bg-[#FCFAF6]/60">
                  <p className="text-[10.5px] font-semibold text-zinc-500">No indexed documents available.</p>
                  <p className="text-[9px] text-zinc-400 mt-0.5">Please upload and index documents first.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="space-y-1">
                    <label className="text-[9.5px] font-bold text-zinc-450 uppercase tracking-wider">Select Source</label>
                    <div className="relative">
                      <select
                        value={selectedDocIdForFC}
                        onChange={(e) => setSelectedDocIdForFC(e.target.value)}
                        className="w-full bg-white border border-[#E5DDD0] rounded-xl px-3 py-2 text-xs text-[#111111] focus:outline-none focus:border-zinc-400 cursor-pointer appearance-none pr-8 font-medium"
                      >
                        {documents.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name.length > 30 ? d.name.slice(0, 27) + '...' : d.name}
                          </option>
                        ))}
                      </select>
                      <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-450 pointer-events-none" />
                    </div>
                  </div>

                  <button
                    onClick={handleGenerateFlashcards}
                    disabled={isGeneratingFC || !selectedDocIdForFC}
                    className="w-full py-2.5 px-4 bg-[#111111] hover:bg-zinc-800 disabled:bg-[#F8F4EC] disabled:text-zinc-400 text-white rounded-xl text-xs font-bold transition-all shadow-sm flex items-center justify-center space-x-2 cursor-pointer btn-press-active"
                  >
                    {isGeneratingFC ? (
                      <>
                        <Loader2 size={13} className="animate-spin" />
                        <span>Generating Cards...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles size={13} />
                        <span>Generate Flashcards</span>
                      </>
                    )}
                  </button>
                </div>
              )}

              {fcError && (
                <div className="flex items-start space-x-2 p-3 bg-rose-50/60 border border-rose-200 rounded-xl">
                  <AlertCircle className="text-rose-700 shrink-0 mt-0.5" size={13} />
                  <span className="text-[9.5px] text-rose-750 font-semibold leading-relaxed">{fcError}</span>
                </div>
              )}
            </div>

            {/* History Decks Panel */}
            <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-5 shadow-sm space-y-3">
              <h3 className="text-[10px] font-bold text-[#111111] uppercase tracking-wider">Your Decks ({decks.length})</h3>
              
              {decks.length === 0 ? (
                <p className="text-[10.5px] text-zinc-400 italic py-2 text-center">No generated decks found.</p>
              ) : (
                <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1 hide-scrollbar">
                  {decks.map((deck) => {
                    const isSelected = selectedDeckId === deck.id;
                    return (
                      <div
                        key={deck.id}
                        onClick={() => {
                          setSelectedDeckId(deck.id);
                          setCurrentCardIndex(0);
                          setIsFlipped(false);
                        }}
                        className={`group p-3 border rounded-xl flex items-center justify-between cursor-pointer transition-all duration-200 ${
                          isSelected 
                            ? 'bg-white border-[#E5DDD0] shadow-sm font-bold' 
                            : 'bg-[#FCFAF6]/60 hover:bg-white border-[#E5DDD0]/60 text-zinc-655'
                        }`}
                      >
                        <div className="flex items-center space-x-2 overflow-hidden flex-1 mr-2">
                          <FileText size={12} className="text-zinc-450 shrink-0" />
                          <span className="text-[11px] font-bold text-[#111111] truncate" title={deck.title}>
                            {deck.title.replace('Flashcards: ', '')}
                          </span>
                        </div>
                        <div className="flex items-center space-x-1 shrink-0">
                          <span className="text-[9px] bg-[#F8F4EC] border border-[#E5DDD0] text-[#111111] font-bold px-1.5 py-0.5 rounded-full">
                            {deck.cards?.length || 0}
                          </span>
                          <button
                            onClick={(e) => handleDeleteDeck(deck.id, e)}
                            className="p-1 hover:bg-rose-50 hover:text-rose-600 rounded-lg text-zinc-400 transition-colors opacity-0 group-hover:opacity-100 focus:opacity-100"
                            title="Delete Deck"
                          >
                            <Trash2 size={11} />
                          </button>
                        </div>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Flashcard Slider Box */}
          <div className="lg:col-span-8">
            <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-6 shadow-sm flex flex-col items-center justify-between min-h-[460px] h-full">
              {!selectedDeck ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center max-w-sm py-16">
                  <div className="p-4 bg-[#F8F4EC] border border-[#E5DDD0] rounded-xl text-zinc-400 mb-3">
                    <BookOpen size={24} />
                  </div>
                  <h4 className="text-xs font-bold text-[#111111]">No Active Deck</h4>
                  <p className="text-[10.5px] text-[#666666] mt-1 leading-relaxed">
                    Select a document on the left and generate flashcards, or select an existing deck from your history to study.
                  </p>
                </div>
              ) : selectedDeck.cards.length === 0 ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center py-16">
                  <p className="text-xs text-zinc-400 font-medium italic">This deck has no cards.</p>
                </div>
              ) : (
                <>
                  {/* Top Deck Info Actions */}
                  <div className="w-full flex items-center justify-between border-b border-[#E5DDD0] pb-3 mb-6">
                    <div>
                      <h4 className="text-xs font-bold text-[#111111] truncate max-w-[300px]" title={selectedDeck.title}>
                        {selectedDeck.title}
                      </h4>
                      <p className="text-[9px] text-[#666666] font-bold uppercase mt-0.5">
                        Card {currentCardIndex + 1} of {selectedDeck.cards.length}
                      </p>
                    </div>
                    <button
                      onClick={() => handleExportDeck(selectedDeck)}
                      className="inline-flex items-center space-x-1.5 text-[9.5px] font-bold text-zinc-650 bg-white hover:bg-[#F8F4EC] border border-[#E5DDD0] px-3 py-1.5 rounded-xl transition-all cursor-pointer shadow-sm"
                      title="Download Deck as JSON"
                    >
                      <Download size={11} />
                      <span>Export Deck</span>
                    </button>
                  </div>

                  {/* 3D Flipped Card Body */}
                  <div className="flex-1 w-full flex items-center justify-center px-4 md:px-12 py-4">
                    <div 
                      className="w-full max-w-lg h-64 cursor-pointer"
                      style={{ perspective: '1200px' }}
                      onClick={() => setIsFlipped(prev => !prev)}
                    >
                      <motion.div
                        className="w-full h-full relative"
                        style={{ transformStyle: 'preserve-3d' }}
                        animate={{ rotateY: isFlipped ? 180 : 0 }}
                        transition={{ duration: 0.4, ease: 'easeInOut' }}
                      >
                        {/* Front Side: Question */}
                        <div 
                          className="absolute inset-0 bg-white border border-[#E5DDD0] rounded-xl p-6 flex flex-col justify-between shadow-sm hover:shadow-md transition-shadow select-none"
                          style={{ backfaceVisibility: 'hidden' }}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] bg-sky-50 text-sky-700 font-bold px-2.5 py-0.5 rounded-full border border-sky-100">
                              QUESTION
                            </span>
                            <span className="text-[9px] text-zinc-450 font-bold tracking-wider">
                              CLICK OR SPACEBAR TO REVEAL
                            </span>
                          </div>
                          <div className="flex-1 flex items-center justify-center text-center px-4 my-3">
                            <p className="text-sm font-bold text-[#111111] leading-relaxed">
                              {selectedDeck.cards[currentCardIndex].question}
                            </p>
                          </div>
                          <div className="flex justify-center">
                            <span className="text-[8px] font-bold text-zinc-400 uppercase tracking-widest flex items-center space-x-1">
                              <RotateCw size={8} />
                              <span>Flip Card</span>
                            </span>
                          </div>
                        </div>

                        {/* Back Side: Answer */}
                        <div 
                          className="absolute inset-0 bg-[#F8F4EC]/65 border border-[#E5DDD0] rounded-xl p-6 flex flex-col justify-between shadow-sm select-text"
                          style={{ backfaceVisibility: 'hidden', transform: 'rotateY(180deg)' }}
                        >
                          <div className="flex items-center justify-between">
                            <span className="text-[9px] bg-emerald-50 text-emerald-700 font-bold px-2.5 py-0.5 rounded-full border border-emerald-100">
                              ANSWER
                            </span>
                            <span className="text-[9px] text-zinc-450 font-bold tracking-wider">
                              CLICK OR SPACEBAR TO FLIP BACK
                            </span>
                          </div>
                          <div className="flex-1 flex items-center justify-center text-center overflow-y-auto px-4 my-3 scrollbar-none">
                            <p className="text-xs font-semibold text-zinc-800 leading-relaxed max-h-40">
                              {selectedDeck.cards[currentCardIndex].answer}
                            </p>
                          </div>
                          <div className="flex justify-center">
                            <span className="text-[8px] font-bold text-zinc-400 uppercase tracking-widest flex items-center space-x-1 select-none">
                              <RotateCw size={8} />
                              <span>Flip Card</span>
                            </span>
                          </div>
                        </div>
                      </motion.div>
                    </div>
                  </div>

                  {/* Navigation Slider Buttons */}
                  <div className="w-full flex items-center justify-between border-t border-[#E5DDD0] pt-5 mt-6">
                    <button
                      onClick={handlePrevFC}
                      className="inline-flex items-center space-x-1 px-3 py-2 border border-[#E5DDD0] hover:bg-[#F8F4EC]/60 bg-white rounded-xl text-xs font-bold text-zinc-650 cursor-pointer transition-all btn-press-active shadow-sm"
                    >
                      <ChevronLeft size={14} />
                      <span>Prev</span>
                    </button>

                    <div className="text-[10px] text-zinc-400 font-bold uppercase tracking-widest hidden sm:block">
                      Use Arrow Keys ← → to navigate
                    </div>

                    <button
                      onClick={handleNextFC}
                      className="inline-flex items-center space-x-1 px-3 py-2 border border-[#E5DDD0] hover:bg-[#F8F4EC]/60 bg-white rounded-xl text-xs font-bold text-zinc-650 cursor-pointer transition-all btn-press-active shadow-sm"
                    >
                      <span>Next</span>
                      <ChevronRight size={14} />
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ---------------------------------------------------- */}
      {/* MCQ GENERATOR VIEW */}
      {/* ---------------------------------------------------- */}
      {activeTab === 'mcqs' && (
        <div className="space-y-6">
          {!quizStarted ? (
            /* MCQ Settings Menu Dashboard */
            <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-6 shadow-sm max-w-xl mx-auto space-y-6">
              <div className="text-center space-y-1 pb-4 border-b border-[#E5DDD0]">
                <div className="p-3 bg-[#F8F4EC] border border-[#E5DDD0] rounded-xl inline-flex text-[#111111] mb-2 animate-fade-in">
                  <HelpIcon size={22} />
                </div>
                <h3 className="text-sm font-bold text-[#111111] font-bevellier">Generate MCQ Quiz</h3>
                <p className="text-xs text-zinc-550 max-w-sm mx-auto leading-relaxed">
                  Select a document and difficulty configuration to compile a dynamic multiple choice assessment.
                </p>
              </div>

              {isLoadingDocs ? (
                <div className="py-8 flex justify-center">
                  <Loader2 size={20} className="animate-spin text-zinc-400" />
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center p-6 border border-dashed border-[#E5DDD0] rounded-xl bg-[#FCFAF6]/60">
                  <p className="text-xs font-bold text-zinc-505">No indexed documents available.</p>
                  <p className="text-[10.5px] text-zinc-450 mt-1">Upload files in your Ingestion Workspace to begin.</p>
                </div>
              ) : (
                <div className="space-y-4">
                  {/* Document Selector */}
                  <div className="space-y-1">
                    <label className="text-[9.5px] font-bold text-zinc-450 uppercase tracking-wider">Select Document Context</label>
                    <div className="relative">
                      <select
                        value={selectedDocIdForMCQ}
                        onChange={(e) => setSelectedDocIdForMCQ(e.target.value)}
                        className="w-full bg-white border border-[#E5DDD0] rounded-xl px-3.5 py-2.5 text-xs text-[#111111] focus:outline-none focus:border-zinc-400 cursor-pointer appearance-none pr-8 font-semibold"
                      >
                        {documents.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name}
                          </option>
                        ))}
                      </select>
                      <ChevronDown size={14} className="absolute right-3.5 top-1/2 -translate-y-1/2 text-zinc-450 pointer-events-none" />
                    </div>
                  </div>

                  {/* Difficulty selector tabs */}
                  <div className="space-y-1.5">
                    <label className="text-[9.5px] font-bold text-zinc-450 uppercase tracking-wider block">Target Difficulty</label>
                    <div className="flex border border-[#E5DDD0] p-1 bg-[#F8F4EC]/60 rounded-xl">
                      {['Easy', 'Medium', 'Hard'].map((diff) => {
                        const isSelected = mcqDifficulty === diff;
                        return (
                          <button
                            key={diff}
                            type="button"
                            onClick={() => setMcqDifficulty(diff)}
                            className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                              isSelected 
                                ? 'bg-white text-[#111111] border border-[#E5DDD0] shadow-sm'
                                : 'text-zinc-650 hover:text-[#111111]'
                            }`}
                          >
                            {diff}
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Question Count */}
                  <div className="space-y-1.5">
                    <label className="text-[9.5px] font-bold text-zinc-450 uppercase tracking-wider block">Number of Questions</label>
                    <div className="flex border border-[#E5DDD0] p-1 bg-[#F8F4EC]/60 rounded-xl">
                      {[5, 10, 15].map((cnt) => {
                        const isSelected = mcqCount === cnt;
                        return (
                          <button
                            key={cnt}
                            type="button"
                            onClick={() => setMcqCount(cnt)}
                            className={`flex-1 py-1.5 text-xs font-bold rounded-lg transition-all cursor-pointer ${
                              isSelected 
                                ? 'bg-white text-[#111111] border border-[#E5DDD0] shadow-sm'
                                : 'text-zinc-655 hover:text-[#111111]'
                            }`}
                          >
                            {cnt} Questions
                          </button>
                        );
                      })}
                    </div>
                  </div>

                  {/* Submit Trigger */}
                  <button
                    onClick={handleGenerateMCQ}
                    disabled={isGeneratingMCQ || !selectedDocIdForMCQ}
                    className="w-full mt-2 py-3 px-4 bg-[#111111] hover:bg-zinc-800 disabled:bg-[#F8F4EC] disabled:text-zinc-400 text-white rounded-xl text-xs font-bold transition-all shadow-sm flex items-center justify-center space-x-2 cursor-pointer btn-press-active"
                  >
                    {isGeneratingMCQ ? (
                      <>
                        <Loader2 size={14} className="animate-spin" />
                        <span>Analyzing context & composing questions...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles size={14} />
                        <span>Generate Quiz Console</span>
                      </>
                    )}
                  </button>
                </div>
              )}

              {mcqError && (
                <div className="flex items-start space-x-2 p-3.5 bg-rose-50/60 border border-rose-205 rounded-xl">
                  <AlertCircle className="text-rose-700 shrink-0 mt-0.5" size={13} />
                  <span className="text-[10px] text-rose-750 font-semibold leading-relaxed">{mcqError}</span>
                </div>
              )}
            </div>
          ) : quizComplete ? (
            /* Score Results Dashboard Screen */
            <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-6 shadow-sm max-w-xl mx-auto space-y-6 animate-fade-in">
              <div className="text-center space-y-2 pb-5 border-b border-[#E5DDD0]">
                <div className="h-16 w-16 bg-[#FACC15]/10 border border-[#FACC15]/20 rounded-full flex items-center justify-center text-[#FACC15] mx-auto animate-bounce">
                  <Trophy size={28} className="stroke-[2]" />
                </div>
                <h3 className="text-base font-extrabold text-[#111111] font-bevellier">Quiz Completed!</h3>
                <p className="text-xs text-zinc-550 font-medium">Here is your summary breakdown</p>
              </div>

              {/* Stats dashboard grid */}
              <div className="grid grid-cols-2 gap-4">
                <div className="border border-[#E5DDD0] rounded-xl p-4 bg-white text-center space-y-1 shadow-sm">
                  <span className="text-[9px] font-bold text-zinc-450 uppercase tracking-widest">Final Score</span>
                  <p className="text-2xl font-extrabold text-[#111111]">{quizScore} / {mcqs.length}</p>
                </div>
                <div className="border border-[#E5DDD0] rounded-xl p-4 bg-white text-center space-y-1 shadow-sm">
                  <span className="text-[9px] font-bold text-zinc-450 uppercase tracking-widest">Success Rate</span>
                  <p className="text-2xl font-extrabold text-[#10b981]">{Math.round((quizScore / mcqs.length) * 100)}%</p>
                </div>
              </div>

              {/* Question review accordion */}
              <div className="space-y-4 pt-2">
                <h4 className="text-[10px] font-bold text-[#666666] uppercase tracking-wider">Review Questions</h4>
                <div className="space-y-3 max-h-[300px] overflow-y-auto pr-1 hide-scrollbar">
                  {mcqs.map((q, idx) => {
                    const hist = quizHistory.find(h => h.questionIndex === idx) || {};
                    return (
                      <div key={idx} className="p-4 border border-[#E5DDD0] rounded-xl bg-white space-y-2 shadow-sm">
                        <div className="flex items-start justify-between gap-2">
                          <p className="text-xs font-bold text-[#111111] leading-relaxed flex-1">
                            {idx + 1}. {q.question}
                          </p>
                          <span className={`inline-flex p-1 rounded-full shrink-0 ${
                            hist.isCorrect 
                              ? 'bg-[#A8D5F2]/20 text-sky-800 border border-[#A8D5F2]/40'
                              : 'bg-rose-50 text-rose-700 border border-rose-100'
                          }`}>
                            {hist.isCorrect ? <Check size={11} className="stroke-[3]" /> : <XIcon size={11} className="stroke-[3]" />}
                          </span>
                        </div>
                        <div className="text-[10px] text-zinc-550 font-semibold space-y-1">
                          <p>Your answer: <span className={hist.isCorrect ? "text-emerald-700 font-bold" : "text-rose-600 font-bold"}>{hist.selected}</span></p>
                          <p>Correct answer: <span className="text-emerald-700 font-extrabold">{hist.correct}</span></p>
                        </div>
                        <div className="text-[10px] leading-relaxed text-[#666666] bg-[#FCFAF6] border border-[#E5DDD0] p-2.5 rounded-lg">
                          <span className="font-bold text-[#111111] block mb-0.5">Explanation:</span>
                          {q.explanation}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>

              <div className="flex space-x-3 pt-3">
                <button
                  onClick={resetQuiz}
                  className="flex-1 py-2.5 border border-[#E5DDD0] hover:bg-[#F8F4EC]/60 bg-white rounded-xl text-xs font-bold text-zinc-650 transition-all cursor-pointer shadow-sm text-center btn-press-active"
                >
                  Configure New Quiz
                </button>
                <button
                  onClick={handleGenerateMCQ}
                  className="flex-1 py-2.5 bg-[#111111] hover:bg-zinc-800 rounded-xl text-xs font-bold text-white transition-all cursor-pointer shadow-sm text-center flex items-center justify-center space-x-1.5 btn-press-active"
                >
                  <RefreshCw size={12} />
                  <span>Restart Same Quiz</span>
                </button>
              </div>
            </div>
          ) : (
            /* Multi-step Quiz active view */
            <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-6 shadow-sm max-w-xl mx-auto space-y-6 animate-fade-in">
              {/* Quiz Header & Progress */}
              <div className="space-y-3.5">
                <div className="flex items-center justify-between">
                  <div>
                    <span className="text-[8.5px] bg-[#F8F4EC] text-zinc-750 font-bold px-2 py-0.5 rounded-md border border-[#E5DDD0]">
                      DIFFICULTY: {mcqDifficulty.toUpperCase()}
                    </span>
                  </div>
                  <span className="text-[10px] text-zinc-450 font-bold uppercase tracking-wider">
                    Question {currentQuestionIndex + 1} of {mcqs.length}
                  </span>
                </div>

                {/* Progress bar */}
                <div className="w-full bg-[#E5DDD0] h-1.5 rounded-full overflow-hidden">
                  <div 
                    className="bg-[#111111] h-full rounded-full transition-all duration-300"
                    style={{ width: `${((currentQuestionIndex + (answerChecked ? 1 : 0)) / mcqs.length) * 100}%` }}
                  ></div>
                </div>
              </div>

              {/* Question String */}
              <div className="py-2">
                <h3 className="text-sm font-extrabold text-[#111111] leading-relaxed">
                  {mcqs[currentQuestionIndex].question}
                </h3>
              </div>

              {/* Interactive Options Cards list */}
              <div className="space-y-2.5">
                {mcqs[currentQuestionIndex].options.map((option) => {
                  const letter = option.trim().charAt(0); // A, B, C, or D
                  const isSelected = selectedOption === letter;
                  
                  // Styling states post checking answer
                  let optionClass = "border-[#E5DDD0] hover:border-zinc-400 bg-white hover:bg-[#F8F4EC]/40";
                  let badgeIcon = null;

                  if (answerChecked) {
                    const isCorrectOption = letter === mcqs[currentQuestionIndex].correct_answer;
                    if (isSelected) {
                      if (isCorrectOption) {
                        optionClass = "border-emerald-500 bg-emerald-50/30 text-emerald-900 shadow-xs";
                        badgeIcon = <Check size={11} className="text-emerald-700 font-bold" />;
                      } else {
                        optionClass = "border-rose-350 bg-rose-50/30 text-rose-900 shadow-xs";
                        badgeIcon = <XIcon size={11} className="text-rose-700 font-bold" />;
                      }
                    } else if (isCorrectOption) {
                      // Highlight correct option user missed
                      optionClass = "border-emerald-500/50 bg-emerald-50/10 text-emerald-900";
                      badgeIcon = <Check size={11} className="text-emerald-700/60" />;
                    } else {
                      optionClass = "border-[#E5DDD0]/60 bg-zinc-50/10 text-zinc-400 opacity-60";
                    }
                  } else if (isSelected) {
                    optionClass = "border-[#111111] bg-[#111111]/5 text-[#111111] shadow-xs font-bold";
                  }

                  return (
                    <div
                      key={option}
                      onClick={() => handleOptionSelect(letter)}
                      className={`p-3.5 border rounded-xl flex items-center justify-between cursor-pointer transition-all duration-200 ${optionClass}`}
                    >
                      <span className="text-[11.5px] font-semibold flex-1 leading-relaxed mr-2">
                        {option}
                      </span>
                      {badgeIcon && (
                        <span className="p-0.5 bg-white border rounded-full shadow-xs shrink-0">
                          {badgeIcon}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>

              {/* Slide down Explanation Panel */}
              <AnimatePresence>
                {answerChecked && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden"
                  >
                    <div className="p-4 bg-[#FCFAF6] border border-[#E5DDD0] rounded-xl space-y-1.5 animate-fade-in select-text">
                      <span className="text-[9px] font-extrabold uppercase tracking-widest text-[#111111] flex items-center space-x-1">
                        <HelpIcon size={10} className="text-[#666666]" />
                        <span>Tutor Explanation</span>
                      </span>
                      <p className="text-[10.5px] leading-relaxed text-[#666666]">
                        {mcqs[currentQuestionIndex].explanation}
                      </p>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>

              {/* Action Navigation Buttons */}
              <div className="flex justify-between items-center border-t border-[#E5DDD0] pt-5">
                <button
                  onClick={resetQuiz}
                  className="px-4 py-2 border border-[#E5DDD0] hover:bg-rose-50 hover:text-rose-600 hover:border-rose-200 bg-white rounded-xl text-xs font-bold text-zinc-650 transition-all cursor-pointer btn-press-active shadow-sm"
                >
                  Quit Quiz
                </button>

                {!answerChecked ? (
                  <button
                    onClick={handleCheckAnswer}
                    disabled={!selectedOption}
                    className="px-5 py-2.5 bg-[#111111] hover:bg-zinc-800 disabled:bg-[#F8F4EC] disabled:text-zinc-400 text-white rounded-xl text-xs font-bold transition-all shadow-sm cursor-pointer btn-press-active flex items-center space-x-1.5"
                  >
                    <span>Check Answer</span>
                    <ArrowRight size={13} />
                  </button>
                ) : (
                  <button
                    onClick={handleNextMCQ}
                    className="px-5 py-2.5 bg-[#111111] hover:bg-zinc-800 text-white rounded-xl text-xs font-bold transition-all shadow-sm cursor-pointer btn-press-active flex items-center space-x-1.5"
                  >
                    <span>{currentQuestionIndex === mcqs.length - 1 ? 'Show Results' : 'Next Question'}</span>
                    <ArrowRight size={13} />
                  </button>
                )}
              </div>
            </div>
          )}
        </div>
      )}
      {/* ---------------------------------------------------- */}
      {/* MIND MAPS VIEW */}
      {/* ---------------------------------------------------- */}
      {activeTab === 'mindmaps' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-fade-in">
          {/* Document Ingestion & Generator Sidebar */}
          <div className="lg:col-span-4 space-y-4">
            <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-5 shadow-sm space-y-4">
              <div>
                <h3 className="text-[10px] font-bold text-[#111111] uppercase tracking-wider">Mind Map Generator</h3>
                <p className="text-[10.5px] text-[#666666] mt-1 leading-relaxed">
                  Synthesize the document text into a hierarchical, interactive study map.
                </p>
              </div>

              {isLoadingDocs ? (
                <div className="py-4 flex justify-center">
                  <Loader2 size={16} className="animate-spin text-zinc-400" />
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center p-4 border border-dashed border-[#E5DDD0] rounded-xl bg-[#FCFAF6]/60">
                  <p className="text-[10.5px] font-semibold text-zinc-500">No indexed documents available.</p>
                  <p className="text-[9px] text-zinc-400 mt-0.5">Please upload and index documents first.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="space-y-1">
                    <label className="text-[9.5px] font-bold text-zinc-450 uppercase tracking-wider">Select Source</label>
                    <div className="relative">
                      <select
                        value={selectedDocIdForMM}
                        onChange={(e) => setSelectedDocIdForMM(e.target.value)}
                        className="w-full bg-white border border-[#E5DDD0] rounded-xl px-3 py-2 text-xs text-[#111111] focus:outline-none focus:border-zinc-400 cursor-pointer appearance-none pr-8 font-medium"
                      >
                        {documents.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name.length > 30 ? d.name.slice(0, 27) + '...' : d.name}
                          </option>
                        ))}
                      </select>
                      <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-450 pointer-events-none" />
                    </div>
                  </div>

                  <button
                    onClick={handleGenerateMindMap}
                    disabled={isGeneratingMM || !selectedDocIdForMM}
                    className="w-full py-2.5 px-4 bg-[#111111] hover:bg-zinc-800 disabled:bg-[#F8F4EC] disabled:text-zinc-400 text-white rounded-xl text-xs font-bold transition-all shadow-sm flex items-center justify-center space-x-2 cursor-pointer btn-press-active"
                  >
                    {isGeneratingMM ? (
                      <>
                        <Loader2 size={13} className="animate-spin" />
                        <span>Structuring Graph...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles size={13} />
                        <span>Generate Mind Map</span>
                      </>
                    )}
                  </button>
                </div>
              )}

              {mmError && (
                <div className="flex items-start space-x-2 p-3 bg-rose-50/60 border border-rose-200 rounded-xl">
                  <AlertCircle className="text-rose-700 shrink-0 mt-0.5" size={13} />
                  <span className="text-[9.5px] text-rose-750 font-semibold leading-relaxed">{mmError}</span>
                </div>
              )}
            </div>

            {/* Quick Tips & Controls Card */}
            {mindmap && (
              <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-5 shadow-sm space-y-3">
                <h4 className="text-[10px] font-bold text-[#111111] uppercase tracking-wider">Navigation Controls</h4>
                <div className="grid grid-cols-3 gap-2">
                  <button 
                    onClick={() => handleZoom(1.2)} 
                    className="py-1.5 border border-[#E5DDD0] hover:bg-[#F8F4EC]/60 bg-white rounded-lg text-[10px] font-bold text-zinc-650 cursor-pointer text-center btn-press-active shadow-sm"
                    title="Zoom In"
                  >
                    🔍 +
                  </button>
                  <button 
                    onClick={() => handleZoom(0.8)} 
                    className="py-1.5 border border-[#E5DDD0] hover:bg-[#F8F4EC]/60 bg-white rounded-lg text-[10px] font-bold text-zinc-650 cursor-pointer text-center btn-press-active shadow-sm"
                    title="Zoom Out"
                  >
                    🔍 -
                  </button>
                  <button 
                    onClick={resetView} 
                    className="py-1.5 border border-[#E5DDD0] hover:bg-[#F8F4EC]/60 bg-white rounded-lg text-[10px] font-bold text-zinc-650 cursor-pointer text-center btn-press-active shadow-sm"
                    title="Reset View"
                  >
                    Reset
                  </button>
                </div>
                <div className="text-[9.5px] text-[#666666] leading-normal space-y-1 pt-1.5">
                  <p>🖱️ <strong>Drag canvas:</strong> Hold left click and move to pan.</p>
                  <p>👆 <strong>Interact:</strong> Click subtopic cards to collapse/expand branches.</p>
                  <p>🧠 <strong>Spaced Recall:</strong> Level-1 nodes represent key themes, Level-2 cards expand with summarized details to study.</p>
                </div>
              </div>
            )}
          </div>

          {/* Interactive Mindmap Canvas Panel */}
          <div className="lg:col-span-8 h-full">
            <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-5 shadow-sm flex flex-col justify-between min-h-[480px] h-full relative overflow-hidden">
              {!mindmap ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center max-w-sm mx-auto py-16">
                  <div className="p-4 bg-[#F8F4EC] border border-[#E5DDD0] rounded-xl text-zinc-400 mb-3">
                    <Map size={24} />
                  </div>
                  <h4 className="text-xs font-bold text-[#111111]">No Active Mind Map</h4>
                  <p className="text-[10.5px] text-[#666666] mt-1 leading-relaxed">
                    Select a document on the left and click generate to visualize structural concepts, connections, and definitions.
                  </p>
                </div>
              ) : (
                <>
                  {/* Top Canvas Header Options */}
                  <div className="flex items-center justify-between border-b border-[#E5DDD0] pb-3 mb-4 z-20">
                    <div>
                      <h4 className="text-xs font-bold text-[#111111] truncate max-w-[280px]">
                        {mindmap.title}
                      </h4>
                      <p className="text-[9px] text-[#666666] font-bold uppercase mt-0.5">
                        Interactive Concept Tree
                      </p>
                    </div>
                    <button
                      onClick={() => handleExportMindMap(mindmap)}
                      className="inline-flex items-center space-x-1.5 text-[9.5px] font-bold text-zinc-650 bg-white hover:bg-[#F8F4EC]/60 border border-[#E5DDD0] px-3 py-1.5 rounded-xl transition-all cursor-pointer shadow-sm"
                      title="Export mindmap schema to JSON file"
                    >
                      <Download size={11} />
                      <span>Export Map</span>
                    </button>
                  </div>

                  {/* Visualizer Canvas Area */}
                  {(() => {
                    const { nodes, edges } = layoutTree(mindmap.root, collapsedNodes);
                    const maxX = Math.max(...nodes.map(n => n.x), 500) + 260;
                    const maxY = Math.max(...nodes.map(n => n.y), 400) + 120;
                    
                    return (
                      <div 
                        onMouseDown={handleMouseDown}
                        onMouseMove={handleMouseMove}
                        onMouseUp={handleMouseUp}
                        onMouseLeave={handleMouseUp}
                        className="flex-1 w-full h-[580px] bg-white border border-[#E5DDD0] rounded-xl overflow-hidden relative cursor-grab active:cursor-grabbing select-none shadow-inner"
                      >
                        {/* Dot Grid Pattern Overlay */}
                        <div className="absolute inset-0 grid-paper opacity-[0.25] pointer-events-none"></div>

                        {/* Scale / Translate Viewport Container */}
                        <div 
                          style={{
                            width: `${maxX}px`,
                            height: `${maxY}px`,
                            transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom})`,
                            transformOrigin: '0 0',
                            transition: isDragging ? 'none' : 'transform 0.15s ease-out',
                            position: 'absolute',
                            inset: 0
                          }}
                        >
                          {/* Connections SVG Layer */}
                          <svg 
                            className="absolute inset-0 w-full h-full pointer-events-none z-0"
                            style={{ width: `${maxX}px`, height: `${maxY}px` }}
                          >
                            <defs>
                              <filter id="shadow" x="-10%" y="-10%" width="120%" height="120%">
                                <feDropShadow dx="0" dy="2" stdDeviation="3" floodOpacity="0.05"/>
                              </filter>
                            </defs>
                            {edges.map((edge) => {
                              const startX = edge.source.x + 190;
                              const startY = edge.source.y + 25;
                              const endX = edge.target.x;
                              const endY = edge.target.y + 25;
                              const controlX = (startX + endX) / 2;
                              return (
                                <g key={edge.id}>
                                  <path 
                                    d={`M ${startX} ${startY} C ${controlX} ${startY}, ${controlX} ${endY}, ${endX} ${endY}`}
                                    stroke="rgba(229, 221, 208, 0.4)"
                                    strokeWidth="4"
                                    fill="none"
                                  />
                                  <path 
                                    d={`M ${startX} ${startY} C ${controlX} ${startY}, ${controlX} ${endY}, ${endX} ${endY}`}
                                    stroke="#a1a1aa"
                                    strokeWidth="2"
                                    fill="none"
                                    strokeDasharray={edge.isCollapsed ? "4 4" : "none"}
                                    className="transition-all duration-300"
                                  />
                                </g>
                              );
                            })}
                          </svg>

                          {/* Nodes DOM Elements Layer */}
                          <div className="absolute inset-0 z-10 pointer-events-none">
                            {nodes.map((node, index) => {
                              const colors = ['border-sky-500 hover:border-sky-600', 'border-indigo-500 hover:border-indigo-600', 'border-emerald-500 hover:border-emerald-600', 'border-amber-500 hover:border-amber-600', 'border-rose-500 hover:border-rose-600'];
                              const borderAccent = colors[index % colors.length];

                              let nodeElement = null;

                              if (node.depth === 0) {
                                nodeElement = (
                                  <div 
                                    className="bg-[#111111] border border-[#111111] text-white rounded-xl w-[190px] min-h-[50px] px-3.5 py-3 shadow-md text-center flex flex-col justify-center select-none"
                                  >
                                    <span className="text-[7.5px] text-zinc-400 font-extrabold uppercase tracking-widest block mb-0.5">Theme Root</span>
                                    <span className="text-[11px] font-extrabold leading-snug tracking-tight text-white">{node.label}</span>
                                  </div>
                                );
                              } else if (node.depth === 1) {
                                nodeElement = (
                                  <div 
                                    onClick={() => toggleNodeCollapse(node.id)}
                                    className={`bg-[#FCFAF6] border border-[#E5DDD0] border-l-4 ${borderAccent} text-[#111111] rounded-xl w-[190px] min-h-[50px] p-3 shadow-sm hover:shadow-md cursor-pointer transition-all duration-200 select-none flex flex-col justify-center`}
                                  >
                                    <div className="flex items-center justify-between">
                                      <span className="text-[10.5px] font-extrabold tracking-tight leading-snug flex-1 truncate pr-1">
                                        {node.label}
                                      </span>
                                      {node.hasChildren && (
                                        <span className="text-[9px] text-zinc-455 font-extrabold border border-[#E5DDD0] rounded px-1.5 py-0.2 select-none bg-white shrink-0">
                                          {node.isCollapsed ? '+' : '−'}
                                        </span>
                                      )}
                                    </div>
                                    {node.description && (
                                      <span className="text-[8.5px] text-[#666666] truncate mt-0.5 font-medium leading-relaxed">
                                        {node.description}
                                      </span>
                                    )}
                                  </div>
                                );
                              } else {
                                nodeElement = (
                                  <div 
                                    className="bg-white border border-[#E5DDD0] text-[#111111] rounded-xl w-[220px] p-3 shadow-sm select-text leading-relaxed flex flex-col justify-center"
                                  >
                                    <span className="text-[9.5px] font-extrabold text-[#111111] leading-snug tracking-tight">
                                      {node.label}
                                    </span>
                                    {node.description && (
                                      <p className="text-[9px] text-[#666666] mt-1 leading-normal font-normal">
                                        {node.description}
                                      </p>
                                    )}
                                  </div>
                                );
                              }

                              return (
                                <div 
                                  key={node.id}
                                  style={{
                                    left: `${node.x}px`,
                                    top: `${node.y}px`,
                                    position: 'absolute'
                                  }}
                                  className="pointer-events-auto transition-all duration-300"
                                >
                                  {nodeElement}
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      </div>
                    );
                  })()}
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {/* ---------------------------------------------------- */}
      {/* STUDY PACKS VIEW */}
      {/* ---------------------------------------------------- */}
      {activeTab === 'studypacks' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 animate-fade-in">
          {/* Generation Widget / Packs Sidebar */}
          <div className="lg:col-span-4 space-y-4">
            {/* Generation Panel */}
            <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-5 shadow-sm space-y-4">
              <div>
                <h3 className="text-[10px] font-bold text-[#111111] uppercase tracking-wider">Generate Study Packs</h3>
                <p className="text-[10.5px] text-[#666666] mt-1 leading-relaxed">
                  Compile a complete learning kit (Summary, Flashcards, MCQs, Mind Map) from a document in one click.
                </p>
              </div>

              {isLoadingDocs ? (
                <div className="py-4 flex justify-center">
                  <Loader2 size={16} className="animate-spin text-zinc-400" />
                </div>
              ) : documents.length === 0 ? (
                <div className="text-center p-4 border border-dashed border-[#E5DDD0] rounded-xl bg-[#FCFAF6]/60">
                  <p className="text-[10.5px] font-semibold text-[#111111]">No indexed documents available.</p>
                  <p className="text-[9px] text-zinc-400 mt-0.5">Please upload and index documents first.</p>
                </div>
              ) : (
                <div className="space-y-3">
                  <div className="space-y-1">
                    <label className="text-[9.5px] font-bold text-[#666666] uppercase tracking-wider">Select Source</label>
                    <div className="relative">
                      <select
                        value={selectedDocIdForSP}
                        onChange={(e) => setSelectedDocIdForSP(e.target.value)}
                        className="w-full bg-white border border-[#E5DDD0] rounded-xl px-3 py-2 text-xs text-[#111111] focus:outline-none focus:border-zinc-400 cursor-pointer appearance-none pr-8 font-medium"
                      >
                        {documents.map((d) => (
                          <option key={d.id} value={d.id}>
                            {d.name.length > 30 ? d.name.slice(0, 27) + '...' : d.name}
                          </option>
                        ))}
                      </select>
                      <ChevronDown size={14} className="absolute right-3 top-1/2 -translate-y-1/2 text-zinc-450 pointer-events-none" />
                    </div>
                  </div>

                  <button
                    onClick={handleGenerateStudyPack}
                    disabled={isGeneratingSP || !selectedDocIdForSP}
                    className="w-full py-2.5 px-4 bg-[#111111] hover:bg-zinc-800 disabled:bg-[#F8F4EC] disabled:text-[#666666]/50 text-white rounded-xl text-xs font-bold transition-all shadow-sm flex items-center justify-center space-x-2 cursor-pointer btn-press-active"
                  >
                    {isGeneratingSP ? (
                      <>
                        <Loader2 size={13} className="animate-spin" />
                        <span>Generating Pack...</span>
                      </>
                    ) : (
                      <>
                        <Sparkles size={13} />
                        <span>Generate Pack</span>
                      </>
                    )}
                  </button>
                </div>
              )}

              {spError && (
                <div className="flex items-start space-x-2 p-3 bg-rose-50 border border-rose-100 rounded-xl">
                  <AlertCircle className="text-rose-700 shrink-0 mt-0.5" size={13} />
                  <span className="text-[9.5px] text-rose-750 font-semibold leading-relaxed">{spError}</span>
                </div>
              )}
            </div>

            {/* History Packs List Panel */}
            <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-5 shadow-sm space-y-3">
              <h3 className="text-[10px] font-bold text-[#111111] uppercase tracking-wider">Your Study Packs ({studyPacks.length})</h3>
              
              {studyPacks.length === 0 ? (
                <p className="text-[10.5px] text-[#666666] italic py-2 text-center">No study packs generated yet.</p>
              ) : (
                <div className="space-y-2 max-h-[260px] overflow-y-auto pr-1 hide-scrollbar">
                  {studyPacks.map((pack) => {
                    const isSelected = activePack?.id === pack.id;
                    return (
                      <div
                        key={pack.id}
                        onClick={() => {
                          setActivePack(pack);
                        }}
                        className={`group p-3 border rounded-xl flex items-center justify-between cursor-pointer transition-all duration-200 ${
                          isSelected 
                            ? 'bg-[#F8F4EC] border-[#E5DDD0] shadow-sm' 
                            : 'bg-white hover:bg-[#F8F4EC]/40 border-[#E5DDD0]'
                        }`}
                      >
                        <div className="flex items-center space-x-2 overflow-hidden flex-1 mr-2">
                          <FileText size={12} className="text-[#666666] shrink-0" />
                          <span className="text-[11px] font-bold text-[#111111] truncate" title={pack.title}>
                            {pack.title.replace('Study Pack: ', '')}
                          </span>
                        </div>
                        <span className="text-[9px] text-[#666666] font-bold shrink-0">
                          {new Date(pack.created_at).toLocaleDateString(undefined, {month: 'short', day: 'numeric'})}
                        </span>
                      </div>
                    );
                  })}
                </div>
              )}
            </div>
          </div>

          {/* Details / Export Panel */}
          <div className="lg:col-span-8">
            <div className="bg-[#FCFAF6] border border-[#E5DDD0] rounded-2xl p-6 shadow-sm flex flex-col items-center justify-between min-h-[460px] h-full">
              {!activePack ? (
                <div className="flex-1 flex flex-col items-center justify-center text-center max-w-sm mx-auto py-16">
                  <div className="p-4 bg-[#F8F4EC] border border-[#E5DDD0] rounded-xl text-zinc-400 mb-3">
                    <Layers size={24} />
                  </div>
                  <h4 className="text-xs font-bold text-[#111111]">No Study Pack Selected</h4>
                  <p className="text-[10.5px] text-[#666666] mt-1 leading-relaxed">
                    Select a document and generate a study pack, or pick an existing study pack from the list to download its elements.
                  </p>
                </div>
              ) : (
                <div className="w-full flex flex-col h-full justify-between flex-grow">
                  {/* Top Deck Info */}
                  <div className="w-full border-b border-[#E5DDD0] pb-4 mb-6">
                    <h4 className="text-sm font-extrabold text-[#111111] truncate max-w-[500px]" title={activePack.title}>
                      {activePack.title}
                    </h4>
                    <p className="text-[9.5px] text-[#666666] font-bold uppercase mt-1">
                      Created: {new Date(activePack.created_at).toLocaleString()}
                    </p>
                  </div>

                  {/* Pack Inclusions Description */}
                  <div className="flex-1 space-y-6 select-text mb-6">
                    <div className="bg-white border border-[#E5DDD0] rounded-xl p-5 space-y-4">
                      <h5 className="text-[10.5px] font-bold text-[#111111] uppercase tracking-wider">Pack Contents Include:</h5>
                      
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="flex items-start space-x-3">
                          <span className="p-1.5 bg-sky-50 text-sky-600 rounded-lg shrink-0 border border-sky-100">
                            <FileText size={14} />
                          </span>
                          <div>
                            <p className="text-[11px] font-bold text-[#111111]">1. Executive Summary & Key Takeaways</p>
                            <p className="text-[9.5px] text-zinc-500 mt-0.5 leading-normal">
                              Cohesive 150-250 word executive summary with 4-6 bulleted core concepts.
                            </p>
                          </div>
                        </div>

                        <div className="flex items-start space-x-3">
                          <span className="p-1.5 bg-indigo-50 text-indigo-600 rounded-lg shrink-0 border border-indigo-100">
                            <BookOpen size={14} />
                          </span>
                          <div>
                            <p className="text-[11px] font-bold text-[#111111]">2. Active Recall Flashcards</p>
                            <p className="text-[9.5px] text-zinc-500 mt-0.5 leading-normal">
                              8 to 12 educational Q&A flashcards designed to lock in details.
                            </p>
                          </div>
                        </div>

                        <div className="flex items-start space-x-3">
                          <span className="p-1.5 bg-amber-50 text-amber-600 rounded-lg shrink-0 border border-amber-100">
                            <HelpCircle size={14} />
                          </span>
                          <div>
                            <p className="text-[11px] font-bold text-[#111111]">3. MCQ Assessment Sheet</p>
                            <p className="text-[9.5px] text-zinc-500 mt-0.5 leading-normal">
                              5 custom difficulty multiple-choice quiz questions with detailed explanations.
                            </p>
                          </div>
                        </div>

                        <div className="flex items-start space-x-3">
                          <span className="p-1.5 bg-emerald-50 text-emerald-600 rounded-lg shrink-0 border border-emerald-100">
                            <Map size={14} />
                          </span>
                          <div>
                            <p className="text-[11px] font-bold text-[#111111]">4. Conceptual Mind Map</p>
                            <p className="text-[9.5px] text-zinc-500 mt-0.5 leading-normal">
                              Hierarchical visual branch chart mapping concepts with Pillow layout.
                            </p>
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="border border-dashed border-[#E5DDD0] rounded-xl p-4 bg-[#F8F4EC]/30 text-center">
                      <p className="text-[10px] text-[#666666]">
                        Choose your preferred export format below. Both downloads compile all study aids automatically.
                      </p>
                    </div>
                  </div>

                  {/* Actions / Download Buttons */}
                  <div className="w-full grid grid-cols-1 md:grid-cols-2 gap-4 border-t border-[#E5DDD0] pt-5">
                    <button
                      onClick={() => handleDownloadPDF(activePack)}
                      className="py-3 px-4 bg-[#111111] hover:bg-zinc-800 text-white rounded-xl text-xs font-bold transition-all shadow-sm flex items-center justify-center space-x-2 cursor-pointer btn-press-active"
                    >
                      <Download size={14} />
                      <span>Download Single PDF</span>
                    </button>

                    <button
                      onClick={() => handleDownloadZIP(activePack)}
                      className="py-3 px-4 border border-[#E5DDD0] hover:bg-[#F8F4EC]/60 text-zinc-750 rounded-xl text-xs font-bold transition-all shadow-sm flex items-center justify-center space-x-2 cursor-pointer btn-press-active"
                    >
                      <Layers size={14} />
                      <span>Download ZIP Bundle</span>
                    </button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

    </div>
  );
};

export default StudyTools;
