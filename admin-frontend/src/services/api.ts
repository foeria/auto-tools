/**
 * API服务封装
 * 提供前端调用的API方法
 */
import axios, { AxiosInstance } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.response.use(
  response => response,
  error => {
    console.error('API Error:', error.response?.data || error.message)
    return Promise.reject(error)
  }
)

export interface TaskCreate {
  url: string
  actions: Action[]
  extractors?: Extractor[]
  priority?: number
  max_retries?: number
  metadata?: Record<string, any>
}

export interface Action {
  type: 'goto' | 'click' | 'input' | 'wait' | 'screenshot' | 'extract' | 'evaluate' | 'scroll' | 'press' | 'hover' | 'upload'
  id?: string
  selector?: string
  value?: string
  url?: string
  timeout?: number
  by_image?: boolean
  template_path?: string
  clear?: boolean
  press_enter?: boolean
  state?: 'visible' | 'hidden' | 'attached' | 'detached'
  script?: string
  arg?: any
  x?: number
  y?: number
  key?: string
  file_paths?: string[]
  selectors?: string[]
  extract_type?: 'text' | 'html' | 'attribute'
  attribute?: string
}

export interface Extractor {
  type: 'html' | 'json' | 'table' | 'xpath' | 'api' | 'screenshot' | 'fullpage'
  selectors?: string[]
  xpaths?: Record<string, string>
  extract_type?: 'text' | 'html' | 'attribute'
  attribute?: string
  script_tag?: string
  selector?: string
  save_path?: string
  url_pattern?: string
  has_header?: boolean
  result_type?: string
}

export interface TaskInfo {
  id: string
  url: string
  actions: Action[]
  extractors: Extractor[]
  priority: number
  status: string
  result?: any
  error?: string
  created_at: string
  started_at?: string
  completed_at?: string
  metadata: Record<string, any>
}

export interface Template {
  id: string
  name: string
  description: string
  url_pattern: string
  actions: Action[]
  extractors: Extractor[]
  created_at: string
}

export interface Statistics {
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
  running_tasks: number
  queue_size: number
  total_data_records: number
}

export const taskApi = {
  async create(taskData: TaskCreate): Promise<{ task_id: string; status: string; message: string }> {
    const response = await api.post('/api/tasks', taskData)
    return response.data
  },

  async list(status?: string, limit = 100, offset = 0): Promise<{ total: number; tasks: TaskInfo[] }> {
    const params = new URLSearchParams()
    if (status) params.append('status', status)
    params.append('limit', limit.toString())
    params.append('offset', offset.toString())
    
    const response = await api.get(`/api/tasks?${params.toString()}`)
    return response.data
  },

  async get(taskId: string): Promise<TaskInfo> {
    const response = await api.get(`/api/tasks/${taskId}`)
    return response.data
  },

  async delete(taskId: string): Promise<void> {
    await api.delete(`/api/tasks/${taskId}`)
  },

  async retry(taskId: string): Promise<{ task_id: string; status: string; message: string }> {
    const response = await api.post(`/api/tasks/${taskId}/retry`)
    return response.data
  },

  async cancel(taskId: string): Promise<void> {
    await api.delete(`/api/tasks/${taskId}`)
  }
}

export const templateApi = {
  async list(): Promise<Template[]> {
    const response = await api.get('/api/templates')
    return response.data
  },

  async create(templateData: Omit<Template, 'id' | 'created_at'>): Promise<Template> {
    const response = await api.post('/api/templates', templateData)
    return response.data
  },

  async delete(templateId: string): Promise<void> {
    await api.delete(`/api/templates/${templateId}`)
  },

  async update(templateId: string, templateData: Partial<Template>): Promise<Template> {
    const response = await api.put(`/api/templates/${templateId}`, templateData)
    return response.data
  }
}

export const dataApi = {
  async forward(data: any, targetUrl: string, headers?: Record<string, string>): Promise<{ success: boolean; status_code?: number; response?: any }> {
    const response = await api.post('/api/forward', { data, target_url: targetUrl, headers })
    return response.data
  },

  async getStatistics(): Promise<Statistics> {
    const response = await api.get('/api/statistics')
    return response.data
  },

  async getAvailableActions(): Promise<{ actions: string[]; extractors: string[] }> {
    const response = await api.get('/api/actions')
    return response.data
  }
}

export const systemApi = {
  async healthCheck(): Promise<{ status: string; timestamp: string; version: string }> {
    const response = await api.get('/health')
    return response.data
  }
}

export default api
