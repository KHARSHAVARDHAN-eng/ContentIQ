import React, { useEffect, useState, useRef } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { 
  Brain, 
  ArrowRight, 
  ShieldCheck, 
  Plus, 
  FileText, 
  CheckCircle2, 
  ChevronRight, 
  ChevronDown, 
  UploadCloud, 
  RefreshCw, 
  BarChart2, 
  File,
  Sparkles,
  Layers,
  CheckSquare
} from 'lucide-react';
import { motion, AnimatePresence, useMotionValue, useSpring } from 'framer-motion';
import CursorTrail from '../components/CursorTrail';
import FloatingParticles from '../components/FloatingParticles';
import gsap from 'gsap';

// --- MAGNETIC WRAPPER FOR BUTTONS ---
const InteractiveMagnetic = ({ children, className = "" }) => {
  const x = useMotionValue(0);
  const y = useMotionValue(0);
  
  const springConfig = { damping: 15, stiffness: 150 };
  const springX = useSpring(x, springConfig);
  const springY = useSpring(y, springConfig);
  
  const handleMouseMove = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const width = rect.width;
    const height = rect.height;
    const clientX = e.clientX - rect.left - width / 2;
    const clientY = e.clientY - rect.top - height / 2;
    x.set(clientX * 0.22);
    y.set(clientY * 0.22);
  };
  
  const handleMouseLeave = () => {
    x.set(0);
    y.set(0);
  };
  
  return (
    <motion.div
      onMouseMove={handleMouseMove}
      onMouseLeave={handleMouseLeave}
      style={{ x: springX, y: springY }}
      className={`inline-block transition-magnetic ${className}`}
    >
      {children}
    </motion.div>
  );
};

// --- SCROLL REVEAL COMPONENT ---
const ScrollReveal = ({ children, className = "", delay = 0 }) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-80px" }}
      transition={{ duration: 0.6, delay, ease: [0.16, 1, 0.3, 1] }}
      className={className}
    >
      {children}
    </motion.div>
  );
};

