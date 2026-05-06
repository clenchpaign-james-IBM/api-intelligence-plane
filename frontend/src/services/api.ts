/**
 * API Client Service
 * 
 * Provides a centralized HTTP client for all backend API calls.
 * Features:
 * - Base URL configuration from environment
 * - Request/response interceptors
 * - Error handling and transformation
 * - Type-safe API methods
 */

import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig, AxiosResponse } from 'axios';

// API Response types
export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  status: number;
}

export interface ApiError {
  message: string;
  status: number;
  details?: any;
}

// API Client Configuration
// Use relative path in production/Docker (goes through Vite proxy)
// Use full URL in development when running frontend standalone
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';
const API_TIMEOUT = 120000; // 120 seconds (2 minutes) - increased for LLM query processing

/**
 * Create and configure Axios instance
 */
const createApiClient = (): AxiosInstance => {
  const client = axios.create({
    baseURL: API_BASE_URL,
    timeout: API_TIMEOUT,
    headers: {
      'Content-Type': 'application/json',
    },
  });

  // Request interceptor
  client.interceptors.request.use(
    (config: InternalAxiosRequestConfig) => {
      // Add authentication token if available
      const token = localStorage.getItem('auth_token');
      if (token && config.headers) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      // Log request in development
      if (import.meta.env.DEV) {
        console.log(`[API Request] ${config.method?.toUpperCase()} ${config.url}`, {
          params: config.params,
          data: config.data,
        });
      }

      return config;
    },
    (error: AxiosError) => {
      console.error('[API Request Error]', error);
      return Promise.reject(error);
    }
  );

  // Response interceptor
  client.interceptors.response.use(
    (response: AxiosResponse) => {
      // Log response in development
      if (import.meta.env.DEV) {
        console.log(`[API Response] ${response.config.method?.toUpperCase()} ${response.config.url}`, {
          status: response.status,
          data: response.data,
        });
      }

      return response;
    },
    (error: AxiosError) => {
      // Transform error for consistent handling
      const apiError: ApiError = {
        message: error.message || 'An unexpected error occurred',
        status: error.response?.status || 500,
        details: error.response?.data,
      };

      // Handle specific error cases
      if (error.response?.status === 401) {
        // Unauthorized - clear token and redirect to login
        localStorage.removeItem('auth_token');
        window.location.href = '/login';
      } else if (error.response?.status === 403) {
        apiError.message = 'Access forbidden';
      } else if (error.response?.status === 404) {
        apiError.message = 'Resource not found';
      } else if (error.response?.status === 500) {
        apiError.message = 'Internal server error';
      }

      console.error('[API Response Error]', apiError);
      return Promise.reject(apiError);
    }
  );

  return client;
};

// Create singleton instance
const apiClient = createApiClient();

/**
 * API Service Methods
 */
