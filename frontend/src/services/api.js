/**
 * API Service for backend communication
 */
import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000';

// Create axios instance
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Handle 401 errors (token expired)
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post(`${API_BASE_URL}/api/auth/refresh`, {
          refresh_token: refreshToken,
        });

        const { access_token, refresh_token } = response.data;
        localStorage.setItem('access_token', access_token);
        localStorage.setItem('refresh_token', refresh_token);

        originalRequest.headers.Authorization = `Bearer ${access_token}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, logout user
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  register: (userData) => api.post('/api/auth/register', userData),
  login: (credentials) => api.post('/api/auth/login', credentials),
  logout: () => api.post('/api/auth/logout'),
  getCurrentUser: () => api.get('/api/auth/me'),
};

// User API
export const userAPI = {
  getProfile: () => api.get('/api/users/profile'),
  updateProfile: (data) => api.put('/api/users/profile', data),
  changePassword: (data) => api.post('/api/users/change-password', data),
  deleteAccount: () => api.delete('/api/users/account'),
  getUploadCount: () => api.get('/api/users/history/count'),
};

// Prediction API
export const predictionAPI = {
  analyzeImage: (formData) =>
    api.post('/api/prediction/analyze', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  getHistory: (skip = 0, limit = 20) =>
    api.get(`/api/prediction/history?skip=${skip}&limit=${limit}`),
  getDetail: (predictionId) => api.get(`/api/prediction/history/${predictionId}`),
  deletePrediction: (predictionId) => api.delete(`/api/prediction/history/${predictionId}`),
};

// Analytics API
export const analyticsAPI = {
  getSummary: () => api.get('/api/analytics/summary'),
  getTrends: (days = 7) => api.get(`/api/analytics/trends?days=${days}`),
  getEmotionBreakdown: () => api.get('/api/analytics/emotion-breakdown'),
  getAgeDistribution: () => api.get('/api/analytics/age-distribution'),
};

// Reports API
export const reportsAPI = {
  generate: (predictionId) => api.post('/api/reports/generate', { prediction_id: predictionId }),
  download: (reportId) => api.get(`/api/reports/download/${reportId}`, { responseType: 'blob' }),
  list: (skip = 0, limit = 20) => api.get(`/api/reports/list?skip=${skip}&limit=${limit}`),
  delete: (reportId) => api.delete(`/api/reports/${reportId}`),
};

// Admin API
export const adminAPI = {
  listUsers: (skip = 0, limit = 50) => api.get(`/api/admin/users?skip=${skip}&limit=${limit}`),
  listPredictions: (skip = 0, limit = 50) =>
    api.get(`/api/admin/predictions?skip=${skip}&limit=${limit}`),
  deletePrediction: (predictionId) => api.delete(`/api/admin/predictions/${predictionId}`),
  toggleUserActive: (userId) => api.put(`/api/admin/users/${userId}/toggle-active`),
  getStats: () => api.get('/api/admin/stats'),
  getDashboard: () => api.get('/api/admin/dashboard'),
};

// Models API
export const modelsAPI = {
  list: () => api.get('/api/models/list'),
  getActive: () => api.get('/api/models/active'),
  activate: (modelId) => api.put(`/api/models/${modelId}/activate`),
  getPerformance: (modelId) => api.get(`/api/models/${modelId}/performance`),
};

export default api;
