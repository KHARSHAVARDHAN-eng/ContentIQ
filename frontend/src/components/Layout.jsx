import React, { useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { Link, useLocation } from 'react-router-dom';
import { LogOut, FileText, Brain, Search, User as UserIcon, HelpCircle, BarChart3, Menu, X, ArrowUpRight } from 'lucide-react';

const Layout = ({ children }) => {
  const { user, logout } = useAuth();
  const location = useLocation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const isActive = (path) => location.pathname === path;

  const getLinkClass = (path) =>
    `flex items-center space-x-3 px-4 py-3 rounded-xl font-medium transition-all duration-300 relative group cursor-pointer ${
      isActive(path)
        ? 'bg-indigo-600/10 border border-indigo-500/20 text-indigo-400 font-semibold shadow-[0_0_20px_-3px_rgba(99,102,241,0.12)]'
        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900/50 border border-transparent'
    }`;

  const navLinks = [
    { path: '/dashboard', label: 'Workspace', icon: FileText },
    { path: '/search', label: 'Search Playground', icon: Search },
    { path: '/chat', label: 'Grounded Copilot', icon: Brain },
    { path: '/evaluations', label: 'Evaluation Console', icon: BarChart3 }
  ];

  return (
    <div className="flex h-screen w-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Background ambient lights */}
      <div className="absolute top-[-10%] left-[-10%] w-[40%] h-[40%] bg-indigo-600/5 rounded-full blur-[120px] pointer-events-none animate-pulse-glow"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[40%] h-[40%] bg-cyan-600/5 rounded-full blur-[120px] pointer-events-none animate-pulse-glow" style={{ animationDelay: '1.5s' }}></div>

      {/* DESKTOP SIDEBAR */}
      <aside className="w-66 bg-slate-900/85 backdrop-blur-md border-r border-slate-900 flex flex-col justify-between hidden md:flex shrink-0 relative z-20">
        <div>
          {/* Logo Brand area */}
          <div className="p-6 flex items-center space-x-3 border-b border-slate-900/50">
            <div className="p-2 bg-gradient-to-tr from-indigo-600 to-indigo-500 rounded-xl text-white shadow-lg shadow-indigo-600/20 animate-float">
              <Brain size={20} className="stroke-[2.5]" />
            </div>
            <div className="flex flex-col">
              <span className="text-lg font-bold tracking-tight bg-gradient-to-r from-slate-100 via-indigo-200 to-cyan-300 bg-clip-text text-transparent">
                DocumentIQ
              </span>
              <span className="text-[10px] text-slate-500 font-bold tracking-wider uppercase">Enterprise RAG</span>
            </div>
          </div>

          {/* Navigation links */}
          <nav className="p-4 space-y-1.5">
            {navLinks.map(({ path, label, icon: Icon }) => (
              <Link key={path} to={path} className={getLinkClass(path)}>
                <Icon size={18} className={`transition-transform duration-300 group-hover:scale-105 ${isActive(path) ? 'text-indigo-400' : 'text-slate-450 group-hover:text-indigo-400'}`} />
                <span>{label}</span>
                {isActive(path) && (
                  <span className="absolute right-3 w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse"></span>
                )}
              </Link>
            ))}
          </nav>
        </div>

        {/* User profile & action panel */}
        <div className="p-4 border-t border-slate-900/50 space-y-4 bg-slate-900/20">
          <div className="flex items-center space-x-3 px-2 py-1.5 rounded-xl bg-slate-950/20 border border-slate-900/30">
            <div className="h-9 w-9 rounded-xl bg-gradient-to-br from-indigo-500/20 to-cyan-500/10 border border-indigo-500/30 flex items-center justify-center text-indigo-400 text-sm font-bold uppercase shadow-inner">
              {user?.email?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="text-xs font-semibold text-slate-200 truncate">{user?.email}</p>
              <div className="flex items-center space-x-1 mt-0.5">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-ping"></span>
                <span className="text-[9px] text-slate-500 font-extrabold uppercase tracking-widest">Active session</span>
              </div>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex items-center justify-center space-x-2 w-full py-2.5 px-4 bg-slate-950/50 hover:bg-rose-950/20 hover:text-rose-400 border border-slate-900 hover:border-rose-500/20 rounded-xl text-xs font-bold transition-all duration-300 cursor-pointer shadow-sm"
          >
            <LogOut size={14} />
            <span>Sign Out</span>
          </button>
        </div>
      </aside>

      {/* MOBILE NAV MENU */}
      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-md flex md:hidden animate-fade-in">
          <div className="w-72 bg-slate-900 border-r border-slate-800 p-6 flex flex-col justify-between h-full">
            <div>
              <div className="flex items-center justify-between pb-6 border-b border-slate-800">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-indigo-600 rounded-lg text-white">
                    <Brain size={20} />
                  </div>
                  <span className="text-lg font-bold text-white">DocumentIQ</span>
                </div>
                <button 
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-1.5 bg-slate-950 border border-slate-800 rounded-lg text-slate-400"
                >
                  <X size={18} />
                </button>
              </div>

              <nav className="mt-6 space-y-2">
                {navLinks.map(({ path, label, icon: Icon }) => (
                  <Link 
                    key={path} 
                    to={path} 
                    onClick={() => setMobileMenuOpen(false)}
                    className={getLinkClass(path)}
                  >
                    <Icon size={18} />
                    <span>{label}</span>
                  </Link>
                ))}
              </nav>
            </div>

            <div className="space-y-4 pt-6 border-t border-slate-800">
              <div className="flex items-center space-x-3">
                <div className="h-9 w-9 rounded-lg bg-indigo-600/20 flex items-center justify-center text-indigo-400 text-sm font-semibold uppercase">
                  {user?.email?.charAt(0) || 'U'}
                </div>
                <div className="overflow-hidden">
                  <p className="text-xs font-semibold text-slate-200 truncate">{user?.email}</p>
                  <p className="text-[10px] text-slate-500 font-medium">Standard Analyst</p>
                </div>
              </div>
              <button
                onClick={logout}
                className="flex items-center justify-center space-x-2 w-full py-2.5 px-4 bg-slate-950 hover:bg-rose-950/40 hover:text-rose-400 border border-slate-800 hover:border-rose-500/25 rounded-xl text-xs font-bold transition-all cursor-pointer"
              >
                <LogOut size={14} />
                <span>Logout</span>
              </button>
            </div>
          </div>
          <div className="flex-1" onClick={() => setMobileMenuOpen(false)}></div>
        </div>
      )}

      {/* MAIN CONTENT AREA */}
      <div className="flex-1 flex flex-col overflow-hidden relative z-10">
        {/* Top Header */}
        <header className="h-16 border-b border-slate-900 bg-slate-950/45 backdrop-blur-md px-6 flex items-center justify-between shrink-0">
          <div className="flex items-center space-x-3 md:hidden">
            <button 
              onClick={() => setMobileMenuOpen(true)}
              className="p-2 bg-slate-900 border border-slate-800 rounded-xl text-slate-300"
            >
              <Menu size={18} />
            </button>
            <span className="text-md font-bold tracking-tight bg-gradient-to-r from-slate-100 via-indigo-200 to-indigo-400 bg-clip-text text-transparent">
              DocumentIQ
            </span>
          </div>
          
          <div className="hidden md:flex items-center space-x-2 text-xs font-bold text-slate-500 uppercase tracking-widest">
            <span>Platform</span>
            <span>/</span>
            <span className="text-indigo-400/90">{location.pathname.replace('/', '') || 'Workspace'}</span>
          </div>

          <div className="flex items-center space-x-3">
            <a 
              href="https://github.com" 
              target="_blank" 
              rel="noreferrer"
              className="hidden sm:flex items-center space-x-1 text-xs font-semibold bg-slate-900 hover:bg-slate-850 border border-slate-800 hover:border-indigo-500/20 text-slate-400 hover:text-slate-200 px-3 py-1.5 rounded-xl transition-all cursor-pointer"
            >
              <span>Repo Documentation</span>
              <ArrowUpRight size={12} />
            </a>
            <button className="p-2 bg-slate-900/50 hover:bg-slate-900 border border-slate-900 hover:border-slate-800 rounded-xl text-slate-400 hover:text-slate-200 transition-all cursor-pointer">
              <HelpCircle size={18} />
            </button>
          </div>
        </header>

        {/* Page Content viewport */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 lg:p-8 bg-gradient-to-b from-slate-950 via-slate-950 to-slate-950">
          <div className="max-w-6xl mx-auto space-y-6 animate-slide-up">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
