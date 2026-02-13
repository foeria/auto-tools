<template>
  <div class="task-history">
    <el-row :gutter="20" class="header">
      <el-col :span="12">
        <h2>任务执行历史</h2>
      </el-col>
      <el-col :span="12" class="actions">
        <el-button @click="refreshHistory">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button @click="exportHistory">
          <el-icon><Download /></el-icon>
          导出报表
        </el-button>
      </el-col>
    </el-row>

    <!-- 统计卡片 -->
    <el-row :gutter="20" class="stats-row">
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <el-statistic title="总任务数" :value="statistics.total_tasks" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card success">
          <el-statistic title="成功" :value="statistics.completed_tasks">
            <template #suffix>
              <span class="stat-ratio">/ {{ statistics.total_tasks }}</span>
            </template>
          </el-statistic>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card danger">
          <el-statistic title="失败" :value="statistics.failed_tasks" />
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="never" class="stat-card">
          <el-statistic title="平均执行时长" :value="formatDuration(statistics.avg_duration)" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 筛选栏 -->
    <el-card shadow="never" class="filter-card">
      <el-row :gutter="20">
        <el-col :span="20">
          <el-date-picker
            v-model="dateRange"
            type="datetimerange"
            range-separator="至"
            start-placeholder="开始时间"
            end-placeholder="结束时间"
            format="YYYY-MM-DD HH:mm"
            value-format="YYYY-MM-DDTHH:mm:ss"
            @change="handleDateChange"
          />
          <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 140px; margin-left: 16px;">
            <el-option label="全部" value="" />
            <el-option label="成功" value="completed" />
            <el-option label="失败" value="failed" />
            <el-option label="已取消" value="cancelled" />
          </el-select>
          <el-button type="primary" style="margin-left: 16px" @click="applyFilters">
            应用筛选
          </el-button>
        </el-col>
        <el-col :span="4" style="text-align: right;">
          <span class="result-count">共 {{ filteredHistory.length }} 条记录</span>
        </el-col>
      </el-row>
    </el-card>

    <!-- 历史记录表格 -->
    <el-card shadow="never">
      <el-table
        :data="paginatedHistory"
        style="width: 100%"
        row-key="id"
        @row-click="viewDetail"
        @sort-change="handleSortChange"
      >
        <el-table-column prop="id" label="任务ID" width="220">
          <template #default="{ row }">
            <el-tooltip :content="row.id" placement="top">
              <span class="task-id">{{ row.id.substring(0, 8) }}...</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="url" label="目标URL" min-width="200">
          <template #default="{ row }">
            <el-tooltip :content="row.url" placement="top">
              <span class="url-text">{{ row.url }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center" sortable="custom">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="actions_count" label="操作数" width="80" align="center" sortable="custom" />
        <el-table-column prop="duration" label="执行时长" width="120" align="center" sortable="custom">
          <template #default="{ row }">
            {{ formatDuration(row.duration) }}
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="执行时间" width="160" align="center" sortable="custom">
          <template #default="{ row }">
            {{ formatDateTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button-group>
              <el-tooltip content="查看详情" placement="top">
                <el-button size="small" type="primary" @click.stop="viewDetail(row)">
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="重新运行" placement="top">
                <el-button
                  size="small"
                  type="success"
                  :disabled="row.status === 'running'"
                  @click.stop="reRunTask(row)"
                >
                  <el-icon><VideoPlay /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
                <el-button
                  size="small"
                  type="danger"
                  @click.stop="deleteHistoryTask(row.id)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-tooltip>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <!-- 分页 -->
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="filteredHistory.length"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>

    <!-- 详情对话框 -->
    <el-dialog
      v-model="detailVisible"
      title="历史任务详情"
      width="900px"
      destroy-on-close
    >
      <template v-if="currentTask">
        <el-descriptions :column="2" border class="task-info">
          <el-descriptions-item label="任务ID">
            <el-tooltip :content="currentTask.id" placement="top">
              <span>{{ currentTask.id.substring(0, 16) }}...</span>
            </el-tooltip>
          </el-descriptions-item>
          <el-descriptions-item label="状态">
            <el-tag :type="getStatusType(currentTask.status)">
              {{ getStatusText(currentTask.status) }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="目标URL" :span="2">
            {{ currentTask.url }}
          </el-descriptions-item>
          <el-descriptions-item label="执行时间">
            {{ formatDateTime(currentTask.created_at) }}
          </el-descriptions-item>
          <el-descriptions-item label="完成时间">
            {{ currentTask.completed_at ? formatDateTime(currentTask.completed_at) : '-' }}
          </el-descriptions-item>
          <el-descriptions-item label="执行时长">
            {{ formatDuration(currentTask.duration || 0) }}
          </el-descriptions-item>
          <el-descriptions-item label="操作数">
            {{ currentTask.actions_count }}
          </el-descriptions-item>
        </el-descriptions>

        <!-- 执行摘要 -->
        <el-divider content-position="left">执行摘要</el-divider>
        <el-row :gutter="20">
          <el-col :span="8">
            <div class="summary-item">
              <el-icon color="#67C23A"><CircleCheck /></el-icon>
              <span>成功步骤: {{ currentTask.success_count || 0 }}</span>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="summary-item">
              <el-icon color="#F56C6C"><CircleClose /></el-icon>
              <span>失败步骤: {{ currentTask.failed_count || 0 }}</span>
            </div>
          </el-col>
          <el-col :span="8">
            <div class="summary-item">
              <el-icon color="#909399"><Timer /></el-icon>
              <span>平均步骤耗时: {{ formatDuration(currentTask.avg_step_duration || 0) }}</span>
            </div>
          </el-col>
        </el-row>

        <!-- 错误信息 -->
        <template v-if="currentTask.error">
          <el-divider content-position="left">错误信息</el-divider>
          <el-alert
            :title="currentTask.error"
            type="error"
            :closable="false"
            show-icon
          />
        </template>

        <!-- 执行步骤 -->
        <el-divider content-position="left">执行步骤</el-divider>
        <el-timeline>
          <el-timeline-item
            v-for="(action, index) in currentTask.actions"
            :key="index"
            :timestamp="`步骤 ${index + 1}`"
            placement="top"
            :type="action.status === 'success' ? 'success' : action.status === 'failed' ? 'danger' : 'primary'"
          >
            <el-card shadow="never" size="small">
              <div class="action-header">
                <el-tag size="small" type="info">{{ action.type }}</el-tag>
                <span class="action-duration" v-if="action.duration">
                  {{ formatDuration(action.duration) }}
                </span>
              </div>
              <div class="action-detail" v-if="action.selector">
                选择器: {{ action.selector }}
              </div>
              <div class="action-detail" v-if="action.value">
                值: {{ action.value }}
              </div>
              <div class="action-status" :class="action.status">
                {{ action.status === 'success' ? '成功' : action.status === 'failed' ? '失败' : '进行中' }}
              </div>
            </el-card>
          </el-timeline-item>
        </el-timeline>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, Download, View, VideoPlay, Delete, CircleCheck, CircleClose, Timer } from '@element-plus/icons-vue'
import { taskApi, dataApi, type TaskHistoryItem } from '@/services/api'

// 格式化函数
function formatDateTime(dateStr: string): string {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    })
  } catch {
    return dateStr
  }
}

