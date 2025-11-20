import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authAPI = {
  login: async (email, password) => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },

  loginWith2FA: async (email, password, totp_code = null) => {
    const response = await api.post('/auth/login-2fa', { email, password, totp_code });
    return response.data;
  },

  register: async (email, name, password, role = 'citizen') => {
    const response = await api.post('/auth/register', { email, name, password, role });
    return response.data;
  },

  getCurrentUser: async () => {
    const response = await api.get('/auth/me');
    return response.data;
  },

  logout: async () => {
    const response = await api.post('/auth/logout');
    return response.data;
  },

  enable2FA: async () => {
    const response = await api.post('/auth/2fa/enable');
    return response.data;
  },

  verify2FA: async (code) => {
    const response = await api.post('/auth/2fa/verify', { code });
    return response.data;
  },

  disable2FA: async (code) => {
    const response = await api.post('/auth/2fa/disable', { code });
    return response.data;
  },

  requestPasswordReset: async (email) => {
    const response = await api.post('/auth/password/reset-request', { email });
    return response.data;
  },

  confirmPasswordReset: async (token, new_password) => {
    const response = await api.post('/auth/password/reset-confirm', { token, new_password });
    return response.data;
  },
};

export const casesAPI = {
  getCases: async (params = {}) => {
    const response = await api.get('/cases/', { params });
    return response.data;
  },

  getCase: async (caseId) => {
    const response = await api.get(`/cases/${caseId}`);
    return response.data;
  },

  createCase: async (caseData) => {
    const response = await api.post('/cases/', caseData);
    return response.data;
  },

  updateCase: async (caseId, caseData) => {
    const response = await api.put(`/cases/${caseId}`, caseData);
    return response.data;
  },

  deleteCase: async (caseId) => {
    const response = await api.delete(`/cases/${caseId}`);
    return response.data;
  },

  getCaseStats: async () => {
    const response = await api.get('/cases/stats/summary');
    return response.data;
  },
};

export const documentsAPI = {
  uploadDocument: async (file, caseId = null) => {
    const formData = new FormData();
    formData.append('file', file);
    if (caseId) {
      formData.append('case_id', caseId);
    }

    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  getDocuments: async (params = {}) => {
    const response = await api.get('/documents/', { params });
    return response.data;
  },

  getDocument: async (documentId) => {
    const response = await api.get(`/documents/${documentId}`);
    return response.data;
  },

  downloadDocument: async (documentId) => {
    const response = await api.get(`/documents/${documentId}/download`, {
      responseType: 'blob',
    });
    return response.data;
  },

  deleteDocument: async (documentId) => {
    const response = await api.delete(`/documents/${documentId}`);
    return response.data;
  },

  updateDocumentOCR: async (documentId, ocrText) => {
    const response = await api.put(`/documents/${documentId}/ocr`, { ocr_text: ocrText });
    return response.data;
  },
};

export default api;
