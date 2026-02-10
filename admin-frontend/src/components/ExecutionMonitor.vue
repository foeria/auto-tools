<template>
  <div class="execution-monitor">
    <div class="monitor-header">
      <div class="header-left">
        <el-icon class="header-icon"><Monitor /></el-icon>
        <span class="header-title">执行监控</span>
      </div>
      <div class="header-right">
        <el-tag :type="connectionStatusType" size="small">
          {{ connectionStatusText }}
        </el-tag>
        <el-button size="small" :icon="Refresh" @click="refreshStatus" :loading="refreshing">
          刷新
        </el-button>
      </div>
    </div>

    <div class="task-info" v-if="currentTask">
      <div class="task-id">
        <span class="label">任务ID:</span>
        <el-tooltip :content="currentTask.taskId" placement="top">
          <span class="value">{{ truncateTaskId(currentTask.taskId) }}</span>
        </el-tooltip>
        <el-button size="small" text :icon="CopyDocument" @click="copyTaskId"></el-button>
      </div>
      <div class="task-status">
        <el-tag :type="statusType" size="large" class="status-tag">
          <el-icon v-if="statusIcon" class="status-icon"><component :is="statusIcon" /></el-icon>
          {{ statusText }}
        </el-tag>
      </div>
    </div>

    <div class="stats-section" v-if="currentTask">
      <div class="stat-card">
        <el-icon class="stat-icon time"><Clock /></el-icon>
        <div class="stat-content">
          <span class="stat-value">{{ formatElapsedTime }}</span>
          <span class="stat-label">运行时间</span>
        </div>
      </div>
      <div class="stat-card">
        <el-icon class="stat-icon actions"><Operation /></el-icon>
        <div class="stat-content">
          <span class="stat-value">{{ currentTask.currentActionIndex || 0 }} / {{ currentTask.totalActions || 0 }}</span>
          <span class="stat-label">执行进度</span>
        </div>
      </div>
      <div class="stat-card">
        <el-icon class="stat-icon" :class="successRate >= 80 ? 'success' : 'warning'"><DataAnalysis /></el-icon>
        <div class="stat-content">
          <span class="stat-value">{{ successRate }}%</span>
          <span class="stat-label">成功率</span>
        </div>
      </div>
      <div class="stat-card">
        <el-icon class="stat-icon info"><InfoFilled /></el-icon>
        <div class="stat-content">
          <span class="stat-value">{{ logs.length }}</span>
          <span class="stat-label">日志数</span>
        </div>
      </div>
    </div>

    <div class="progress-section" v-if="currentTask && currentTask.status !== 'completed' && currentTask.status !== 'failed'">
      <div class="progress-info">
        <span class="progress-label">{{ currentTask.currentAction || '准备中...' }}</span>
        <span class="progress-percentage">{{ currentTask.progress }}%</span>
      </div>
      <el-progress 
        :percentage="currentTask.progress" 
        :status="progressStatus"
        :stroke-width="8"
        :show-text="false"
      />
      <div class="progress-details">
        <span class="action-count">
          <el-icon><Operation /></el-icon>
          {{ currentTask.currentActionIndex || 0 }} / {{ currentTask.totalActions || 0 }}
        </span>
        <span class="elapsed-time" v-if="startTime">
          <el-icon><Clock /></el-icon>
          {{ formatElapsedTime }}
        </span>
      </div>
    </div>

    <div class="actions-progress" v-if="currentTask && currentTask.totalActions > 0">
      <div class="actions-header">
        <el-icon><List /></el-icon>
        <span>执行进度</span>
      </div>
      <div class="actions-list">
        <div 
          v-for="(action, index) in displayedActions" 
          :key="index"
          class="action-item"
          :class="{ 
            'active': index + 1 === currentTask.currentActionIndex,
            'completed': index + 1 < currentTask.currentActionIndex,
            'pending': index + 1 > currentTask.currentActionIndex
          }"
        >
          <div class="action-status">
            <el-icon v-if="index + 1 < currentTask.currentActionIndex" class="completed-icon"><CircleCheck /></el-icon>
            <el-icon v-else-if="index + 1 === currentTask.currentActionIndex" class="active-icon"><Loading /></el-icon>
            <el-icon v-else class="pending-icon"><Remove /></el-icon>
          </div>
          <div class="action-info">
            <span class="action-name">{{ action.name }}</span>
            <span class="action-detail">{{ action.detail }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="logs-section" v-if="showLogs">
      <div class="logs-header">
        <div class="header-left">
          <el-icon><Document /></el-icon>
          <span>执行日志</span>
          <el-badge :value="filteredLogs.length" :hidden="filteredLogs.length === 0" class="log-badge" />
        </div>
        <div class="header-right">
          <el-switch
            v-model="autoScroll"
            size="small"
            title="自动滚动"
          />
          <el-select 
            v-model="logFilter" 
            size="small" 
            placeholder="日志级别"
            clearable
            class="log-filter"
          >
            <el-option label="全部" value="" />
            <el-option label="INFO" value="info" />
            <el-option label="SUCCESS" value="success" />
            <el-option label="WARNING" value="warning" />
            <el-option label="ERROR" value="error" />
          </el-select>
          <el-input
            v-model="logSearch"
            size="small"
            placeholder="搜索日志..."
            :prefix-icon="Search"
            clearable
            class="log-search"
          />
          <el-button size="small" text :icon="Download" @click="exportLogs" :disabled="filteredLogs.length === 0">
            导出
          </el-button>
          <el-button size="small" text :icon="Delete" @click="clearLogs" :disabled="logs.length === 0">
            清空
          </el-button>
        </div>
      </div>
      <div class="logs-container" ref="logsContainerRef">
        <div 
          v-for="(log, index) in filteredLogs" 
          :key="index"
          class="log-item"
          :class="[`log-${log.level}`]"
        >
          <span class="log-time">{{ formatLogTime(log.timestamp) }}</span>
          <el-tag :type="getLogLevelType(log.level)" size="small" class="log-level">
            {{ log.level.toUpperCase() }}
          </el-tag>
          <span class="log-message">{{ log.message }}</span>
          <el-tag v-if="log.action" size="small" type="info" class="log-action">
            {{ log.action }}
          </el-tag>
        </div>
        <div v-if="filteredLogs.length === 0 && logs.length > 0" class="logs-empty">
          <el-icon><Search /></el-icon>
          <span>没有匹配的日志</span>
        </div>
        <div v-if="logs.length === 0" class="logs-empty">
          <el-icon><InfoFilled /></el-icon>
          <span>暂无日志</span>
        </div>
      </div>
      <div class="logs-footer">
        <span class="log-count">
          显示 {{ filteredLogs.length }} / {{ logs.length }} 条日志
        </span>
      </div>
    </div>

    <div class="monitor-footer">
      <el-button 
        v-if="currentTask && canCancel" 
        type="danger" 
        :icon="Close"
        @click="handleCancel"
      >
        取消任务
      </el-button>
      <el-button 
        v-if="currentTask && currentTask.status === 'failed'" 
        type="warning" 
        :icon="Refresh"
        @click="handleRetry"
      >
        重新运行
      </el-button>
      <el-button 
        v-if="currentTask && (currentTask.status === 'completed' || currentTask.status === 'failed')" 
        :icon="View"
        @click="viewResults"
      >
        查看结果
      </el-button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { 
  Monitor, Refresh, CopyDocument, Operation, Clock, List, 
  CircleCheck, Loading, Document, Download, Delete,
  InfoFilled, Close, View, WarningFilled, SuccessFilled, CircleClose, Remove,
  Search, DataAnalysis
} from '@element-plus/icons-vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useWebSocket, type TaskStatusPayload, type TaskProgressPayload, type TaskLogPayload } from '@/services/websocket'
import { taskApi } from '@/services/api'

interface ActionInfo {
  name: string
  detail: string
}

interface LogEntry {
  timestamp: string
  level: string
  message: string
  action?: string
}

interface TaskInfo {
  taskId: string
  url: string
  status: string
  progress: number
  currentAction: string | null
  currentActionIndex: number
  totalActions: number
  startTime: string | null
}

const props = defineProps<{
  taskId?: string
  autoConnect?: boolean
  showLogs?: boolean
  maxLogs?: number
}>()

const emit = defineEmits<{
  (e: 'complete', data: unknown): void
  (e: 'error', error: string): void
  (e: 'cancel'): void
}>()

const { connected, connect, disconnect, onTaskStatus, onTaskProgress, onTaskLog, onTaskResult, onTaskError, subscribe } = useWebSocket()

const currentTask = ref<TaskInfo | null>(null)
const logs = ref<LogEntry[]>([])
const startTime = ref<Date | null>(null)
const refreshing = ref(false)
const logsContainerRef = ref<HTMLElement | null>(null)

const connectionStatusType = computed(() => connected.value ? 'success' : 'danger')
const connectionStatusText = computed(() => connected.value ? '已连接' : '未连接')

const statusType = computed(() => {
  const status = currentTask.value?.status
  if (status === 'running') return 'primary'
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'cancelled') return 'info'
  return 'warning'
})

