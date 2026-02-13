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

export interface TaskScreenshotPayload {
  task_id: string
  screenshot: string  // base64 encoded image
  action_index: number
  timestamp: string
}

// WebSocket配置（可从后端config.yaml同步）
interface WebSocketConfig {
  pingInterval: number      // 心跳间隔 (ms) - 对应 config.websocket.ping_interval
  pongTimeout: number       // Pong超时 (ms) - 对应 config.websocket.pong_timeout
  maxReconnectAttempts: number  // 最大重连次数 - 对应 config.websocket.max_reconnect_attempts
  reconnectDelayBase: number    // 重连延迟基数 (ms) - 对应 config.websocket.reconnect_delay_base
}

class WebSocketService {
  private ws: WebSocket | null = null
  private url: string = ''
  private config: WebSocketConfig = {
    pingInterval: 30000,          // 30秒
    pongTimeout: 10000,          // 10秒
    maxReconnectAttempts: 5,      // 最多5次
    reconnectDelayBase: 3000      // 3秒基数
  }
  private reconnectAttempts: number = 0
  private messageHandlers: Map<string, Set<(data: unknown) => void>> = new Map()
  private isConnecting: boolean = false
  private heartbeatInterval: number | null = null
  private pongTimeout: number | null = null
  private lastPongTime: number = 0

  public connected = ref(false)
  public connectionError = ref<string | null>(null)
  public lastMessage = ref<WebSocketMessage | null>(null)

  /**
   * 更新WebSocket配置
   * @param config - 部分配置对象，会与现有配置合并
   */
  updateConfig(config: Partial<WebSocketConfig>): void {
    this.config = { ...this.config, ...config }
  }

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
        this.startHeartbeat()
      }

      this.ws.onmessage = (event) => {
        try {
          const message: WebSocketMessage = JSON.parse(event.data)
          this.lastMessage.value = message

          // 处理心跳响应
          if (message.type === 'pong') {
            this.lastPongTime = Date.now()
            this.clearPongTimeout()
            return
          }

          this.dispatchMessage(message)
        } catch (e) {
          console.error('[WebSocket] Failed to parse message:', e)
        }
      }

      this.ws.onclose = (event) => {
        console.log('[WebSocket] Disconnected:', event.code, event.reason)
        this.connected.value = false
        this.isConnecting = false
        this.stopHeartbeat()

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

  // 启动心跳
  private startHeartbeat(): void {
    this.stopHeartbeat()
    this.lastPongTime = Date.now()

    // 发送ping
    this.send({ type: 'ping' })

    // 设置pong超时检测 (使用配置)
    this.pongTimeout = window.setTimeout(() => {
      if (Date.now() - this.lastPongTime > this.config.pongTimeout) {
        console.warn('[WebSocket] Pong timeout, reconnecting...')
        this.handleConnectionLost()
      }
    }, this.config.pongTimeout)

    // 定期发送心跳 (使用配置)
    this.heartbeatInterval = window.setInterval(() => {
      if (this.connected.value) {
        this.send({ type: 'ping' })
        this.pongTimeout = window.setTimeout(() => {
          if (Date.now() - this.lastPongTime > this.config.pongTimeout) {
            console.warn('[WebSocket] Pong timeout, reconnecting...')
            this.handleConnectionLost()
          }
        }, this.config.pongTimeout)
      }
    }, this.config.pingInterval)
  }

  // 停止心跳
  private stopHeartbeat(): void {
    if (this.heartbeatInterval !== null) {
      clearInterval(this.heartbeatInterval)
      this.heartbeatInterval = null
    }
    this.clearPongTimeout()
  }

  private clearPongTimeout(): void {
    if (this.pongTimeout !== null) {
      clearTimeout(this.pongTimeout)
      this.pongTimeout = null
    }
  }

  // 处理连接丢失
  private handleConnectionLost(): void {
    this.stopHeartbeat()
    if (this.ws) {
      this.ws.close(1001, 'Connection lost')
      this.ws = null
    }
    this.scheduleReconnect()
  }

  private scheduleReconnect(): void {
    if (this.reconnectAttempts >= this.config.maxReconnectAttempts) {
      console.error('[WebSocket] Max reconnect attempts reached')
      this.connectionError.value = 'Failed to reconnect after multiple attempts'
      return
    }

    this.reconnectAttempts++
    // 使用指数退避计算重连延迟
    const delay = Math.min(
      this.config.reconnectDelayBase * Math.pow(2, this.reconnectAttempts - 1),
      30000  // 最大30秒
    )
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

  onTaskScreenshot(handler: (data: TaskScreenshotPayload) => void): () => void {
    return this.on<TaskScreenshotPayload>('task_screenshot', handler)
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
    onTaskError: wsService.onTaskError.bind(wsService),
    onTaskScreenshot: wsService.onTaskScreenshot.bind(wsService)
  }
}
