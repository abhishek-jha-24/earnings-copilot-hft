import axios, { AxiosInstance } from 'axios';
import {
  KpiData,
  Signal,
  Subscription,
  SubscriptionCreate,
  SearchResponse,
  UploadResponse,
  DashboardStats,
  TickerSummary,
  ApiError
} from '../types';

class ApiService {
  private api: AxiosInstance;
  private apiKey: string = '';

  constructor() {
    this.api = axios.create({
      baseURL: 'http://localhost:8000',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add API key
    this.api.interceptors.request.use((config) => {
      if (this.apiKey) {
        config.headers['X-API-Key'] = this.apiKey;
      }
      return config;
    });

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error) => {
        const apiError: ApiError = {
          detail: error.response?.data?.detail || error.message,
          status_code: error.response?.status,
          error_code: error.response?.data?.error_code,
        };
        return Promise.reject(apiError);
      }
    );
  }

  setApiKey(apiKey: string) {
    this.apiKey = apiKey;
  }

  // Health check
  async healthCheck(): Promise<any> {
    const response = await this.api.get('/health');
    return response.data;
  }

  // KPI endpoints
  async getKpi(ticker: string, metric: string, period?: string): Promise<KpiData> {
    const params: any = { ticker, metric };
    if (period) params.period = period;
    
    const response = await this.api.get('/kpi', { params });
    return response.data;
  }

  // Signal endpoints
  async getSignal(ticker: string, period?: string): Promise<Signal> {
    const params: any = { ticker };
    if (period) params.period = period;
    
    const response = await this.api.get('/signal', { params });
    return response.data;
  }

  // Search endpoints
  async search(query: string, limit: number = 10): Promise<SearchResponse> {
    const response = await this.api.get('/search', {
      params: { q: query, limit }
    });
    return response.data;
  }

  // Subscription endpoints
  async createSubscription(subscription: SubscriptionCreate): Promise<Subscription> {
    const response = await this.api.post('/subscriptions', subscription);
    return response.data;
  }

  async getSubscriptions(): Promise<Subscription[]> {
    const response = await this.api.get('/subscriptions');
    return response.data;
  }

  async deleteSubscription(ticker: string): Promise<void> {
    await this.api.delete(`/subscriptions/${ticker}`);
  }

  async getSubscriptionStatus(ticker: string): Promise<any> {
    const response = await this.api.get(`/subscriptions/${ticker}/status`);
    return response.data;
  }

  // Admin endpoints
  async uploadDocument(
    file: File,
    ticker: string,
    docType: string,
    period?: string,
    effectiveDate?: string
  ): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('ticker', ticker);
    formData.append('doc_type', docType);
    if (period) formData.append('period', period);
    if (effectiveDate) formData.append('effective_date', effectiveDate);

    const response = await this.api.post('/admin/ingest', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async getAdminStats(): Promise<DashboardStats> {
    const response = await this.api.get('/admin/stats');
    return response.data;
  }

  // Ticker endpoints
  async getAvailableTickers(): Promise<string[]> {
    const response = await this.api.get('/tickers');
    return response.data.tickers;
  }

  async getTickerSummary(ticker: string): Promise<TickerSummary> {
    const response = await this.api.get(`/ticker/${ticker}/summary`);
    return response.data;
  }

  // Export endpoints
  async exportMemo(
    ticker: string,
    period: string,
    format: 'pdf' | 'markdown' = 'pdf',
    includeCitations: boolean = true,
    includeCompliance: boolean = true
  ): Promise<Blob> {
    const response = await this.api.get('/export/memo', {
      params: {
        ticker,
        period,
        format,
        include_citations: includeCitations,
        include_compliance: includeCompliance,
      },
      responseType: 'blob',
    });
    return response.data;
  }

  // SSE connection
  createEventSource(userId: string): EventSource {
    const apiKey = this.apiKey || localStorage.getItem('apiKey') || '';
    const url = `${this.api.defaults.baseURL}/events/stream?api_key=${encodeURIComponent(apiKey)}&user_id=${userId}`;
    return new EventSource(url);
  }
}

export const apiService = new ApiService();