const statusText = computed(() => {
  const status = currentTask.value?.status
  const texts: Record<string, string> = {
    pending: '等待中',
    queued: '排队中',
    running: '执行中',
    starting: '启动中',
    completed: '已完成',
    failed: '失败',
    cancelled: '已取消'
  }
  return texts[status || ''] || status || '未知'
})

const statusIcon = computed(() => {
  const status = currentTask.value?.status
  if (status === 'running' || status === 'starting') return Loading
  if (status === 'completed') return SuccessFilled
  if (status === 'failed') return CircleClose
  return WarningFilled
})

const progressStatus = computed(() => {
  const status = currentTask.value?.status
  if (status === 'completed') return 'success'
  if (status === 'failed') return 'exception'
  return ''
})

const canCancel = computed(() => {
  const status = currentTask.value?.status
  return status === 'running' || status === 'starting' || status === 'pending' || status === 'queued'
})

const displayedActions = computed<ActionInfo[]>(() => {
  if (!currentTask.value || !currentTask.value.totalActions) {
    return []
  }
  return getActionNames(currentTask.value.totalActions)
})

const formatElapsedTime = computed(() => {
  if (!startTime.value) return '00:00'
  const elapsed = Math.floor((Date.now() - startTime.value.getTime()) / 1000)
  const minutes = Math.floor(elapsed / 60)
  const seconds = elapsed % 60
  return `${minutes.toString().padStart(2, '0')}:${seconds.toString().padStart(2, '0')}`
})