export const api = {
  // Generic HTTP methods
  get: <T = any>(url: string, params?: any): Promise<T> =>
    apiClient.get(url, { params }).then((res) => res.data),

  post: <T = any>(url: string, data?: any): Promise<T> =>
    apiClient.post(url, data).then((res) => res.data),

  put: <T = any>(url: string, data?: any): Promise<T> =>
    apiClient.put(url, data).then((res) => res.data),

  patch: <T = any>(url: string, data?: any): Promise<T> =>
    apiClient.patch(url, data).then((res) => res.data),

  delete: <T = any>(url: string): Promise<T> =>
    apiClient.delete(url).then((res) => res.data),

  // Health check
  health: () => api.get('/health'),

  // Gateway endpoints
  gateways: {
    list: () => api.get('/api/v1/gateways'),
    get: (id: string) => api.get(`/api/v1/gateways/${id}`),
    create: (data: any) => api.post('/api/v1/gateways', data),
    update: (id: string, data: any) => api.put(`/api/v1/gateways/${id}`, data),
    delete: (id: string) => api.delete(`/api/v1/gateways/${id}`),
    sync: (id: string) => api.post(`/api/v1/gateways/${id}/sync`),
    connect: (id: string) => api.post(`/api/v1/gateways/${id}/connect`),
    disconnect: (id: string) => api.post(`/api/v1/gateways/${id}/disconnect`),
    testConnection: (data: any) => api.post('/api/v1/gateways/test-connection', data),
    bulkSync: (gatewayIds: string[], forceRefresh: boolean = false) => {
      const queryParams = new URLSearchParams();
      if (forceRefresh) queryParams.append('force_refresh', 'true');
      return api.post(`/api/v1/gateways/bulk-sync?${queryParams.toString()}`, gatewayIds);
    },
  },

  // API endpoints (gateway-scoped)
  apis: {
    list: (params?: any) => api.get('/api/v1/apis', params),
    get: (id: string) => api.get(`/api/v1/apis/${id}`),
    search: (query: string, gatewayId?: string) => {
      const params: any = { query };
      if (gatewayId) params.gateway_id = gatewayId;
      return api.get('/api/v1/apis/search', params);
    },
    // Get security policies for an API (derived from policy_actions)
    getSecurityPolicies: (id: string) => api.get(`/api/v1/apis/${id}/security-policies`),
  },

  // Metrics endpoints (gateway-scoped)
  metrics: {
    list: (params?: any) => api.get('/api/v1/metrics', params),
    get: (id: string) => api.get(`/api/v1/metrics/${id}`),
    aggregate: (params: any) => api.post('/api/v1/metrics/aggregate', params),
  },

  // Predictions endpoints (gateway-scoped)
  predictions: {
    list: (params?: any) => api.get('/api/v1/predictions', params),
    get: (id: string) => api.get(`/api/v1/predictions/${id}`),
    create: (data: any) => api.post('/api/v1/predictions', data),
    getExplanation: (id: string) => api.get(`/api/v1/predictions/${id}/explanation`),
  },

  // Security endpoints (gateway-scoped)
  security: {
    vulnerabilities: {
      list: (params?: any) => api.get('/api/v1/security/vulnerabilities', params),
      get: (id: string) => api.get(`/api/v1/security/vulnerabilities/${id}`),
      scan: (apiId: string, gatewayId?: string) => {
        const params: any = {};
        if (gatewayId) params.gateway_id = gatewayId;
        return api.post(`/api/v1/security/scan/${apiId}`, params);
      },
    },
  },

  // Optimization recommendations endpoints (gateway-scoped)
  recommendations: {
    list: (params?: any) => api.get('/api/v1/recommendations', params),
    get: (id: string) => api.get(`/api/v1/recommendations/${id}`),
    generate: (apiId: string, minImpact?: number, useAi?: boolean, gatewayId?: string) => {
      const params: any = { api_id: apiId };
      if (minImpact !== undefined) params.min_impact = minImpact;
      if (useAi !== undefined) params.use_ai = useAi;
      if (gatewayId) params.gateway_id = gatewayId;
      return api.post('/api/v1/recommendations/generate', params);
    },
    stats: (params?: any) => api.get('/api/v1/recommendations/stats', params),
    // Apply recommendation policy to Gateway (legacy endpoint)
    apply: (id: string) => api.post(`/api/v1/recommendations/${id}/apply`),
    
    // Gateway-scoped remediation endpoints
    previewPolicy: (gatewayId: string, recommendationId: string) =>
      api.post(`/api/v1/gateways/${gatewayId}/optimization/recommendations/${recommendationId}/preview`),
    
    applyToGateway: (gatewayId: string, recommendationId: string, overrideRequest?: {
      override_config?: Record<string, any>;
      manual_analysis?: {
        reason?: string;
        risk_acknowledgement?: string;
        reviewed_by?: string;
      };
    }) =>
      api.post(`/api/v1/gateways/${gatewayId}/optimization/recommendations/${recommendationId}/apply`, overrideRequest),
    
    removeFromGateway: (gatewayId: string, recommendationId: string) =>
      api.delete(`/api/v1/gateways/${gatewayId}/optimization/recommendations/${recommendationId}/policy`),
    
    validate: (gatewayId: string, recommendationId: string, validationWindowHours: number = 24) =>
      api.post(
        `/api/v1/gateways/${gatewayId}/optimization/recommendations/${recommendationId}/validate?validation_window_hours=${validationWindowHours}`
      ),
    
    getActions: (gatewayId: string, recommendationId: string) =>
      api.get(`/api/v1/gateways/${gatewayId}/optimization/recommendations/${recommendationId}/actions`),
    
    // AI-enhanced endpoints
    generateAiEnhanced: (apiId: string, minImpact?: number, gatewayId?: string) => {
      const params: any = { api_id: apiId };
      if (minImpact !== undefined) params.min_impact = minImpact;
      if (gatewayId) params.gateway_id = gatewayId;
      return api.post('/api/v1/optimization/ai-enhanced', params);
    },
    getInsights: (id: string) => api.get(`/api/v1/optimization/${id}/insights`),
  },

  // Rate limit endpoints (gateway-scoped)
  rateLimits: {
    list: (params?: any) => api.get('/api/v1/rate-limits', params),
    get: (id: string) => api.get(`/api/v1/rate-limits/${id}`),
    create: (data: any) => api.post('/api/v1/rate-limits', data),
    activate: (id: string) => api.post(`/api/v1/rate-limits/${id}/activate`),
    deactivate: (id: string) => api.post(`/api/v1/rate-limits/${id}/deactivate`),
    apply: (id: string) => api.post(`/api/v1/rate-limits/${id}/apply`),
    suggest: (apiId: string, gatewayId?: string) => {
      const params: any = {};
      if (gatewayId) params.gateway_id = gatewayId;
      return api.get(`/api/v1/rate-limits/suggest/${apiId}`, params);
    },
    effectiveness: (id: string) => api.get(`/api/v1/rate-limits/${id}/effectiveness`),
  },

  // Query endpoints
  query: {
    execute: (query: string) => {
      // Use extended timeout for query execution (LLM processing can take time)
      return apiClient.post('/api/v1/query', { query }, { timeout: 120000 }).then((res) => res.data);
    },
    history: (params?: any) => api.get('/api/v1/query/history', params),
  },
};

export default api;

// Convenience exports for common operations
export const getAPIs = async (params?: any) => {
  const response = await api.apis.list(params);
  // Handle paginated response - return items array
  return response.items || response;
};
export const getGateways = () => api.gateways.list();
export const getPredictions = (params?: any) => api.predictions.list(params);
export const getRecommendations = (params?: any) => api.recommendations.list(params);

// Made with Bob
