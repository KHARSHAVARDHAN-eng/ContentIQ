let rawApiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// If VITE_API_URL is configured without the /api suffix, dynamically append it.
if (rawApiUrl && !rawApiUrl.endsWith('/api') && !rawApiUrl.endsWith('/api/')) {
  // Strip trailing slash if present, then append /api
  rawApiUrl = rawApiUrl.replace(/\/$/, '') + '/api';
}

export const API_URL = rawApiUrl;