const successRate = computed(() => {
  if (!logs.value.length) return 100
  const successLogs = logs.value.filter(log => log.level === 'success').length
  const errorLogs = logs.value.filter(log => log.level === 'error').length
  if (successLogs === 0 && errorLogs === 0) return 100
  return Math.round((successLogs / (successLogs + errorLogs)) * 100)
})

const autoScroll = ref(true)
const logFilter = ref('')
const logSearch = ref('')

const filteredLogs = computed(() => {
  let result = logs.value
  
  if (logFilter.value) {
    result = result.filter(log => log.level === logFilter.value)
  }
  
  if (logSearch.value.trim()) {
    const search = logSearch.value.toLowerCase()
    result = result.filter(log => 
      log.message.toLowerCase().includes(search) ||
      log.action?.toLowerCase().includes(search)
    )
  }
  
  return result
})

watch(filteredLogs, () => {
  if (autoScroll.value) {
    nextTick(() => {
      if (logsContainerRef.value) {
        logsContainerRef.value.scrollTop = logsContainerRef.value.scrollHeight
      }
    })
  }
})

let unsubscribeStatus: (() => void) | null = null
let unsubscribeProgress: (() => void) | null = null
let unsubscribeLog: (() => void) | null = null
let unsubscribeResult: (() => void) | null = null
let unsubscribeError: (() => void) | null = null

