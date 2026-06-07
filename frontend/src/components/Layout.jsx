import React from 'react';
import { useAuth } from '../context/AuthContext';
import { Link, useLocation } from 'react-router-dom';
import { LogOut, FileText, Brain, Search, User as UserIcon, HelpCircle } from 'lucide-react';

const Layout = ({ children }) => {
  const { user, logout } = useAuth();
  const location = useLocation();

  const isActive = (path) => location.pathname === path;

  const getLinkClass = (path) =>
    `flex items-center space-x-3 px-4 py-3 rounded-xl font-medium transition-all duration-200 cursor-pointer ${
      isActive(path)
        ? 'bg-slate-850 border border-slate-700/50 text-indigo-400 font-semibold shadow-lg shadow-indigo-500/5'
        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/40 border border-transparent'
    }`;

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100 overflow-hidden font-sans">
      {/* Sidebar */}
      <aside className="w-64 bg-slate-900 border-r border-slate-800 flex flex-col justify-between hidden md:flex">
        <div>
          {/* Logo */}
          <div className="p-6 flex items-center space-x-3 border-b border-slate-800">
            <div className="p-2 bg-indigo-600 rounded-lg text-white">
              <Brain size={24} />
            </div>
            <span className="text-xl font-bold tracking-wider bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              DocumentIQ
            </span>
          </div>

          {/* Navigation Links */}
          <nav className="p-4 space-y-2">
            <Link to="/dashboard" className={getLinkClass('/dashboard')}>
              <FileText size={20} />
              <span>Workspace</span>
            </Link>
            <Link to="/search" className={getLinkClass('/search')}>
              <Search size={20} />
              <span>Search Playground</span>
            </Link>
            <Link to="/chat" className={getLinkClass('/chat')}>
              <Brain size={20} />
              <span>Chat Assistant</span>
            </Link>

            <a href="#" className="flex items-center space-x-3 px-4 py-3 hover:bg-slate-800/40 rounded-xl text-slate-400 hover:text-slate-200 font-medium transition-all duration-200">
              <UserIcon size={20} />
              <span>Account</span>
            </a>
          </nav>
        </div>


        {/* User Info & Logout */}
        <div className="p-4 border-t border-slate-800 space-y-4">
          <div className="flex items-center space-x-3 px-2">
            <div className="h-10 w-10 rounded-full bg-indigo-600/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 font-semibold uppercase">
              {user?.email?.charAt(0) || 'U'}
            </div>
            <div className="flex-1 overflow-hidden">
              <p className="text-sm font-medium text-slate-200 truncate">{user?.email}</p>
              <p className="text-xs text-slate-500 truncate">Pro Analyst</p>
            </div>
          </div>
          <button
            onClick={logout}
            className="flex items-center justify-center space-x-2 w-full py-2.5 px-4 bg-slate-850 hover:bg-rose-950/40 hover:text-rose-400 border border-slate-700 hover:border-rose-500/20 rounded-xl text-sm font-medium transition-all duration-300 cursor-pointer"
          >
            <LogOut size={16} />
            <span>Logout</span>
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Top Header for Mobile & Quick Actions */}
        <header className="h-16 bg-slate-900 border-b border-slate-800 px-6 flex items-center justify-between">
          <div className="flex items-center space-x-3 md:hidden">
            <div className="p-1.5 bg-indigo-600 rounded text-white">
              <Brain size={20} />
            </div>
            <span className="text-lg font-bold tracking-wider text-slate-200">DocumentIQ</span>
          </div>
          <div className="hidden md:block text-sm text-slate-400 font-medium">
            Project Workspace
          </div>
          <div className="flex items-center space-x-4">
            <button className="p-2 text-slate-400 hover:text-slate-200 transition-colors">
              <HelpCircle size={20} />
            </button>
            <button
              onClick={logout}
              className="md:hidden p-2 text-slate-400 hover:text-rose-400 transition-colors"
            >
              <LogOut size={20} />
            </button>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto p-6 md:p-8 bg-slate-950">
          <div className="max-w-6xl mx-auto space-y-8">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
};

export default Layout;
