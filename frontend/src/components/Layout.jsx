import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link, useLocation } from 'react-router-dom';
import { LogOut, FileText, Brain, Search, User as UserIcon, HelpCircle, BarChart3, Menu, X, ArrowUpRight, Plus, GraduationCap } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const Layout = ({ children }) => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isActive = (path) => location.pathname === path;

  const getLinkClass = (path) =>
    `flex items-center space-x-3 px-3 py-2 rounded-lg text-sm font-semibold transition-all duration-200 relative group cursor-pointer ${
      isActive(path)
        ? 'bg-zinc-200/60 text-[#18181b]'
        : 'text-zinc-600 hover:text-[#18181b] hover:bg-zinc-100'
    }`;

  const navLinks = [
    { path: '/dashboard', label: 'Workspace', icon: FileText },
    { path: '/search', label: 'Search Playground', icon: Search },
    { path: '/chat', label: 'Grounded Copilot', icon: Brain },
    { path: '/evaluations', label: 'Evaluation Console', icon: BarChart3 },
    { path: '/study-tools', label: 'Study Tools', icon: GraduationCap }
  ];

  return (
    <div className="flex h-screen w-screen bg-[#F8F4EC] text-[#111111] overflow-hidden font-sans antialiased">
      
      {/* DESKTOP SIDEBAR (Perplexity slim-side navigation menu) */}
      <aside className="w-64 bg-[#FCFAF6] border-r border-[#E5DDD0] flex flex-col justify-between hidden md:flex shrink-0 z-20">
        <div>
          {/* Logo & Brand area */}
          <div className="p-5 flex items-center space-x-3 border-b border-[#E5DDD0]/60">
            <div className="p-2 bg-[#18181b] rounded-xl text-white shadow-sm">
              <Brain size={16} className="stroke-[2.5]" />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-bold tracking-tight text-[#18181b]">
                DocumentIQ
              </span>
              <span className="text-[8.5px] text-zinc-500 font-bold tracking-wider uppercase">Enterprise RAG</span>
            </div>
          </div>

          <div className="p-3">
            {/* New Thread button */}
            <Link
              to="/chat"
              className="flex items-center justify-between px-3.5 py-2.5 border border-[#E5DDD0] hover:border-zinc-400 rounded-full bg-[#FCFAF6] hover:bg-[#F8F4EC] text-xs font-semibold transition-all duration-200 shadow-sm cursor-pointer mb-3 group btn-press-active"
            >
              <div className="flex items-center space-x-2">
                <Plus size={14} className="text-zinc-650" />
                <span className="text-zinc-800">New Thread</span>
              </div>
              <kbd className="hidden lg:inline-flex items-center h-4 select-none rounded border border-zinc-100 bg-zinc-50 px-1 font-mono text-[8px] font-medium text-zinc-400">
                ⌘I
              </kbd>
            </Link>

            {/* Navigation Links */}
            <nav className="space-y-1">
              {navLinks.map(({ path, label, icon: Icon }) => (
                <Link key={path} to={path} className={getLinkClass(path)}>
                  <Icon size={15} className={`transition-transform duration-200 group-hover:scale-[1.02] ${isActive(path) ? 'text-[#18181b]' : 'text-zinc-550 group-hover:text-[#18181b]'}`} />
                  <span>{label}</span>
                  {isActive(path) && (
                    <span className="absolute right-3.5 w-1.5 h-1.5 rounded-full bg-[#18181b]"></span>
                  )}
                </Link>
              ))}
            </nav>
          </div>
        </div>

        {/* User profile actions */}
        <div className="p-3.5 border-t border-[#E5DDD0]/60 bg-[#F3EBDD]/20 space-y-3">
          <div className="flex items-center space-x-2.5 px-2 py-1.5 rounded-xl border border-[#E5DDD0] bg-[#FCFAF6]">
            <div className="h-7 w-7 rounded-lg bg-[#F8F4EC] border border-[#E5DDD0] flex items-center justify-center text-[#111111] text-xs font-bold uppercase">
              {user?.email?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="text-[10px] font-bold text-[#111111] truncate">{user?.email}</p>
              <div className="flex items-center space-x-1">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                <span className="text-[8px] text-[#666666] font-bold uppercase tracking-wider">Active Analyst</span>
              </div>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex items-center justify-center space-x-2 w-full py-2 px-3 bg-[#FCFAF6] hover:bg-rose-50 hover:text-rose-600 border border-[#E5DDD0] hover:border-rose-200 rounded-xl text-xs font-bold text-zinc-650 transition-all duration-200 cursor-pointer shadow-sm btn-press-active"
          >
            <LogOut size={12} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* MOBILE NAVIGATION DRAWER */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <div className="fixed inset-0 z-50 bg-black/10 backdrop-blur-xs flex md:hidden">
            <motion.div 
              initial={{ x: -280 }}
              animate={{ x: 0 }}
              exit={{ x: -280 }}
              transition={{ type: 'spring', damping: 25, stiffness: 200 }}
              className="w-64 bg-[#FCFAF6] border-r border-[#E5DDD0] p-5 flex flex-col justify-between h-full shadow-lg"
            >
              <div>
                <div className="flex items-center justify-between pb-4 border-b border-[#e4e4e7]/60">
                  <div className="flex items-center space-x-2.5">
                    <div className="p-2 bg-[#18181b] rounded-lg text-white">
                      <Brain size={14} />
                    </div>
                    <span className="text-md font-bold text-[#18181b]">DocumentIQ</span>
                  </div>
                  <button 
                    onClick={() => setMobileMenuOpen(false)}
                    className="p-1.5 bg-white border border-zinc-250 rounded-lg text-zinc-650"
                  >
                    <X size={15} />
                  </button>
                </div>

                <div className="mt-4">
                  {/* New Thread inside Mobile */}
                  <Link
                    to="/chat"
                    onClick={() => setMobileMenuOpen(false)}
                    className="flex items-center space-x-2 w-full px-3.5 py-2 border border-zinc-200 hover:border-zinc-300 rounded-full bg-white hover:bg-zinc-50 text-xs font-semibold transition-all duration-200 shadow-sm cursor-pointer mb-3"
                  >
                    <Plus size={14} className="text-zinc-650" />
                    <span className="text-zinc-800">New Thread</span>
                  </Link>

                  <nav className="space-y-1">
                    {navLinks.map(({ path, label, icon: Icon }) => (
                      <Link 
                        key={path} 
                        to={path} 
                        onClick={() => setMobileMenuOpen(false)}
                        className={getLinkClass(path)}
                      >
                        <Icon size={15} />
                        <span>{label}</span>
                      </Link>
                    ))}
                  </nav>
                </div>
              </div>

              <div className="space-y-3 pt-4 border-t border-[#e4e4e7]/60">
                <div className="flex items-center space-x-2.5">
                  <div className="h-8 w-8 rounded-lg bg-zinc-200 flex items-center justify-center text-[#18181b] text-xs font-bold uppercase">
                    {user?.email?.charAt(0) || 'U'}
                  </div>
                  <div className="overflow-hidden">
                    <p className="text-[11px] font-bold text-[#18181b] truncate">{user?.email}</p>
                    <p className="text-[9px] text-zinc-500 font-bold">Standard Analyst</p>
                  </div>
                </div>
                <button
                  onClick={logout}
                  className="flex items-center justify-center space-x-2 w-full py-2 px-3 bg-white hover:bg-rose-50 hover:text-rose-600 border border-zinc-200 rounded-xl text-xs font-bold text-zinc-650 transition-all cursor-pointer"
                >
                  <LogOut size={12} />
                  <span>Logout</span>
                </button>
              </div>
            </motion.div>
            <div className="flex-1" onClick={() => setMobileMenuOpen(false)}></div>
          </div>
        )}
      </AnimatePresence>

      {/* MAIN VIEWPORT */}
      <div className="flex-1 flex flex-col overflow-hidden relative z-10 bg-[#F8F4EC]">
        {/* Header toolbar */}
        <header className="h-14 border-b border-[#E5DDD0] bg-[#FCFAF6]/80 backdrop-blur-md px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-2.5 md:hidden">
            <button 
              onClick={() => setMobileMenuOpen(true)}
              className="p-1.5 bg-[#FCFAF6] border border-[#E5DDD0] rounded-xl text-zinc-650 btn-press-active"
            >
              <Menu size={15} />
            </button>
            <span className="text-sm font-bold tracking-tight text-[#111111]">
              DocumentIQ
            </span>
          </div>
          
          <div className="hidden md:flex items-center space-x-2 text-[9px] font-bold text-[#666666] uppercase tracking-widest">
            <span>Workspace</span>
            <span>/</span>
            <span className="text-[#111111]">{location.pathname.replace('/', '') || 'Dashboard'}</span>
          </div>

          <div className="flex items-center space-x-2">
            <a 
              href="https://github.com" 
              target="_blank" 
              rel="noreferrer"
              className="hidden sm:flex items-center space-x-1 text-[10px] font-bold bg-[#FCFAF6] hover:bg-[#F8F4EC] border border-[#E5DDD0] text-zinc-650 px-3 py-1.5 rounded-xl transition-all cursor-pointer shadow-sm btn-press-active animate-fade-in"
            >
              <span>Repository</span>
              <ArrowUpRight size={10} />
            </a>
            <button className="p-1.5 bg-[#FCFAF6] border border-[#E5DDD0] hover:bg-[#F8F4EC] rounded-xl text-zinc-650 transition-all cursor-pointer btn-press-active">
              <HelpCircle size={14} />
            </button>
          </div>
        </header>

        {/* Dynamic page container */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 lg:p-10 grid-paper">
          <div className="max-w-4xl mx-auto space-y-6">
            <AnimatePresence mode="wait">
              <motion.div
                key={location.pathname}
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -4 }}
                transition={{ duration: 0.15, ease: 'easeOut' }}
              >
                {children}
              </motion.div>
            </AnimatePresence>
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