function formatDuration(seconds: number): string {
  if (!seconds || seconds < 0) return '0s'
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) {
    const mins = Math.floor(seconds / 60)
    const secs = Math.round(seconds % 60)
    return mins > 0 ? `${mins}m ${secs}s` : `${secs}s`
  }
  const hours = Math.floor(seconds / 3600)
  const mins = Math.round((seconds % 3600) / 60)
  return `${hours}h ${mins}m`
}

interface Statistics {
  total_tasks: number
  completed_tasks: number
  failed_tasks: number
  avg_duration: number
}

// 响应式数据
const historyTasks = ref<TaskHistoryItem[]>([])
const dateRange = ref<[string, string] | null>(null)
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(20)
const detailVisible = ref(false)
const currentTask = ref<TaskHistoryItem | null>(null)
const sortProp = ref('')
const sortOrder = ref('')

// 统计数据
const statistics = computed<Statistics>(() => {
  const tasks = filteredHistory.value
  const completed = tasks.filter(t => t.status === 'completed')
  const failed = tasks.filter(t => t.status === 'failed')
  const durations = tasks
    .filter(t => (t.duration || 0) > 0)
    .map(t => (t.duration || 0) as number)

  return {
    total_tasks: tasks.length,
    completed_tasks: completed.length,
    failed_tasks: failed.length,
    avg_duration: durations.length > 0
      ? durations.reduce((a, b) => (a || 0) + (b || 0), 0) / durations.length
      : 0
  }
})

// 筛选后的历史记录
const filteredHistory = computed(() => {
  let result = [...historyTasks.value]

  // 日期筛选
  if (dateRange.value && dateRange.value.length === 2) {
    const [start, end] = dateRange.value
    result = result.filter(task => {
      if (!task.created_at) return true
      return task.created_at >= start && task.created_at <= end
    })
  }

  // 状态筛选
  if (statusFilter.value) {
    result = result.filter(task => task.status === statusFilter.value)
  }

  // 排序
  if (sortProp.value) {
    result.sort((a, b) => {
      let aVal = a[sortProp.value as keyof TaskHistoryItem]
      let bVal = b[sortProp.value as keyof TaskHistoryItem]

      if (typeof aVal === 'string') {
        aVal = aVal?.toLowerCase() || ''
        bVal = bVal?.toLowerCase() || ''
      }

      if (sortOrder.value === 'ascending') {
        return aVal > bVal ? 1 : -1
      } else {
        return aVal < bVal ? 1 : -1
      }
    })
  }

  return result
})