function getActionNames(count: number): ActionInfo[] {
  const names: Record<string, string> = {
    goto: '访问页面',
    click: '点击元素',
    input: '输入内容',
    wait: '等待',
    scroll: '页面滚动',
    screenshot: '截图',
    extract: '提取数据',
    press: '键盘操作',
    hover: '悬停',
    upload: '上传文件',
    evaluate: '执行脚本',
    switch_frame: '切换框架',
    switch_tab: '切换标签页',
    new_tab: '打开新标签页',
    close_tab: '关闭标签页',
    drag: '拖拽元素'
  }
  return Array.from({ length: count }, (_, i) => ({
    name: names[`action_${i + 1}`] || `操作 ${i + 1}`,
    detail: ''
  }))
}

function truncateTaskId(taskId: string): string {
  if (taskId.length <= 12) return taskId
  return `${taskId.substring(0, 6)}...${taskId.substring(taskId.length - 6)}`
}

async function copyTaskId() {
  if (currentTask.value?.taskId) {
    await navigator.clipboard.writeText(currentTask.value.taskId)
    ElMessage.success('任务ID已复制到剪贴板')
  }
}

function formatLogTime(timestamp: string): string {
  try {
    const date = new Date(timestamp)
    return date.toLocaleTimeString('zh-CN', { hour12: false })
  } catch {
    return '--:--:--'
  }
}

function getLogLevelType(level: string): 'success' | 'warning' | 'danger' | 'info' {
  const types: Record<string, 'success' | 'warning' | 'danger' | 'info'> = {
    info: 'info',
    success: 'success',
    warning: 'warning',
    error: 'danger'
  }
  return types[level.toLowerCase()] || 'info'
}

