import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export interface Job {
  id: number;
  title: string;
  company: string;
  location: string;
  description: string;
  requirements?: string;
  url: string;
  source: string;
  remote: boolean;
  source_meta?: Record<string, any>;
  post_date?: string;
  job_hash: string;
  relevance_score: number;
  keywords_matched?: string;
  applied: boolean;
  notes?: string;
  created_at: string;
  updated_at?: string;
}

export interface Settings {
  keywords: string[];
  locations: string[];
  sources: Record<string, boolean>;
  greenhouse_boards: { name: string; board_url: string }[];
  india_mode: boolean;
  linkedin_mode: string;
  linkedin_email: Record<string, any>;
  linkedin_crawl: Record<string, any>;
  crawl_hour: number;
  crawl_minute: number;
}

export interface CrawlResult {
  status: string;
  jobs_found: number;
  jobs_added: number;
  message: string;
}

export interface Stats {
  total_jobs: number;
  applied_jobs: number;
  pending_jobs: number;
  sources: Record<string, number>;
}

export interface CrawlRun {
  run_id: string;
  started_at: string;
  finished_at?: string;
  duration_ms?: number;
  sources_attempted: string[];
  sources_succeeded: string[];
  sources_failed: { source: string; error: string }[];
  fetched_count: number;
  inserted_new_count: number;
  errors_summary?: string;
}

export const fetchJobs = async (params?: {
  q?: string;
  location?: string;
  applied?: boolean;
  source?: string[] | string;
  remote?: boolean;
  limit?: number;
  offset?: number;
}): Promise<Job[]> => {
  const response = await api.get('/api/jobs', { params: { ...params, _t: Date.now() } });
  return response.data;
};

export const fetchJob = async (id: number): Promise<Job> => {
  const response = await api.get(`/api/jobs/${id}`);
  return response.data;
};

export const updateJob = async (id: number, data: { applied?: boolean; notes?: string }): Promise<Job> => {
  const response = await api.patch(`/api/jobs/${id}`, data);
  return response.data;
};

export const triggerRescan = async (): Promise<CrawlResult> => {
  const response = await api.post('/api/rescan');
  return response.data;
};

export const fetchSettings = async (): Promise<Settings> => {
  const response = await api.get('/api/settings');
  return response.data;
};

export const updateSettings = async (settings: Settings): Promise<Settings> => {
  const response = await api.put('/api/settings', settings);
  return response.data;
};

export const fetchStats = async (): Promise<Stats> => {
  const response = await api.get('/api/stats');
  return response.data;
};

export const fetchRuns = async (params?: { limit?: number; offset?: number }): Promise<CrawlRun[]> => {
  const response = await api.get('/api/runs', { params });
  return response.data;
};

export const fetchRun = async (runId: string): Promise<CrawlRun> => {
  const response = await api.get(`/api/runs/${runId}`);
  return response.data;
};
