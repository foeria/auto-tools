/**
 * API 服务测试
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import axios from 'axios'

// Mock axios
vi.mock('axios')

describe('API Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('taskApi', () => {
    it('should create a task successfully', async () => {
      const { taskApi } = await import('@/services/api')

      const mockResponse = {
        data: {
          task_id: 'test-task-123',
          status: 'pending',
          message: '任务已创建'
        }
      }
      ;(axios.post as vi.Mock).mockResolvedValue(mockResponse)

      const result = await taskApi.create({
        url: 'https://example.com',
        actions: [{ type: 'goto', url: 'https://example.com' }]
      })

      expect(axios.post).toHaveBeenCalledWith(
        '/api/tasks',
        expect.objectContaining({
          url: 'https://example.com',
          actions: [{ type: 'goto', url: 'https://example.com' }]
        })
      )
      expect(result.task_id).toBe('test-task-123')
    })

    it('should list tasks', async () => {
      const { taskApi } = await import('@/services/api')

      const mockResponse = {
        data: {
          total: 10,
          tasks: [
            { id: 'task-1', url: 'https://example.com', status: 'pending' }
          ]
        }
      }
      ;(axios.get as vi.Mock).mockResolvedValue(mockResponse)

      const result = await taskApi.list('pending', 10, 0)

      expect(axios.get).toHaveBeenCalled()
      expect(result.total).toBe(10)
    })

    it('should delete a task', async () => {
      const { taskApi } = await import('@/services/api')
      ;(axios.delete as vi.Mock).mockResolvedValue({})

      await taskApi.delete('test-task-id')

      expect(axios.delete).toHaveBeenCalledWith('/api/tasks/test-task-id')
    })

    it('should retry a task', async () => {
      const { taskApi } = await import('@/services/api')

      const mockResponse = {
        data: {
          task_id: 'new-task-456',
          status: 'retry',
          message: '任务已重新入队'
        }
      }
      ;(axios.post as vi.Mock).mockResolvedValue(mockResponse)

      const result = await taskApi.retry('old-task-id')

      expect(axios.post).toHaveBeenCalledWith('/api/tasks/old-task-id/retry')
      expect(result.task_id).toBe('new-task-456')
    })
  })

  describe('taskApi batch operations', () => {
    it('should create batch tasks', async () => {
      const { taskApi } = await import('@/services/api')

      const mockResponse = {
        data: {
          created: [
            { task_id: 'task-1', url: 'https://example1.com', status: 'pending' },
            { task_id: 'task-2', url: 'https://example2.com', status: 'pending' }
          ],
          errors: [],
          total_created: 2,
          total_errors: 0
        }
      }
      ;(axios.post as vi.Mock).mockResolvedValue(mockResponse)

      const result = await taskApi.createBatch([
        { url: 'https://example1.com', actions: [] },
        { url: 'https://example2.com', actions: [] }
      ])

      expect(axios.post).toHaveBeenCalledWith(
        '/api/tasks/batch',
        expect.objectContaining({
          tasks: expect.any(Array),
          max_retries: undefined
        })
      )
      expect(result.total_created).toBe(2)
    })

    it('should delete batch tasks', async () => {
      const { taskApi } = await import('@/services/api')

      const mockResponse = {
        data: {
          deleted: ['task-1', 'task-2'],
          errors: [],
          total_deleted: 2,
          total_errors: 0
        }
      }
      ;(axios.request as vi.Mock).mockResolvedValue(mockResponse)

      const result = await taskApi.deleteBatch(['task-1', 'task-2'])

      expect(axios.request).toHaveBeenCalledWith(
        expect.objectContaining({
          method: 'delete',
          url: '/api/tasks/batch',
          data: { task_ids: ['task-1', 'task-2'] }
        })
      )
      expect(result.total_deleted).toBe(2)
    })

    it('should cancel batch tasks', async () => {
      const { taskApi } = await import('@/services/api')

      const mockResponse = {
        data: {
          cancelled: ['task-1'],
          errors: [],
          total_cancelled: 1,
          total_errors: 0
        }
      }
      ;(axios.post as vi.Mock).mockResolvedValue(mockResponse)

      const result = await taskApi.cancelBatch(['task-1'])

      expect(axios.post).toHaveBeenCalledWith(
        '/api/tasks/batch/cancel',
        { task_ids: ['task-1'] }
      )
      expect(result.total_cancelled).toBe(1)
    })
  })

  describe('templateApi', () => {
    it('should list templates', async () => {
      const { templateApi } = await import('@/services/api')

      const mockResponse = {
        data: [
          { id: 'template-1', name: 'Test Template' }
        ]
      }
      ;(axios.get as vi.Mock).mockResolvedValue(mockResponse)

      const result = await templateApi.list()

      expect(axios.get).toHaveBeenCalledWith('/api/templates')
      expect(result[0].name).toBe('Test Template')
    })

    it('should create a template', async () => {
      const { templateApi } = await import('@/services/api')

      const mockResponse = {
        data: {
          id: 'new-template-id',
          name: 'New Template',
          actions: []
        }
      }
      ;(axios.post as vi.Mock).mockResolvedValue(mockResponse)

      const result = await templateApi.create({
        name: 'New Template',
        description: 'Description',
        url_pattern: 'https://example.com/*',
        actions: [],
        extractors: []
      })

      expect(axios.post).toHaveBeenCalledWith(
        '/api/templates',
        expect.objectContaining({
          name: 'New Template'
        })
      )
    })
  })

  describe('dataApi', () => {
    it('should get statistics', async () => {
      const { dataApi } = await import('@/services/api')

      const mockResponse = {
        data: {
          total_tasks: 100,
          completed_tasks: 80,
          failed_tasks: 15,
          running_tasks: 5
        }
      }
      ;(axios.get as vi.Mock).mockResolvedValue(mockResponse)

      const result = await dataApi.getStatistics()

      expect(axios.get).toHaveBeenCalledWith('/api/statistics')
      expect(result.total_tasks).toBe(100)
    })

    it('should get task history', async () => {
      const { dataApi } = await import('@/services/api')

      const mockResponse = {
        data: {
          data: [
            { id: 'history-1', url: 'https://example.com', status: 'completed' }
          ],
          total: 1
        }
      }
      ;(axios.get as vi.Mock).mockResolvedValue(mockResponse)

      const result = await dataApi.getTaskHistory({
        start_date: '2024-01-01',
        end_date: '2024-12-31',
        status: 'completed'
      })

      expect(axios.get).toHaveBeenCalled()
      expect(result.data[0].id).toBe('history-1')
    })

    it('should get history statistics', async () => {
      const { dataApi } = await import('@/services/api')

      const mockResponse = {
        data: {
          total_tasks: 500,
          completed_tasks: 400,
          failed_tasks: 80,
          success_rate: 0.8
        }
      }
      ;(axios.get as vi.Mock).mockResolvedValue(mockResponse)

      const result = await dataApi.getHistoryStatistics({})

      expect(axios.get).toHaveBeenCalled()
      expect(result.success_rate).toBe(0.8)
    })
  })

  describe('systemApi', () => {
    it('should perform health check', async () => {
      const { systemApi } = await import('@/services/api')

      const mockResponse = {
        data: {
          status: 'healthy',
          version: '1.0.0',
          timestamp: '2024-01-01T00:00:00Z'
        }
      }
      ;(axios.get as vi.Mock).mockResolvedValue(mockResponse)

      const result = await systemApi.healthCheck()

      expect(axios.get).toHaveBeenCalledWith('/health')
      expect(result.status).toBe('healthy')
    })
  })
})