const Landing = () => {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const footerRef = useRef(null);

  // GSAP animation for footer reveal
  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          gsap.fromTo(footerRef.current,
            { y: 20, opacity: 0 },
            { y: 0, opacity: 1, duration: 0.8, ease: 'power3.out' }
          );
          observer.unobserve(entry.target);
        }
      },
      { threshold: 0.05 }
    );
    if (footerRef.current) {
      observer.observe(footerRef.current);
    }
    return () => observer.disconnect();
  }, []);
  
  // States for interactive upload simulation
  const [uploadState, setUploadState] = useState('idle'); // idle -> uploading -> parsing -> indexing -> done
  const [uploadProgress, setUploadProgress] = useState(0);
  const [citationHovered, setCitationHovered] = useState(null);
  const [activeFaq, setActiveFaq] = useState(null);

  // Mouse tracking position for hero glow
  const [mousePos, setMousePos] = useState({ x: 0, y: 0 });
  const handleMouseMoveHero = (e) => {
    const rect = e.currentTarget.getBoundingClientRect();
    setMousePos({
      x: e.clientX - rect.left,
      y: e.clientY - rect.top
    });
  };

  // Redirect authenticated users
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate]);

  // GSAP staggered intro animations
  useEffect(() => {
    const tl = gsap.timeline({ defaults: { ease: 'power3.out' } });

    // Staggered Hero Elements
    tl.fromTo('.gsap-hero-title', 
      { y: 40, opacity: 0 }, 
      { y: 0, opacity: 1, duration: 0.9, delay: 0.2 }
    );
    
    tl.fromTo('.gsap-hero-subtitle', 
      { y: 25, opacity: 0 }, 
      { y: 0, opacity: 1, duration: 0.9 },
      '-=0.6'
    );
    
    tl.fromTo('.gsap-hero-buttons', 
      { y: 20, opacity: 0 }, 
      { y: 0, opacity: 1, duration: 0.7 },
      '-=0.6'
    );
    
    // Trust section formats card
    tl.fromTo('.gsap-trust-card', 
      { y: 25, opacity: 0 }, 
      { y: 0, opacity: 1, duration: 0.9 },
      '-=0.5'
    );
  }, []);

  // Simulation trigger
  const runUploadSim = () => {
    if (uploadState !== 'idle' && uploadState !== 'done') return;
    setUploadState('uploading');
    setUploadProgress(0);
  };

  useEffect(() => {
    let interval;
    if (uploadState === 'uploading') {
      interval = setInterval(() => {
        setUploadProgress((prev) => {
          if (prev >= 100) {
            clearInterval(interval);
            setUploadState('parsing');
            return 100;
          }
          return prev + 25;
        });
      }, 100);
    } else if (uploadState === 'parsing') {
      const timer = setTimeout(() => {
        setUploadState('indexing');
      }, 600);
      return () => clearTimeout(timer);
    } else if (uploadState === 'indexing') {
      const timer = setTimeout(() => {
        setUploadState('done');
      }, 800);
      return () => clearTimeout(timer);
    }
    return () => clearInterval(interval);
  }, [uploadState]);

  return (
    <div className="min-h-screen text-[#1A1A1A] font-sans selection:bg-[#7DD3FC]/30 selection:text-zinc-950 overflow-x-hidden relative grid-paper pb-16">
      
      {/* Premium Cursor Trail Effect */}
      <CursorTrail />
      {/* --- STICKY TRANSPARENT NAVBAR (Underlined links, contentIQ branding) --- */}
      <header className="sticky top-0 z-50 w-full bg-[#F8F4EC]/90 backdrop-blur-md px-8 py-5 flex items-center justify-between border-b border-[#E5DDD0]/50 text-[#1A1A1A]">
        <Link 
          to="/" 
          className="text-4xl font-extrabold font-bevellier tracking-tight underline decoration-brand-sky decoration-[3px] underline-offset-8 cursor-pointer hover:text-zinc-700 transition-colors"
        >
          contentIQ
        </Link>
        
        {/* Nav Links */}
        <nav className="hidden md:flex items-center space-x-10 text-xl font-bold font-bevellier uppercase tracking-wider">
          <a href="#features" className="hover:text-zinc-700 transition-colors underline decoration-brand-sky decoration-[3px] underline-offset-8">Features</a>
          <a href="#how-it-works" className="hover:text-zinc-700 transition-colors underline decoration-brand-sky decoration-[3px] underline-offset-8">How It Works</a>
          <a href="#use-cases" className="hover:text-zinc-700 transition-colors underline decoration-brand-sky decoration-[3px] underline-offset-8">Use Cases</a>
          <a href="#faq" className="hover:text-zinc-700 transition-colors underline decoration-brand-sky decoration-[3px] underline-offset-8">FAQ</a>
        </nav>

        {/* Action buttons */}
        <div className="flex items-center space-x-8 text-xl font-bold font-bevellier uppercase tracking-wider">
          <Link 
            to="/login"
            className="hover:text-zinc-700 transition-colors underline decoration-brand-sky decoration-[3px] underline-offset-8 cursor-pointer"
          >
            Log In
          </Link>
          <InteractiveMagnetic>
            <Link
              to="/register"
              className="hover:text-zinc-700 transition-colors underline decoration-brand-sky decoration-[3px] underline-offset-8 cursor-pointer"
            >
              Get Started
            </Link>
          </InteractiveMagnetic>
        </div>
      </header>

      {/* --- HERO SECTION --- */}
      <section 
        onMouseMove={handleMouseMoveHero}
        className="max-w-5xl mx-auto px-6 pt-28 md:pt-40 pb-10 text-center space-y-8 relative z-10 overflow-hidden"
      >
        <FloatingParticles />

        {/* Spring animated mouse-following soft blue glow halo */}
        <div 
          className="absolute rounded-full bg-[#BAE6FD]/30 blur-[100px] pointer-events-none z-0 hidden md:block"
          style={{
            left: mousePos.x - 250,
            top: mousePos.y - 250,
            width: 500,
            height: 500,
          }}
        />
        
        <div className="relative z-10 space-y-8">
          <h1 className="gsap-hero-title text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-extrabold tracking-tight text-[#1A1A1A] leading-[1.05] max-w-4xl mx-auto opacity-0">
            Documents That <br className="hidden sm:inline" />
            Answer Back
          </h1>

          <p className="gsap-hero-subtitle text-zinc-650 text-sm sm:text-base md:text-lg max-w-2xl mx-auto leading-relaxed font-semibold opacity-0">
            Upload documents. Ask questions naturally. Get instant answers with source citations.
          </p>

          <div className="gsap-hero-buttons flex flex-col sm:flex-row items-center justify-center gap-4 pt-3 relative opacity-0">
            {/* Subtle yellow ambient halo near buttons */}
            <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[260px] h-[90px] rounded-full bg-[#FDE68A]/20 blur-[70px] pointer-events-none z-0" />
            
            <div className="relative z-10 flex flex-col sm:flex-row items-center justify-center gap-4 w-full sm:w-auto">
              <InteractiveMagnetic>
                <Link
                  to="/register"
                  className="w-full sm:w-auto flex items-center justify-center space-x-2 px-7 py-3.5 bg-gradient-to-r from-[#7DD3FC] to-[#BAE6FD] hover:from-[#38BDF8] hover:to-[#7DD3FC] text-[#1A1A1A] font-extrabold rounded-full shadow-md text-xs uppercase tracking-wider transition-all cursor-pointer active:scale-95 transition-transform"
                >
                  <span>Upload Document</span>
                  <ArrowRight size={13} className="stroke-[2.5]" />
                </Link>
              </InteractiveMagnetic>
              <InteractiveMagnetic>
                <a
                  href="#how-it-works"
                  className="w-full sm:w-auto flex items-center justify-center space-x-1 px-7 py-3.5 bg-[#F3EBDD] hover:bg-[#E5DDD0] border border-[#E5DDD0] text-[#1A1A1A] font-bold rounded-full shadow-sm text-xs uppercase tracking-wider transition-all cursor-pointer active:scale-95 transition-transform"
                >
                  <span>See How It Works</span>
                </a>
              </InteractiveMagnetic>
            </div>
          </div>
        </div>
      </section>

      {/* --- 3. FORMATS / TRUST SECTION --- */}
      <section className="max-w-4xl mx-auto px-6 pb-14 relative z-10">
        <div className="gsap-trust-card opacity-0">
          <div className="glass-card rounded-[20px] border border-[#E5DDD0]/70 p-6 text-center space-y-4 shadow-sm">
            <span className="text-[10px] text-zinc-500 font-extrabold uppercase tracking-widest block">Supported Document Formats</span>
            <div className="flex flex-wrap items-center justify-center gap-8 text-xs font-bold text-zinc-700 uppercase">
              <span className="flex items-center space-x-2">
                <File size={14} className="text-[#7DD3FC]" />
                <span>PDF Documents</span>
              </span>
              <span className="flex items-center space-x-2">
                <FileText size={14} className="text-[#7DD3FC]" />
                <span>Word Files</span>
              </span>
              <span className="flex items-center space-x-2">
                <Sparkles size={14} className="text-[#FACC15]" />
                <span>Scanned Reports</span>
              </span>
              <span className="flex items-center space-x-2">
                <Layers size={14} className="text-[#7DD3FC]" />
                <span>Plain text logs</span>
              </span>
              <span className="flex items-center space-x-2">
                <CheckSquare size={14} className="text-[#FACC15]" />
                <span>Written Notebooks</span>
              </span>
            </div>
          </div>
        </div>
      </section>

      {/* --- 4. BENTO GRID FEATURES --- */}
      <section id="features" className="max-w-5xl mx-auto px-6 py-14 space-y-8 relative z-10 border-t border-[#E5DDD0]/50">
        <ScrollReveal>
          <div className="space-y-1.5 text-center md:text-left">
            <h2 className="text-xs font-extrabold text-[#7DD3FC] uppercase tracking-widest">Why contentIQ</h2>
            <h3 className="text-3xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-[#1A1A1A]">Why People Choose contentIQ</h3>
          </div>
        </ScrollReveal>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          
          {/* Card 1: Ask Questions Naturally (2 columns wide) */}
          <ScrollReveal delay={0.05} className="md:col-span-2">
            <motion.div 
              whileHover={{ y: -4 }}
              className="glass-card rounded-[20px] p-7 min-h-[240px] flex flex-col justify-between border border-[#E5DDD0]/70 shadow-sm hover:shadow-md transition-all duration-300"
            >
              <div className="space-y-3">
                <div className="p-2 bg-[#7DD3FC]/10 border border-[#7DD3FC]/20 text-[#38BDF8] rounded-xl w-max">
                  <ShieldCheck size={22} />
                </div>
                <h4 className="text-xl sm:text-2xl md:text-3xl font-extrabold text-[#1A1A1A]">Ask Questions Naturally</h4>
                <p className="text-xs sm:text-sm text-zinc-650 leading-relaxed font-semibold">
                  Type questions in simple, plain language. Get direct answers immediately without combing through massive files or cross-referencing pages manually.
                </p>
              </div>
              
              <div className="border border-[#E5DDD0] bg-[#F3EBDD]/60 rounded-xl p-3 flex items-center justify-between shadow-inner">
                <div className="flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-[#FACC15] animate-pulse"></span>
                  <span className="text-[10px] font-bold text-zinc-700 font-mono">Verifiable answers and highlights</span>
                </div>
              </div>
            </motion.div>
          </ScrollReveal>

          {/* Card 2: Source-backed Answers (1 column) */}
          <ScrollReveal delay={0.1}>
            <motion.div 
              whileHover={{ y: -4 }}
              className="glass-card rounded-[20px] p-7 min-h-[240px] flex flex-col justify-between border border-[#E5DDD0]/70 shadow-sm hover:shadow-md transition-all duration-300"
            >
              <div className="space-y-3">
                <div className="p-2 bg-[#FACC15]/10 border border-[#FACC15]/20 text-yellow-700 rounded-xl w-max">
                  <Sparkles size={22} />
                </div>
                <h4 className="text-xl sm:text-2xl md:text-3xl font-extrabold text-[#1A1A1A]">Source-backed Answers</h4>
                <p className="text-xs sm:text-sm text-zinc-650 leading-relaxed font-semibold">
                  Every response links back to specific passages in your documents. Hover over citations to review source texts instantly.
                </p>
              </div>
            </motion.div>
          </ScrollReveal>

          {/* Card 3: Instant Document Search (1 column) */}
          <ScrollReveal delay={0.15}>
            <motion.div 
              whileHover={{ y: -4 }}
              className="glass-card rounded-[20px] p-7 min-h-[240px] flex flex-col justify-between border border-[#E5DDD0]/70 shadow-sm hover:shadow-md transition-all duration-300"
            >
              <div className="space-y-3">
                <div className="p-2 bg-[#7DD3FC]/10 border border-[#7DD3FC]/20 text-[#38BDF8] rounded-xl w-max">
                  <UploadCloud size={22} />
                </div>
                <h4 className="text-xl sm:text-2xl md:text-3xl font-extrabold text-[#1A1A1A]">Instant Document Search</h4>
                <p className="text-xs sm:text-sm text-zinc-650 leading-relaxed font-semibold">
                  Search across your entire catalog of uploads. Find exact matches and relevant text segments in fractions of a second.
                </p>
              </div>
            </motion.div>
          </ScrollReveal>

          {/* Card 4: Works With Any PDF (2 columns wide) */}
          <ScrollReveal delay={0.2} className="md:col-span-2">
            <motion.div 
              whileHover={{ y: -4 }}
              className="glass-card rounded-[20px] p-7 min-h-[240px] flex flex-col justify-between border border-[#E5DDD0]/70 shadow-sm hover:shadow-md transition-all duration-300"
            >
              <div className="space-y-3">
                <div className="p-2 bg-[#FACC15]/10 border border-[#FACC15]/20 text-yellow-700 rounded-xl w-max">
                  <BarChart2 size={22} />
                </div>
                <h4 className="text-xl sm:text-2xl md:text-3xl font-extrabold text-[#1A1A1A]">Works With Any PDF</h4>
                <p className="text-xs sm:text-sm text-zinc-650 leading-relaxed font-semibold text-zinc-600">
                  Drop digital PDFs, scanned agreements, pictures, or notes. Our layout parser extracts text blocks and reads tabular structures automatically.
                </p>
              </div>
            </motion.div>
          </ScrollReveal>
        </div>
      </section>

      {/* --- 5. HOW IT WORKS --- */}
      <section id="how-it-works" className="max-w-5xl mx-auto px-6 py-14 relative z-10 border-t border-[#E5DDD0]/50">
        <ScrollReveal>
          <div className="max-w-xl mx-auto text-center space-y-2 pb-10">
            <h2 className="text-xs font-extrabold text-[#7DD3FC] uppercase tracking-widest">Workflow</h2>
            <h3 className="text-3xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-[#1A1A1A]">How It Works</h3>
            <p className="text-xs sm:text-sm text-zinc-550 font-semibold">Four simple steps to get answers from your documents.</p>
          </div>
        </ScrollReveal>

        {/* Steps Grid */}
        <ScrollReveal delay={0.1} className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-6 pb-12">
          {[
            { step: "Step 1", title: "Upload Documents", desc: "Drag and drop PDFs, reports, notes, or scanned images securely into your workspace." },
            { step: "Step 2", title: "AI Processes Content", desc: "Our document text parser processes layout blocks, columns, and scans instantly." },
            { step: "Step 3", title: "Ask Questions", desc: "Type questions in plain, natural English inside your workspace thread." },
            { step: "Step 4", title: "Get Answers With Sources", desc: "Read responses compiled with clear highlighted underlines and citations back to original files." }
          ].map((item, idx) => (
            <motion.div 
              key={idx}
              whileHover={{ y: -2 }}
              className="glass-card rounded-2xl p-5 border border-[#E5DDD0]/70 flex flex-col justify-between shadow-sm"
            >
              <div className="space-y-2">
                <span className="text-[10px] font-bold text-[#7DD3FC] uppercase tracking-wider block font-mono">{item.step}</span>
                <h4 className="text-base font-bold text-[#1A1A1A]">{item.title}</h4>
                <p className="text-[11px] text-zinc-550 font-semibold leading-relaxed">{item.desc}</p>
              </div>
            </motion.div>
          ))}
        </ScrollReveal>

        {/* Simulator */}
        <ScrollReveal delay={0.2} className="max-w-md mx-auto">
          <motion.div 
            whileHover={{ y: -2 }}
            onClick={runUploadSim}
            className={`glass-card-darker rounded-[20px] p-7 border border-[#E5DDD0] shadow-md text-center cursor-pointer transition-all duration-300 relative overflow-hidden select-none ${
              uploadState !== 'idle' && uploadState !== 'done' ? 'pointer-events-none' : ''
            }`}
          >
            <AnimatePresence mode="wait">
              {uploadState === 'idle' && (
                <motion.div 
                  key="idle"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  className="space-y-4 py-4"
                >
                  <div className="w-12 h-12 rounded-xl bg-[#F8F4EC] border border-[#E5DDD0] flex items-center justify-center mx-auto text-zinc-400 shadow-inner">
                    <UploadCloud size={22} />
                  </div>
                  <div>
                    <h4 className="text-xs sm:text-sm font-bold text-zinc-800">Click to upload document mockup</h4>
                    <p className="text-[10px] text-zinc-500 font-bold mt-1">Accepts PDF, DOCX, Images, Notes</p>
                  </div>
                </motion.div>
              )}

              {uploadState === 'uploading' && (
                <motion.div 
                  key="uploading"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  className="space-y-4 py-4"
                >
                  <RefreshCw size={22} className="text-[#38BDF8] animate-spin mx-auto" />
                  <div className="space-y-2">
                    <h4 className="text-xs sm:text-sm font-bold text-zinc-800">Uploading File...</h4>
                    <div className="w-44 h-1.5 bg-[#E5DDD0] rounded-full mx-auto overflow-hidden">
                      <div 
                        className="h-full bg-[#38BDF8] transition-all duration-100" 
                        style={{ width: `${uploadProgress}%` }}
                      ></div>
                    </div>
                    <span className="text-[9px] font-bold text-zinc-600 font-mono">{uploadProgress}%</span>
                  </div>
                </motion.div>
              )}

              {uploadState === 'parsing' && (
                <motion.div 
                  key="parsing"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  className="space-y-4 py-4"
                >
                  <RefreshCw size={22} className="text-[#FACC15] animate-spin mx-auto" />
                  <div className="space-y-1">
                    <h4 className="text-xs sm:text-sm font-bold text-zinc-800">Scanning structures & pages...</h4>
                    <p className="text-[10px] text-zinc-500 font-bold font-sans">Isolating paragraph coordinates</p>
                  </div>
                </motion.div>
              )}

              {uploadState === 'indexing' && (
                <motion.div 
                  key="indexing"
                  initial={{ opacity: 0, y: 5 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -5 }}
                  className="space-y-4 py-4"
                >
                  <Layers size={22} className="text-[#38BDF8] animate-bounce mx-auto" />
                  <div className="space-y-1">
                    <h4 className="text-xs sm:text-sm font-bold text-[#1A1A1A]">Indexing Paragraphs...</h4>
                    <p className="text-[10px] text-zinc-550 font-bold">Compiling source citation keys</p>
                  </div>
                </motion.div>
              )}

              {uploadState === 'done' && (
                <motion.div 
                  key="done"
                  initial={{ opacity: 0, scale: 0.96 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0 }}
                  className="space-y-4 py-4"
                >
                  <div className="w-12 h-12 rounded-xl bg-emerald-50 border border-emerald-100 flex items-center justify-center mx-auto text-emerald-500 shadow-inner">
                    <CheckCircle2 size={22} className="stroke-[2.5]" />
                  </div>
                  <div>
                    <h4 className="text-xs sm:text-sm font-bold text-zinc-850">Document Successfully Indexed</h4>
                    <p className="text-[10px] text-zinc-650 font-bold mt-1">
                      Text splits ready. Citations active.
                    </p>
                  </div>
                  <button 
                    onClick={(e) => {
                      e.stopPropagation();
                      setUploadState('idle');
                    }}
                    className="text-[10px] font-bold text-[#1A1A1A] hover:bg-[#E5DDD0] bg-[#F3EBDD] px-4 py-1.5 rounded-full border border-[#E5DDD0]"
                  >
                    Upload Another
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </motion.div>
        </ScrollReveal>
      </section>

      {/* --- 6. RAG CITATIONS DEMO SECTION --- */}
      <section id="citations" className="max-w-5xl mx-auto px-6 py-14 relative z-10 border-t border-[#E5DDD0]/50">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-10 items-center">
          
          <ScrollReveal className="space-y-4">
            <div className="p-2 bg-[#7DD3FC]/10 border border-[#7DD3FC]/20 text-[#38BDF8] rounded-xl w-max">
              <ShieldCheck size={20} />
            </div>
            <h3 className="text-3xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-[#1A1A1A]">
              Clear attributions. <br />
              Double-check instantly.
            </h3>
            <p className="text-xs sm:text-sm text-zinc-650 leading-relaxed font-semibold">
              contentIQ segments uploaded text and prompts chat to reference paragraphs directly. Simply hover over citation tags to view the source passage in one click.
            </p>
          </ScrollReveal>

          {/* Interactive Chat Mockup */}
          <ScrollReveal delay={0.1}>
            <div className="glass-card-darker rounded-[20px] border border-[#E5DDD0] p-5.5 shadow-md space-y-4">
              <div className="pb-2.5 border-b border-[#E5DDD0] flex items-center justify-between">
                <span className="text-[10px] text-zinc-500 font-bold uppercase tracking-wider">Document Chat Session</span>
                <span className="h-2 w-2 rounded-full bg-[#7DD3FC]"></span>
              </div>

              {/* Chat Thread */}
              <div className="space-y-3.5 text-xs">
                {/* User Message */}
                <div className="text-right">
                  <div className="inline-block bg-[#F3EBDD] border border-[#E5DDD0] text-zinc-800 rounded-xl rounded-tr-none px-4 py-2 font-bold">
                    What is the late penalty terms in Section 4.5?
                  </div>
                </div>

                {/* Citation Cards */}
                <div className="space-y-1">
                  <div className="text-[9px] font-bold text-zinc-555 uppercase tracking-widest">Sources Found</div>
                  <div className="bg-[#F8F4EC] border border-[#E5DDD0] p-2.5 rounded-lg flex items-center space-x-2">
                    <FileText size={13} className="text-zinc-500" />
                    <span className="text-[10px] font-bold text-zinc-800 truncate">Vendor_Agreement_Final.pdf</span>
                    <span className="text-[9px] bg-[#F3EBDD] border border-[#E5DDD0] text-zinc-600 px-2 py-0.5 rounded font-bold ml-auto shrink-0">Page 4</span>
                  </div>
                </div>

                {/* Bot Message */}
                <div className="bg-white/90 border border-[#E5DDD0] rounded-xl p-4 space-y-3 shadow-sm font-sans">
                  <p className="leading-relaxed text-zinc-700 font-semibold text-xs">
                    Late payment settlements under Section 4.5 trigger an automatic 1.5% monthly interest penalty{' '}
                    <span 
                      onMouseEnter={() => setCitationHovered(1)}
                      onMouseLeave={() => setCitationHovered(null)}
                      className={`inline-flex items-center justify-center w-4 h-4 rounded-full text-[8.5px] font-extrabold border cursor-help transition-all ${
                        citationHovered === 1 
                          ? 'bg-[#7DD3FC] text-zinc-950 border-[#7DD3FC] scale-110 shadow-sm' 
                          : 'bg-zinc-200/80 text-zinc-650 border-zinc-350'
                      }`}
                    >
                      1
                    </span>
                    , which begins compounding 30 days after invoice delivery{' '}
                    <span 
                      onMouseEnter={() => setCitationHovered(2)}
                      onMouseLeave={() => setCitationHovered(null)}
                      className={`inline-flex items-center justify-center w-4 h-4 rounded-full text-[8.5px] font-extrabold border cursor-help transition-all ${
                        citationHovered === 2 
                          ? 'bg-[#7DD3FC] text-zinc-950 border-[#7DD3FC] scale-110 shadow-sm' 
                          : 'bg-zinc-200/80 text-zinc-650 border-zinc-350'
                      }`}
                    >
                      2
                    </span>
                    .
                  </p>

                  <AnimatePresence mode="wait">
                    {citationHovered === 1 && (
                      <motion.div 
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="bg-[#FDE68A]/25 border border-[#FACC15]/30 p-3 rounded-lg text-xs leading-normal font-semibold text-zinc-800 font-mono"
                      >
                        <span className="font-extrabold text-yellow-850 block text-[8.5px] uppercase mb-0.5">Section 4.5 segment:</span>
                        "...settlements bear interest at a rate of 1.5% per month..."
                      </motion.div>
                    )}

                    {citationHovered === 2 && (
                      <motion.div 
                        initial={{ opacity: 0, y: 4 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0 }}
                        className="bg-[#FDE68A]/25 border border-[#FACC15]/30 p-3 rounded-lg text-xs leading-normal font-semibold text-zinc-800 font-mono"
                      >
                        <span className="font-extrabold text-yellow-850 block text-[8.5px] uppercase mb-0.5">Section 4.5 segment:</span>
                        "...interest compounds 30 calendar days following deliverable invoice receipts..."
                      </motion.div>
                    )}
                  </AnimatePresence>
                </div>
              </div>
            </div>
          </ScrollReveal>

        </div>
      </section>

      {/* --- 7. USE CASES --- */}
      <section id="use-cases" className="max-w-5xl mx-auto px-6 py-14 relative z-10 border-t border-[#E5DDD0]/50">
        <ScrollReveal>
          <div className="max-w-xl mx-auto text-center space-y-2 pb-10">
            <h2 className="text-xs font-extrabold text-[#7DD3FC] uppercase tracking-widest">Applications</h2>
            <h3 className="text-3xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-[#1A1A1A]">Built for Every Researcher</h3>
            <p className="text-xs sm:text-sm text-zinc-550 font-semibold">How students, researchers, and professional teams use contentIQ.</p>
          </div>
        </ScrollReveal>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {[
            { title: "For Students & Academics", desc: "Read research papers, search textbooks, and query thesis publications. Get immediate answers with clear bookmarks back to original page coordinates." },
            { title: "For Professional Teams", desc: "Review policy reports, company handbooks, and operational files. Maintain complete fact auditing checks across update libraries." },
            { title: "For Legal & Contracts", desc: "Upload vendor agreements, terms, and contracts. Query dates, penalty terms, and liability limits with absolute attribution fidelity." }
          ].map((item, idx) => (
            <motion.div 
              key={idx}
              whileHover={{ y: -4 }}
              className="glass-card rounded-[20px] p-6 border border-[#E5DDD0]/70 flex flex-col justify-between shadow-sm"
            >
              <div className="space-y-3">
                <div className="p-2 bg-[#FACC15]/10 border border-[#FACC15]/20 text-yellow-700 rounded-xl w-max">
                  <Sparkles size={18} />
                </div>
                <h4 className="text-lg font-bold text-[#1A1A1A]">{item.title}</h4>
                <p className="text-xs sm:text-sm text-zinc-650 leading-relaxed font-semibold">{item.desc}</p>
              </div>
            </motion.div>
          ))}
        </div>
      </section>

      {/* --- 8. FAQ SECTION --- */}
      <section id="faq" className="max-w-4xl mx-auto px-6 py-14 relative z-10 border-t border-[#E5DDD0]/50">
        <ScrollReveal>
          <div className="max-w-xl mx-auto text-center space-y-2 pb-8">
            <h2 className="text-xs font-extrabold text-[#7DD3FC] uppercase tracking-widest">Questions</h2>
            <h3 className="text-3xl sm:text-5xl md:text-6xl font-extrabold tracking-tight text-[#1A1A1A]">Frequently Asked Questions</h3>
          </div>
        </ScrollReveal>

        <ScrollReveal delay={0.1} className="max-w-2xl mx-auto space-y-3">
          {[
            {
              q: "How does the document citation mechanism work?",
              a: "When you upload files, they are converted into text paragraphs and stored securely. When you query a document, our engine retrieves paragraphs that address your question and highlights them. The response includes interactive references so you can instantly check original passages."
            },
            {
              q: "Can I extract text from scans or images?",
              a: "Yes. contentIQ features an image parser. If an uploaded PDF contains pictures instead of structured text, the OCR engine initiates fallback scanning, retrieving layout paragraphs and preserving table columns."
            },
            {
              q: "Are my documents secure?",
              a: "Absolutely. All files are isolated to your private account workspace. Passwords and sessions use secure encryption, and document segments are protected by access tokens to prevent leaks."
            }
          ].map((faq, idx) => (
            <div 
              key={idx}
              className="glass-card rounded-[20px] border border-[#E5DDD0]/70 overflow-hidden shadow-sm"
            >
              <button 
                onClick={() => setActiveFaq(activeFaq === idx ? null : idx)}
                className="w-full flex items-center justify-between p-5 text-left text-xs sm:text-sm font-bold text-zinc-800 transition-colors select-none cursor-pointer hover:bg-[#F3EBDD]/40"
              >
                <span>{faq.q}</span>
                <ChevronDown 
                  size={14} 
                  className={`text-zinc-505 transition-transform duration-300 ${activeFaq === idx ? 'rotate-180' : ''}`}
                />
              </button>
              
              <AnimatePresence initial={false}>
                {activeFaq === idx && (
                  <motion.div
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                  >
                    <div className="px-5 pb-5 pt-1.5 text-xs text-zinc-650 leading-relaxed font-semibold border-t border-[#E5DDD0] bg-[#F3EBDD]/20">
                      {faq.a}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </div>
          ))}
        </ScrollReveal>
      </section>

      {/* --- 9. FINAL CTA SECTION --- */}
      <section className="max-w-4xl mx-auto px-6 py-8 relative z-10">
        <ScrollReveal>
          <div className="bg-[#1A1A1A] text-white rounded-[24px] p-10 md:p-14 text-center space-y-6 relative overflow-hidden shadow-lg border border-[#1A1A1A]">
            {/* Soft sky-blue glow inside the dark final CTA banner */}
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_80%_at_50%_-20%,rgba(125,211,252,0.15),rgba(255,255,255,0))] pointer-events-none"></div>
            
            <div className="space-y-3.5 relative z-10 max-w-2xl mx-auto">
              <h2 className="text-3xl sm:text-5xl md:text-6xl font-extrabold tracking-tight">Access Attributed Insights</h2>
              <p className="text-zinc-400 text-xs sm:text-sm leading-relaxed font-semibold">
                Stop scanning pages manually. Upload documents, query values, and read responses with verified attributions.
              </p>
            </div>

            <div className="relative z-10 pt-3 flex items-center justify-center">
              <InteractiveMagnetic>
                <Link
                  to="/register"
                  className="inline-flex items-center justify-center space-x-2 px-6 py-3.5 bg-gradient-to-r from-[#7DD3FC] to-[#BAE6FD] hover:from-[#38BDF8] hover:to-[#7DD3FC] text-[#1A1A1A] font-extrabold rounded-full shadow-md text-xs uppercase tracking-wider transition-all cursor-pointer active:scale-95 transition-transform"
                >
                  <span>Get Started for Free</span>
                  <ArrowRight size={13} className="stroke-[2.5]" />
                </Link>
              </InteractiveMagnetic>
            </div>
          </div>
        </ScrollReveal>
      </section>

      {/* --- 10. FOOTER --- */}
      <footer 
        ref={footerRef}
        className="border-t border-[#E5DDD0]/50 bg-[#F3EBDD]/30 py-12 px-6 relative z-10 opacity-0"
      >
        <div className="max-w-4xl mx-auto grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-8">
          <div className="space-y-4 col-span-1">
            <div className="flex items-center space-x-2.5">
              <div className="p-1.5 bg-[#1A1A1A] rounded-lg text-white">
                <Brain size={14} />
              </div>
              <span className="text-xs font-extrabold text-[#1A1A1A]">contentIQ</span>
            </div>
            <p className="text-[11px] text-zinc-550 leading-relaxed font-semibold max-w-xs">
              Attributed document workspace. Upload contracts, agreements, reports, and notes.
            </p>
          </div>

          <div className="space-y-3.5 text-xs col-span-1">
            <h5 className="font-extrabold text-zinc-800 uppercase tracking-widest text-[9.5px]">Links</h5>
            <ul className="space-y-2 font-semibold text-zinc-555">
              <li><a href="#features" className="hover:text-[#1A1A1A] transition-colors">Features</a></li>
              <li><a href="#how-it-works" className="hover:text-[#1A1A1A] transition-colors">How It Works</a></li>
              <li><a href="#use-cases" className="hover:text-[#1A1A1A] transition-colors">Use Cases</a></li>
            </ul>
          </div>

          {/* Column 3: Built By Section */}
          <div className="space-y-3.5 text-xs col-span-1 border-t border-[#E5DDD0]/30 pt-6 sm:border-t-0 sm:pt-0">
            <h5 className="font-extrabold text-zinc-500 uppercase tracking-widest text-[9.5px]">Built By</h5>
            <div className="space-y-1.5">
              <p className="text-[11px] font-bold text-[#1A1A1A] uppercase tracking-wide">
                K HARSHAVARDHAN
              </p>
              <a 
                href="https://www.linkedin.com/in/harshavardhan-katabatthina/"
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center text-[10.5px] font-bold text-zinc-500 hover:text-[#0077B5] transition-all duration-300 hover:translate-x-0.5 underline decoration-zinc-300 hover:decoration-[#0077B5] underline-offset-4"
              >
                Connect on LinkedIn
              </a>
            </div>
          </div>
        </div>

        <div className="max-w-4xl mx-auto mt-10 pt-5 border-t border-[#E5DDD0]/30 text-center flex flex-col sm:flex-row items-center justify-between text-[10px] text-zinc-400 font-bold">
          <span>© {new Date().getFullYear()} contentIQ. All rights reserved.</span>
          <span className="mt-2 sm:mt-0 font-bold text-zinc-500">
            Built by <span className="text-[#1A1A1A] font-extrabold">K HARSHAVARDHAN</span>
          </span>
        </div>
      </footer>

    </div>
  );
};

export default Landing;