// 分页后的数据
const paginatedHistory = computed(() => {
  const start = (currentPage.value - 1) * pageSize.value
  return filteredHistory.value.slice(start, start + pageSize.value)
})

// 获取历史记录
async function fetchHistory() {
  try {
    const response = await dataApi.getTaskHistory({
      start_date: dateRange.value?.[0] || '',
      end_date: dateRange.value?.[1] || '',
      status: statusFilter.value || undefined,
      limit: 1000
    })
    historyTasks.value = response.data || []
  } catch (error) {
    console.error('获取历史记录失败:', error)
    ElMessage.error('获取历史记录失败')
  }
}

// 刷新
async function refreshHistory() {
  await fetchHistory()
  ElMessage.success('刷新成功')
}

// 应用筛选
function applyFilters() {
  currentPage.value = 1
}

// 日期变更
function handleDateChange() {
  applyFilters()
}

// 分页变更
function handleSizeChange() {
  currentPage.value = 1
}

function handlePageChange() {
  // 分页变更无需特殊处理
}

// 排序变更
function handleSortChange({ prop, order }: { prop: string; order: string }) {
  sortProp.value = prop
  sortOrder.value = order
}

// 查看详情
function viewDetail(row: TaskHistoryItem) {
  currentTask.value = row
  detailVisible.value = true
}

// 重新运行
function reRunTask(row: TaskHistoryItem) {
  // 跳转到工作流设计器并加载此任务
  navigateToWorkflowDesigner(row)
}

// 删除历史任务
async function deleteHistoryTask(taskId: string) {
  try {
    await ElMessageBox.confirm(
      '确定要删除此历史记录吗？',
      '确认删除',
      { type: 'warning' }
    )

    await taskApi.delete(taskId)
    historyTasks.value = historyTasks.value.filter(t => t.id !== taskId)
    ElMessage.success('删除成功')
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 导出历史记录
function exportHistory() {
  const data = filteredHistory.value.map(task => ({
    任务ID: task.id,
    目标URL: task.url,
    状态: getStatusText(task.status),
    操作数: task.actions_count,
    执行时长: formatDuration(task.duration || 0),
    执行时间: formatDateTime(task.created_at),
    完成时间: formatDateTime(task.completed_at || '')
  }))

  const csv = [
    Object.keys(data[0] || {}).join(','),
    ...data.map(row => Object.values(row).join(','))
  ].join('\n')

  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `任务历史_${formatDateTime(new Date().toISOString())}.csv`
  link.click()

  ElMessage.success('导出成功')
}

// 跳转到工作流设计器
function navigateToWorkflowDesigner(task: TaskHistoryItem) {
  // 保存任务数据到sessionStorage
  sessionStorage.setItem('rerun_task', JSON.stringify({
    url: task.url,
    actions: task.actions
  }))

  // 跳转到工作流设计器
  window.location.href = '/workflow'
}

// 状态文本
function getStatusType(status: string): string {
  const map: Record<string, string> = {
    completed: 'success',
    failed: 'danger',
    running: 'warning',
    pending: 'info',
    cancelled: 'info'
  }
  return map[status] || 'info'
}

function getStatusText(status: string): string {
  const map: Record<string, string> = {
    completed: '成功',
    failed: '失败',
    running: '执行中',
    pending: '待执行',
    cancelled: '已取消'
  }
  return map[status] || status
}

// 生命周期
onMounted(() => {
  fetchHistory()
})
</script>

<style scoped>
.task-history {
  padding: 20px;
}

.header {
  margin-bottom: 20px;
}

.header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.actions {
  text-align: right;
}

.stats-row {
  margin-bottom: 20px;
}

.stat-card {
  text-align: center;
}

.stat-card.success :deep(.el-statistic__number) {
  color: #67C23A;
}

.stat-card.danger :deep(.el-statistic__number) {
  color: #F56C6C;
}

.stat-ratio {
  font-size: 14px;
  color: #909399;
}

.filter-card {
  margin-bottom: 20px;
}

.result-count {
  color: #909399;
  font-size: 14px;
  line-height: 32px;
}

.task-id {
  font-family: monospace;
  font-size: 12px;
}

.url-text {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 200px;
  display: inline-block;
}

.pagination-wrapper {
  margin-top: 20px;
  display: flex;
  justify-content: flex-end;
}

.task-info {
  margin-bottom: 20px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
}

.action-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.action-detail {
  font-size: 12px;
  color: #606266;
  margin-bottom: 4px;
}

.action-status {
  font-size: 12px;
  margin-top: 8px;
}

.action-status.success {
  color: #67C23A;
}

.action-status.failed {
  color: #F56C6C;
}
</style>
