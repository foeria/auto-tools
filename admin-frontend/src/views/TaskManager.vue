<template>
  <div class="task-manager">
    <el-row :gutter="20" class="header">
      <el-col :span="12">
        <h2>任务管理</h2>
      </el-col>
      <el-col :span="12" class="actions">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索任务..."
          style="width: 200px"
          clearable
        />
        <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 140px">
          <el-option label="全部" value="" />
          <el-option label="待执行" value="pending" />
          <el-option label="执行中" value="running" />
          <el-option label="已完成" value="completed" />
          <el-option label="失败" value="failed" />
        </el-select>
        <el-button type="primary" @click="refreshTasks">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </el-col>
    </el-row>
    
    <el-card shadow="never">
      <el-table
        :data="filteredTasks"
        style="width: 100%"
        row-key="id"
        :tree-props="{ children: 'children', hasChildren: 'hasChildren' }"
        default-expand-all
        @selection-change="handleSelectionChange"
      >
        <el-table-column type="selection" width="50" />
        <el-table-column prop="id" label="任务ID" width="220" />
        <el-table-column prop="url" label="目标URL" min-width="200">
          <template #default="{ row }">
            <el-tooltip :content="row.url" placement="top">
              <span class="url-text">{{ row.url }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column prop="actions_count" label="操作数" width="80" align="center" />
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">
              {{ getStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="completed_at" label="完成时间" width="160">
          <template #default="{ row }">
            {{ row.completed_at ? formatDate(row.completed_at) : '-' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center" fixed="right">
          <template #default="{ row }">
            <el-button-group>
              <el-tooltip content="查看详情" placement="top">
                <el-button size="small" @click="viewTaskDetail(row)">
                  <el-icon><View /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="重新运行" placement="top">
                <el-button 
                  size="small" 
                  type="primary"
                  :disabled="row.status === 'running'"
                  @click="reRunTask(row)"
                >
                  <el-icon><VideoPlay /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
                <el-button 
                  size="small" 
                  type="danger"
                  @click="deleteTask(row.id)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-tooltip>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
      
      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100]"
          :total="totalTasks"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="handleSizeChange"
          @current-change="handlePageChange"
        />
      </div>
    </el-card>
    
    <el-dialog
      v-model="detailDialogVisible"
      title="任务详情"
      width="800px"
      destroy-on-close
    >
      <el-descriptions :column="2" border v-if="currentTask">
        <el-descriptions-item label="任务ID">
          {{ currentTask.id }}
        </el-descriptions-item>
        <el-descriptions-item label="状态">
          <el-tag :type="getStatusType(currentTask.status)">
            {{ getStatusText(currentTask.status) }}
          </el-tag>
        </el-descriptions-item>
        <el-descriptions-item label="目标URL" :span="2">
          {{ currentTask.url }}
        </el-descriptions-item>
        <el-descriptions-item label="创建时间">
          {{ formatDate(currentTask.created_at) }}
        </el-descriptions-item>
        <el-descriptions-item label="完成时间">
          {{ currentTask.completed_at ? formatDate(currentTask.completed_at) : '-' }}
        </el-descriptions-item>
      </el-descriptions>
      
      <el-divider content-position="left">执行步骤</el-divider>
      
      <el-timeline v-if="currentTask?.actions">
        <el-timeline-item
          v-for="(action, index) in currentTask.actions"
          :key="index"
          :timestamp="`步骤 ${index + 1}`"
          placement="top"
        >
          <el-card shadow="never">
            <template #header>
              <span>{{ action.type?.toUpperCase() }}</span>
            </template>
            <pre>{{ JSON.stringify(action, null, 2) }}</pre>
          </el-card>
        </el-timeline-item>
      </el-timeline>
      
      <el-divider content-position="left" v-if="currentTask?.result">
        执行结果
      </el-divider>
      
      <el-input
        v-if="currentTask?.result"
        type="textarea"
        :rows="10"
        :model-value="JSON.stringify(currentTask.result, null, 2)"
        readonly
      />
      
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
        <el-button 
          type="primary" 
          @click="reRunTask(currentTask)"
          v-if="currentTask"
        >
          重新运行
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, View, VideoPlay, Delete } from '@element-plus/icons-vue'
import axios from 'axios'

interface Task {
  id: string
  url: string
  actions: any[]
  actions_count?: number
  status: string
  result?: any
  error?: string
  created_at: string
  completed_at?: string
}

const tasks = ref<Task[]>([])
const searchKeyword = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const totalTasks = ref(0)
const selectedTasks = ref<Task[]>([])
const detailDialogVisible = ref(false)
const currentTask = ref<Task | null>(null)

const filteredTasks = computed(() => {
  return tasks.value.filter(task => {
    const matchKeyword = !searchKeyword.value || 
      task.id.includes(searchKeyword.value) ||
      task.url.includes(searchKeyword.value)
    const matchStatus = !statusFilter.value || task.status === statusFilter.value
    return matchKeyword && matchStatus
  })
})

function getStatusType(status: string): string {
  const typeMap: Record<string, string> = {
    pending: 'info',
    running: 'warning',
    completed: 'success',
    failed: 'danger'
  }
  return typeMap[status] || ''
}

function getStatusText(status: string): string {
  const textMap: Record<string, string> = {
    pending: '待执行',
    running: '执行中',
    completed: '已完成',
    failed: '失败'
  }
  return textMap[status] || status
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  return new Date(dateStr).toLocaleString('zh-CN')
}

async function fetchTasks() {
  try {
    const params = new URLSearchParams()
    if (statusFilter.value) params.append('status', statusFilter.value)
    params.append('limit', '100')
    params.append('offset', '0')
    
    const response = await axios.get(`http://localhost:8000/api/tasks?${params.toString()}`)
    tasks.value = response.data.tasks.map((task: any) => ({
      ...task,
      actions_count: task.actions?.length || 0
    }))
    totalTasks.value = response.data.total
  } catch (error) {
    console.error('获取任务列表失败:', error)
    tasks.value = generateMockTasks()
    totalTasks.value = tasks.value.length
  }
}

function generateMockTasks(): Task[] {
  return [
    {
      id: 'task-001',
      url: 'https://www.example.com',
      actions: [
        { type: 'goto', url: 'https://www.example.com' },
        { type: 'click', selector: '#search-btn' },
        { type: 'input', selector: '#keyword', value: 'test' },
        { type: 'wait', timeout: 2000 },
        { type: 'extract', selectors: ['.result-item'] }
      ],
      actions_count: 5,
      status: 'completed',
      created_at: new Date(Date.now() - 3600000).toISOString(),
      completed_at: new Date(Date.now() - 3500000).toISOString()
    },
    {
      id: 'task-002',
      url: 'https://www.example.org',
      actions: [
        { type: 'goto', url: 'https://www.example.org' },
        { type: 'input', selector: '#username', value: 'admin' },
        { type: 'input', selector: '#password', value: '123456' },
        { type: 'click', selector: '#login-btn' }
      ],
      actions_count: 4,
      status: 'running',
      created_at: new Date(Date.now() - 600000).toISOString()
    },
    {
      id: 'task-003',
      url: 'https://www.example.net',
      actions: [
        { type: 'goto', url: 'https://www.example.net' },
        { type: 'wait', timeout: 5000 }
      ],
      actions_count: 2,
      status: 'failed',
      error: 'Timeout waiting for element',
      created_at: new Date(Date.now() - 7200000).toISOString()
    },
    {
      id: 'task-004',
      url: 'https://www.example.cn',
      actions: [
        { type: 'goto', url: 'https://www.example.cn' },
        { type: 'click', by_image: true, templatePath: 'submit.png' },
        { type: 'extract', selectors: ['.content'] }
      ],
      actions_count: 3,
      status: 'pending',
      created_at: new Date(Date.now() - 1800000).toISOString()
    }
  ]
}

function handleSelectionChange(selection: Task[]) {
  selectedTasks.value = selection
}

function handleSizeChange(val: number) {
  pageSize.value = val
  currentPage.value = 1
}

function handlePageChange(val: number) {
  currentPage.value = val
}

async function refreshTasks() {
  ElMessage.info('正在刷新...')
  await fetchTasks()
  ElMessage.success('已刷新')
}

function viewTaskDetail(task: Task) {
  currentTask.value = task
  detailDialogVisible.value = true
}

async function reRunTask(task: Task) {
  try {
    await ElMessageBox.confirm(`确定要重新运行任务 "${task.id}" 吗？`, '确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
    
    ElMessage.info('正在重新提交任务...')
    
    const response = await axios.post(`http://localhost:8000/api/tasks/${task.id}/retry`)
    
    ElMessage.success(`任务已重新提交，新任务ID: ${response.data.task_id}`)
    await fetchTasks()
    detailDialogVisible.value = false
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('重新运行任务失败:', error)
      ElMessage.error(error.response?.data?.detail || '重新运行任务失败')
    } else {
      ElMessage.info('取消操作')
    }
  }
}

async function deleteTask(taskId: string) {
  try {
    await ElMessageBox.confirm('确定要删除该任务吗？此操作不可恢复。', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    
    await axios.delete(`http://localhost:8000/api/tasks/${taskId}`)
    tasks.value = tasks.value.filter(t => t.id !== taskId)
    totalTasks.value = tasks.value.length
    ElMessage.success('任务已删除')
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除任务失败:', error)
      ElMessage.error(error.response?.data?.detail || '删除任务失败')
    } else {
      ElMessage.info('取消删除')
    }
  }
}

onMounted(() => {
  fetchTasks()
})
</script>

<style scoped lang="scss">
.task-manager {
  .header {
    margin-bottom: 20px;
    
    h2 {
      margin: 0;
      font-size: 20px;
      color: #303133;
    }
    
    .actions {
      display: flex;
      gap: 12px;
      justify-content: flex-end;
    }
  }
  
  .url-text {
    display: inline-block;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    vertical-align: bottom;
  }
  
  .pagination-wrapper {
    display: flex;
    justify-content: flex-end;
    margin-top: 20px;
    padding-top: 20px;
    border-top: 1px solid #ebeef5;
  }
}
</style>
