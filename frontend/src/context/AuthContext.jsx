import React, { createContext, useState, useEffect, useContext } from 'react';
import axios from 'axios';

const AuthContext = createContext(null);

import { API_URL } from '../config';

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem('token') || null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  // Set axios global Authorization header & request interceptor
  useEffect(() => {
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
    } else {
      delete axios.defaults.headers.common['Authorization'];
    }

    const reqInterceptor = axios.interceptors.request.use((config) => {
      const storedToken = localStorage.getItem('token');
      if (storedToken && !config.headers['Authorization']) {
        config.headers['Authorization'] = `Bearer ${storedToken}`;
      }
      return config;
    });

    const resInterceptor = axios.interceptors.response.use(
      (response) => response,
      (err) => {
        if (err.response && (err.response.status === 401 || err.response.status === 403)) {
          if (localStorage.getItem('token')) {
            localStorage.removeItem('token');
            setToken(null);
            setUser(null);
          }
        }
        return Promise.reject(err);
      }
    );

    return () => {
      axios.interceptors.request.eject(reqInterceptor);
      axios.interceptors.response.eject(resInterceptor);
    };
  }, [token]);

  const fetchUserProfile = async (authToken) => {
    try {
      const response = await axios.get(`${API_URL}/users/me`, {
        headers: { Authorization: `Bearer ${authToken}` }
      });
      setUser(response.data);
    } catch (err) {
      console.error("Failed to fetch user profile:", err);
      logout();
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (token) {
      fetchUserProfile(token);
    } else {
      setIsLoading(false);
    }
  }, [token]);

  const login = async (email, password) => {
    setError(null);
    try {
      const response = await axios.post(`${API_URL}/auth/login`, { email, password });
      const { access_token } = response.data;
      localStorage.setItem('token', access_token);
      setToken(access_token);
      await fetchUserProfile(access_token);
      return true;
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Login failed. Please check your credentials.';
      setError(errMsg);
      throw new Error(errMsg);
    }
  };

  const register = async (email, password) => {
    setError(null);
    try {
      await axios.post(`${API_URL}/auth/register`, { email, password });
      // Automatically log in after registration
      return await login(email, password);
    } catch (err) {
      const errMsg = err.response?.data?.detail || 'Registration failed.';
      setError(errMsg);
      throw new Error(errMsg);
    }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
  };

  const value = {
    user,
    token,
    isLoading,
    error,
    isAuthenticated: !!token && !!user,
    login,
    register,
    logout,
    setError
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
