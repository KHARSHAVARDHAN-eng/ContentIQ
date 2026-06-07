import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Brain, Mail, Lock, AlertCircle, ArrowRight } from 'lucide-react';

const Register = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [validationError, setValidationError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { register, isAuthenticated, error, setError } = useAuth();
  const navigate = useNavigate();

  useEffect(() => {
    setError(null);
    if (isAuthenticated) {
      navigate('/dashboard');
    }
  }, [isAuthenticated, navigate, setError]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setValidationError('');

    if (!email || !password || !confirmPassword) return;

    if (password !== confirmPassword) {
      setValidationError('Passwords do not match.');
      return;
    }

    if (password.length < 6) {
      setValidationError('Password must be at least 6 characters.');
      return;
    }

    setIsSubmitting(true);
    try {
      await register(email, password);
      navigate('/dashboard');
    } catch (err) {
      console.error(err);
    } finally {
      setIsSubmitting(false);
    }
  };

  const activeError = validationError || error;

  return (
    <div className="min-h-screen w-screen flex items-center justify-center bg-slate-950 relative overflow-hidden font-sans select-none">
      {/* Background glowing decorations */}
      <div className="absolute top-[-10%] left-[-10%] w-[50%] h-[50%] bg-indigo-600/10 rounded-full blur-[140px] pointer-events-none animate-pulse-glow"></div>
      <div className="absolute bottom-[-10%] right-[-10%] w-[50%] h-[50%] bg-cyan-600/10 rounded-full blur-[140px] pointer-events-none animate-pulse-glow" style={{ animationDelay: '2s' }}></div>

      {/* Register Container Card */}
      <div className="w-full max-w-[420px] p-8 bg-slate-900/60 backdrop-blur-xl border border-slate-900 rounded-3xl shadow-2xl relative z-10 mx-4 animate-slide-up">
        {/* Header */}
        <div className="flex flex-col items-center space-y-3 mb-8">
          <div className="p-3 bg-gradient-to-tr from-indigo-600 to-indigo-500 rounded-2xl text-white shadow-lg shadow-indigo-600/30 animate-float">
            <Brain size={28} className="stroke-[2.5]" />
          </div>
          <div className="text-center space-y-1">
            <h1 className="text-2xl font-extrabold text-slate-100 tracking-tight bg-gradient-to-r from-slate-100 via-indigo-100 to-cyan-200 bg-clip-text text-transparent">
              Register Account
            </h1>
            <p className="text-slate-455 text-xs font-semibold">Get started with DocumentIQ</p>
          </div>
        </div>

        {/* Form fields */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {activeError && (
            <div className="flex items-start space-x-2.5 p-3.5 bg-rose-500/5 border border-rose-500/15 rounded-2xl text-rose-455 text-xs leading-relaxed animate-fade-in">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <span>{activeError}</span>
            </div>
          )}

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider pl-1">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-650" size={16} />
              <input
                id="register-email-input"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="developer@documentiq.io"
                className="w-full pl-11 pr-4 py-3 bg-slate-950/70 border border-slate-850 hover:border-slate-800 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 rounded-2xl text-slate-200 text-xs md:text-sm placeholder-slate-650 transition-all outline-none"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider pl-1">Password</label>
            <div className="relative">
              <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-650" size={16} />
              <input
                id="register-password-input"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Choose security key (min 6 chars)"
                className="w-full pl-11 pr-4 py-3 bg-slate-950/70 border border-slate-850 hover:border-slate-800 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 rounded-2xl text-slate-200 text-xs md:text-sm placeholder-slate-650 transition-all outline-none"
              />
            </div>
          </div>

          <div className="space-y-1.5">
            <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider pl-1">Confirm Password</label>
            <div className="relative">
              <Lock className="absolute left-4 top-1/2 -translate-y-1/2 text-slate-650" size={16} />
              <input
                id="register-confirm-password-input"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Verify security key matches"
                className="w-full pl-11 pr-4 py-3 bg-slate-950/70 border border-slate-855 hover:border-slate-800 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-500/10 rounded-2xl text-slate-200 text-xs md:text-sm placeholder-slate-650 transition-all outline-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-3 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-800/80 text-white font-bold rounded-2xl shadow-lg shadow-indigo-600/10 hover:shadow-indigo-600/20 transition-all duration-300 flex items-center justify-center space-x-2 cursor-pointer text-xs md:text-sm uppercase tracking-wider"
          >
            {isSubmitting ? (
              <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <>
                <span>Register Account</span>
                <ArrowRight size={14} />
              </>
            )}
          </button>
        </form>

        {/* Navigation link footer */}
        <p className="mt-6 text-center text-xs text-slate-500 font-medium">
          Already registered?{' '}
          <Link to="/login" className="font-bold text-indigo-400 hover:text-indigo-300 transition-colors uppercase tracking-wider pl-1">
            Sign In
          </Link>
        </p>
      </div>
    </div>
  );
};

export default Register;