async function exportLogs() {
  const logText = filteredLogs.value.map(log => {
    const time = formatLogTime(log.timestamp)
    const action = log.action ? ` [${log.action}]` : ''
    return `[${time}] [${log.level.toUpperCase()}]${action} ${log.message}`
  }).join('\n')

  const header = `任务ID: ${currentTask.value?.taskId || '未知'}\n`
             + `状态: ${statusText.value}\n`
             + `开始时间: ${startTime.value?.toLocaleString('zh-CN') || '未知'}\n`
             + `日志数量: ${filteredLogs.value.length}\n`
             + `--------------------------------------------------\n\n`
  
  const blob = new Blob([header + logText], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `task-logs-${currentTask.value?.taskId || 'export'}-${Date.now()}.txt`
  a.click()
  URL.revokeObjectURL(url)

  ElMessage.success(`已导出 ${filteredLogs.value.length} 条日志`)
}

function clearLogs() {
  logs.value = []
}

async function refreshStatus() {
  if (!currentTask.value?.taskId) return
  
  refreshing.value = true
  try {
    const status = await taskApi.get(currentTask.value.taskId)
    currentTask.value.status = status.status
    currentTask.value.progress = status.status === 'completed' ? 100 : currentTask.value.progress
  } catch (error) {
    ElMessage.error('获取状态失败')
  } finally {
    refreshing.value = false
  }
}

async function handleCancel() {
  if (!currentTask.value?.taskId) return

  try {
    await ElMessageBox.confirm('确定要取消当前任务吗？', '确认取消', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    await taskApi.cancel(currentTask.value.taskId)
    emit('cancel')
    ElMessage.success('任务已取消')
  } catch {
    ElMessage.info('取消操作')
  }
}

async function handleRetry() {
  if (!currentTask.value?.taskId) return

  try {
    await ElMessageBox.confirm('确定要重新运行任务吗？', '确认重试', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })

    const response = await taskApi.retry(currentTask.value.taskId)
    currentTask.value.taskId = response.task_id
    currentTask.value.status = 'pending'
    currentTask.value.progress = 0
    currentTask.value.currentAction = null
    currentTask.value.currentActionIndex = 0
    logs.value = []
    startTime.value = new Date()
    
    connect()
    subscribe(response.task_id)
    
    ElMessage.success('任务已重新提交')
  } catch {
    ElMessage.info('取消重试')
  }
}

function viewResults() {
  emit('complete', currentTask.value)
}

function addLog(log: TaskLogPayload) {
  if (props.maxLogs && logs.value.length >= props.maxLogs) {
    logs.value.shift()
  }
  
  logs.value.push({
    timestamp: new Date().toISOString(),
    level: log.level,
    message: log.message,
    action: log.action_name || undefined
  })

  nextTick(() => {
    if (logsContainerRef.value) {
      logsContainerRef.value.scrollTop = logsContainerRef.value.scrollHeight
    }
  })
}

function handleStatus(status: TaskStatusPayload) {
  if (!currentTask.value) {
    currentTask.value = {
      taskId: status.task_id,
      url: '',
      status: status.status,
      progress: status.progress,
      currentAction: status.current_action,
      currentActionIndex: 0,
      totalActions: 0,
      startTime: new Date().toISOString()
    }
    startTime.value = new Date()
  } else {
    currentTask.value.status = status.status
    currentTask.value.progress = status.progress
    currentTask.value.currentAction = status.current_action
  }

  if (status.status === 'running' && !startTime.value) {
    startTime.value = new Date()
  }
}

function handleProgress(progress: TaskProgressPayload) {
  if (currentTask.value) {
    currentTask.value.totalActions = progress.total_actions
    currentTask.value.currentActionIndex = progress.action_index
    currentTask.value.progress = progress.progress
  }
}

function handleResult(result: unknown) {
  if (currentTask.value) {
    currentTask.value.status = 'completed'
    currentTask.value.progress = 100
    currentTask.value.currentAction = '任务完成'
  }
  emit('complete', result)
}

function handleError(error: unknown) {
  if (currentTask.value) {
    currentTask.value.status = 'failed'
  }
  emit('error', String(error))
}

function initializeWebSocket() {
  if (props.autoConnect) {
    connect()
  }

  if (props.taskId) {
    currentTask.value = {
      taskId: props.taskId,
      url: '',
      status: 'pending',
      progress: 0,
      currentAction: null,
      currentActionIndex: 0,
      totalActions: 0,
      startTime: null
    }
    subscribe(props.taskId)
  }

  unsubscribeStatus = onTaskStatus(handleStatus)
  unsubscribeProgress = onTaskProgress(handleProgress)
  unsubscribeLog = onTaskLog(addLog)
  unsubscribeResult = onTaskResult(handleResult)
  unsubscribeError = onTaskError(handleError)
}

onMounted(() => {
  initializeWebSocket()
})

onUnmounted(() => {
  unsubscribeStatus?.()
  unsubscribeProgress?.()
  unsubscribeLog?.()
  unsubscribeResult?.()
  unsubscribeError?.()
})

defineExpose({
  connect: () => {
    connect()
    if (currentTask.value?.taskId) {
      subscribe(currentTask.value.taskId)
    }
  },
  disconnect,
  clearLogs,
  getLogs: () => logs.value
})
</script>

<style lang="scss" scoped>
.execution-monitor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--el-bg-color);
  border-radius: 8px;
  border: 1px solid var(--el-border-color-light);
  overflow: hidden;
}

.monitor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-icon {
  color: var(--el-color-primary);
  font-size: 18px;
}

