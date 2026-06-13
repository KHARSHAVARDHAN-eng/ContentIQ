import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Brain, Mail, Lock, AlertCircle, ArrowRight } from 'lucide-react';
import { motion } from 'framer-motion';

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
    <div className="min-h-screen w-screen flex items-center justify-center bg-[#fafafa] relative overflow-hidden font-sans select-none">
      
      {/* Background decoration blur */}
      <div className="absolute inset-0 z-0 flex items-center justify-center opacity-30 pointer-events-none">
        <div className="w-[600px] h-[600px] rounded-full bg-zinc-200/40 blur-3xl"></div>
      </div>

      {/* Register Card */}
      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.25, ease: 'easeOut' }}
        className="w-full max-w-[380px] p-8 bg-white border border-zinc-200/80 rounded-3xl shadow-sm relative z-10 mx-4"
      >
        {/* Header */}
        <div className="flex flex-col items-center space-y-3 mb-6">
          <div className="p-2.5 bg-[#18181b] rounded-xl text-white shadow-sm">
            <Brain size={20} className="stroke-[2.5]" />
          </div>
          <div className="text-center space-y-1">
            <h1 className="text-lg font-bold text-[#18181b] tracking-tight">
              Create Account
            </h1>
            <p className="text-zinc-500 text-xs font-semibold">Join the DocumentIQ indexing workspace</p>
          </div>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {activeError && (
            <div className="flex items-start space-x-2.5 p-3 bg-rose-50 border border-rose-100 rounded-xl text-rose-700 text-xs leading-relaxed animate-fade-in shadow-sm">
              <AlertCircle size={14} className="shrink-0 mt-0.5" />
              <span>{activeError}</span>
            </div>
          )}

          <div className="space-y-1">
            <label className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider pl-1">Email Address</label>
            <div className="relative">
              <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400" size={14} />
              <input
                id="register-email-input"
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="analyst@documentiq.ai"
                className="w-full pl-10 pr-4 py-2.5 bg-zinc-50/50 border border-zinc-200 hover:border-zinc-300 focus:border-[#18181b] focus:bg-white rounded-xl text-[#18181b] text-xs placeholder-zinc-400 transition-all outline-none"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider pl-1">Password</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400" size={14} />
              <input
                id="register-password-input"
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="Create password (min 6 chars)"
                className="w-full pl-10 pr-4 py-2.5 bg-zinc-50/50 border border-zinc-200 hover:border-zinc-300 focus:border-[#18181b] focus:bg-white rounded-xl text-[#18181b] text-xs placeholder-zinc-400 transition-all outline-none"
              />
            </div>
          </div>

          <div className="space-y-1">
            <label className="text-[9px] font-bold text-zinc-500 uppercase tracking-wider pl-1">Verify Password</label>
            <div className="relative">
              <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 text-zinc-400" size={14} />
              <input
                id="register-confirm-password-input"
                type="password"
                required
                value={confirmPassword}
                onChange={(e) => setConfirmPassword(e.target.value)}
                placeholder="Re-enter security password"
                className="w-full pl-10 pr-4 py-2.5 bg-zinc-50/50 border border-zinc-200 hover:border-zinc-300 focus:border-[#18181b] focus:bg-white rounded-xl text-[#18181b] text-xs placeholder-zinc-400 transition-all outline-none"
              />
            </div>
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full mt-3 py-2.5 bg-[#18181b] hover:bg-zinc-800 disabled:bg-zinc-100 disabled:text-zinc-400 text-white font-bold rounded-full shadow-sm transition-all duration-200 flex items-center justify-center space-x-2 cursor-pointer text-xs uppercase tracking-wider btn-press-active"
          >
            {isSubmitting ? (
              <div className="h-4 w-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
            ) : (
              <>
                <span>Register Account</span>
                <ArrowRight size={13} />
              </>
            )}
          </button>
        </form>

        <p className="mt-5 text-center text-xs text-zinc-500 font-semibold">
          Already registered?{' '}
          <Link to="/login" className="font-bold text-[#18181b] hover:underline uppercase tracking-wider pl-1">
            Sign In
          </Link>
        </p>
      </motion.div>
    </div>
  );
};

export default Register;
