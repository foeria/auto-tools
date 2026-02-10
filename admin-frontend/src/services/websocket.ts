import { ref, computed } from 'vue'

export interface WebSocketMessage {
  type: string
  payload: Record<string, unknown>
  task_id: string | null
  timestamp: string
}

export interface TaskStatusPayload {
  task_id: string
  status: string
  progress: number
  current_action: string | null
  message: string | null
}

export interface TaskProgressPayload {
  task_id: string
  action_index: number
  total_actions: number
  progress: number
  action_name: string
  details: Record<string, unknown>
}

export interface TaskLogPayload {
  task_id: string
  level: string
  message: string
  action_name: string | null
  details: Record<string, unknown>
}

export interface TaskResultPayload {
  task_id: string
  result: Record<string, unknown>
}

export interface TaskErrorPayload {
  task_id: string
  error: string
  details: Record<string, unknown>
}

class WebSocketService {
  private ws: WebSocket | null = null
  private url: string = ''
  private reconnectInterval: number = 3000
  private maxReconnectAttempts: number = 5
  private reconnectAttempts: number = 0
  private messageHandlers: Map<string, Set<(data: unknown) => void>> = new Map()
  private isConnecting: boolean = false

  public connected = ref(false)
  public connectionError = ref<string | null>(null)
  public lastMessage = ref<WebSocketMessage | null>(null)

  connect(url: string = (import.meta.env.VITE_WS_URL || 'ws://localhost:8000') + '/ws/tasks'): void {
    if (this.ws?.readyState === WebSocket.OPEN || this.isConnecting) {
      return
    }

    this.url = url
    this.isConnecting = true
    this.connectionError.value = null

    try {
      this.ws = new WebSocket(url)

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected to', url)
        this.connected.value = true
        this.isConnecting = false
        this.reconnectAttempts = 0
        this.connectionError.value = null
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          this.lastMessage.value = message
          this.dispatchMessage(message)
        } catch (e) {
          console.error('[WebSocket] Failed to parse message:', e)
        }
      }

      this.ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason)
        this.connected.value = false
        this.isConnecting = false

        if (!event.wasClean) {
          this.scheduleReconnect()
        }
      }

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error)
        this.connectionError.value = 'WebSocket connection error'
        this.isConnecting = false
      }
    } catch (error) {
      console.error('[WebSocket] Failed to create connection:', error)
      this.connectionError.value = 'Failed to create WebSocket connection'
      this.isConnecting = false
      this.scheduleReconnect()
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnect attempts reached')
      this.connectionError.value = 'Failed to reconnect after multiple attempts'
      return
    }

    this.reconnectAttempts++
    const delay = this.reconnectInterval * this.reconnectAttempts
    console.log(`[WebSocket] Scheduling reconnect attempt ${this.reconnectAttempts} in ${delay}ms`)

    setTimeout(() => {
      this.connect(this.url)
    }, delay)
  }

  disconnect(): void {
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
      this.connected.value = false
      this.isConnecting = false
    }
  }

  subscribe(taskId: string): void {
    this.send({
      type: 'subscribe',
      task_id: taskId
    })
  }

  unsubscribe(taskId: string): void {
    this.send({
      type: 'unsubscribe',
      task_id: taskId
    })
  }

  send(data: Record<string, unknown>): void {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(data))
    } else {
      console.warn('[WebSocket] Cannot send message: connection not open')
    }
  }

  on<T>(type: string, handler: (data: T) => void): () => void {
    if (!this.messageHandlers.has(type)) {
      this.messageHandlers.set(type, new Set())
    }
    this.messageHandlers.get(type)!.add(handler as (data: unknown) => void)

    return () => {
      this.messageHandlers.get(type)?.delete(handler as (data: unknown) => void)
    }
  }

  onTaskStatus(handler: (data: TaskStatusPayload) => void): () => void {
    return this.on<TaskStatusPayload>('task_status', handler)
  }

  onTaskProgress(handler: (data: TaskProgressPayload) => void): () => void {
    return this.on<TaskProgressPayload>('task_progress', handler)
  }

  onTaskLog(handler: (data: TaskLogPayload) => void): () => void {
    return this.on<TaskLogPayload>('task_log', handler)
  }

  onTaskResult(handler: (data: TaskResultPayload) => void): () => void {
    return this.on<TaskResultPayload>('task_result', handler)
  }

  onTaskError(handler: (data: TaskErrorPayload) => void): () => void {
    return this.on<TaskErrorPayload>('task_error', handler)
  }

  private dispatchMessage(message: WebSocketMessage): void {
    const handlers = this.messageHandlers.get(message.type)
    if (handlers) {
      handlers.forEach(handler => {
        try {
          handler(message.payload)
        } catch (e) {
          console.error(`[WebSocket] Error in handler for ${message.type}:`, e)
        }
      })
    }
  }

  getState(): number {
    return this.ws?.readyState ?? WebSocket.CLOSED
  }

  isOpen(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}

export const wsService = new WebSocketService()

export function useWebSocket() {
  const connected = computed(() => wsService.connected.value)
  const connectionError = computed(() => wsService.connectionError.value)
  const lastMessage = computed(() => wsService.lastMessage.value)

  function connect(url?: string): void {
    wsService.connect(url)
  }

  function disconnect(): void {
    wsService.disconnect()
  }

  function subscribe(taskId: string): void {
    wsService.subscribe(taskId)
  }

  function unsubscribe(taskId: string): void {
    wsService.unsubscribe(taskId)
  }

  return {
    connected,
    connectionError,
    lastMessage,
    connect,
    disconnect,
    subscribe,
    unsubscribe,
    on: wsService.on.bind(wsService),
    onTaskStatus: wsService.onTaskStatus.bind(wsService),
    onTaskProgress: wsService.onTaskProgress.bind(wsService),
    onTaskLog: wsService.onTaskLog.bind(wsService),
    onTaskResult: wsService.onTaskResult.bind(wsService),
    onTaskError: wsService.onTaskError.bind(wsService)
  }
}
