import axios from 'axios';
import { LoginCredentials, LoginResponse } from '../types/auth';

const API_URL = '/api';

// Create axios instance
const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add authorization header to requests when token is available
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    // Explicitly add Bearer to the token
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authService = {
  login: async (credentials: LoginCredentials): Promise<string> => {
    try {
      // The Basic Auth is required according to the auth-service implementation
      const auth = btoa(`${credentials.username}:${credentials.password}`);
      const response = await api.post<string>('/login', {}, {
        headers: {
          Authorization: `Basic ${auth}`,
        },
      });
      
      // Store the raw token without Bearer
      localStorage.setItem('token', response.data);
      return response.data;
    } catch (error) {
      console.error('Login error:', error);
      throw error;
    }
  },
  
  logout: () => {
    localStorage.removeItem('token');
  },
  
  isAuthenticated: (): boolean => {
    return localStorage.getItem('token') !== null;
  }
};

export const uploadService = {
  uploadVideo: async (file: File): Promise<string> => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      
      const response = await api.post<string>('/upload', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      
      return response.data;
    } catch (error) {
      console.error('Upload error:', error);
      throw error;
    }
  }
};

export default api;