.header-title {
  font-weight: 600;
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.header-right {
  display: flex;
  align-items: center;
  gap: 8px;
}

.task-info {
  padding: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.task-id {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
  
  .label {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
  
  .value {
    font-family: 'Monaco', 'Consolas', monospace;
    font-size: 12px;
    color: var(--el-text-color-primary);
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.task-status {
  display: flex;
  align-items: center;
}

.status-tag {
  .status-icon {
    margin-right: 4px;
  }
}

.progress-section {
  padding: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.progress-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.progress-label {
  font-size: 13px;
  color: var(--el-text-color-primary);
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.progress-percentage {
  font-size: 14px;
  font-weight: 600;
  color: var(--el-text-color-primary);
  margin-left: 12px;
}

.progress-details {
  display: flex;
  justify-content: space-between;
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
  
  span {
    display: flex;
    align-items: center;
    gap: 4px;
  }
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
  padding: 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
}

.stat-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  background: var(--el-bg-color);
  border-radius: 8px;
  border: 1px solid var(--el-border-color-lighter);
  
  .stat-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 8px;
    font-size: 20px;
    
    &.time {
      background: var(--el-color-primary-light-9);
      color: var(--el-color-primary);
    }
    
    &.actions {
      background: var(--el-color-success-light-9);
      color: var(--el-color-success);
    }
    
    &.success {
      background: var(--el-color-success-light-9);
      color: var(--el-color-success);
    }
    
    &.warning {
      background: var(--el-color-warning-light-9);
      color: var(--el-color-warning);
    }
    
    &.info {
      background: var(--el-color-info-light-9);
      color: var(--el-color-info);
    }
  }
  
  .stat-content {
    flex: 1;
    min-width: 0;
    
    .stat-value {
      display: block;
      font-size: 18px;
      font-weight: 600;
      color: var(--el-text-color-primary);
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }
    
    .stat-label {
      display: block;
      font-size: 12px;
      color: var(--el-text-color-secondary);
      margin-top: 2px;
    }
  }
}

.actions-progress {
  flex: 1;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.actions-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  font-size: 13px;
  font-weight: 500;
}

.actions-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}

.action-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 8px;
  border-radius: 4px;
  transition: background-color 0.2s;
  
  &:hover {
    background: var(--el-fill-color-light);
  }
  
  &.active {
    background: var(--el-color-primary-light-9);
  }
  
  &.completed {
    .completed-icon {
      color: var(--el-color-success);
    }
  }
}

.action-status {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  
  .completed-icon {
    color: var(--el-color-success);
  }
  
  .active-icon {
    color: var(--el-color-primary);
    animation: rotate 1s linear infinite;
  }
  
  .pending-icon {
    color: var(--el-text-color-secondary);
  }
}

@keyframes rotate {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.action-info {
  flex: 1;
  min-width: 0;
}

.action-name {
  display: block;
  font-size: 13px;
  color: var(--el-text-color-primary);
}

.action-detail {
  display: block;
  font-size: 11px;
  color: var(--el-text-color-secondary);
  margin-top: 2px;
}

.logs-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-top: 1px solid var(--el-border-color-lighter);
}

.logs-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  flex-wrap: wrap;
  gap: 8px;
}

.header-left {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  font-weight: 500;
}

.log-badge {
  margin-left: 4px;
}

.log-filter {
  width: 100px;
}

.log-search {
  width: 150px;
}

.logs-container {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
  font-family: 'Monaco', 'Consolas', monospace;
  font-size: 12px;
}

.log-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 4px 0;
  line-height: 1.5;
  
  .log-time {
    color: var(--el-text-color-secondary);
    flex-shrink: 0;
    width: 70px;
  }
  
  .log-level {
    flex-shrink: 0;
    width: 50px;
    text-align: center;
  }
  
  .log-message {
    color: var(--el-text-color-primary);
    word-break: break-all;
  }
  
  .log-action {
    flex-shrink: 0;
    margin-left: auto;
  }
  
  &.log-info .log-message {
    color: var(--el-text-color-primary);
  }
  
  &.log-success .log-message {
    color: var(--el-color-success);
  }
  
  &.log-warning .log-message {
    color: var(--el-color-warning);
  }
  
  &.log-error .log-message {
    color: var(--el-color-danger);
  }
}

.logs-footer {
  display: flex;
  justify-content: flex-end;
  padding: 8px 16px;
  border-top: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
  
  .log-count {
    font-size: 12px;
    color: var(--el-text-color-secondary);
  }
}

.logs-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: var(--el-text-color-secondary);
  gap: 8px;
  
  .el-icon {
    font-size: 32px;
  }
}

.monitor-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 12px 16px;
  border-top: 1px solid var(--el-border-color-lighter);
  background: var(--el-fill-color-light);
}
</style>
