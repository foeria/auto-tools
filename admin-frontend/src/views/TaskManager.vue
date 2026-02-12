<template>
  <div class="task-manager">
    <el-row :gutter="20" class="header">
      <el-col :span="12">
        <h2>任务与工作流管理</h2>
      </el-col>
      <el-col :span="12" class="actions">
        <el-button type="primary" @click="goToWorkflowDesigner">
          <el-icon><Plus /></el-icon>
          新建工作流
        </el-button>
        <el-button @click="refreshTasks">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <el-tabs v-model="activeTab" @tab-change="handleTabChange">
        <!-- 任务列表标签页 -->
        <el-tab-pane label="任务列表" name="tasks">
          <el-row :gutter="20" class="filter-bar">
            <el-col :span="12">
              <el-input
                v-model="searchKeyword"
                placeholder="搜索任务..."
                style="width: 200px"
                clearable
              />
            </el-col>
            <el-col :span="12" style="text-align: right;">
              <el-select v-model="statusFilter" placeholder="状态筛选" clearable style="width: 140px">
                <el-option label="全部" value="" />
                <el-option label="待执行" value="pending" />
                <el-option label="执行中" value="running" />
                <el-option label="已完成" value="completed" />
                <el-option label="失败" value="failed" />
              </el-select>
            </el-col>
          </el-row>

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
        </el-tab-pane>

        <!-- 工作流管理标签页 -->
        <el-tab-pane label="工作流管理" name="workflows">
          <el-row :gutter="20" class="filter-bar">
            <el-col :span="12">
              <span class="workflow-count">已保存工作流: {{ savedWorkflows.length }} 个</span>
            </el-col>
            <el-col :span="12" style="text-align: right;">
              <el-button size="small" @click="loadSavedWorkflows">
                <el-icon><Refresh /></el-icon>
                刷新列表
              </el-button>
            </el-col>
          </el-row>

          <el-table
            :data="savedWorkflows"
            style="width: 100%"
            v-if="savedWorkflows.length > 0"
          >
            <el-table-column prop="name" label="工作流名称" min-width="180">
              <template #default="{ row }">
                <div class="workflow-name">
                  <el-icon size="18"><Operation /></el-icon>
                  <span>{{ row.name }}</span>
                </div>
              </template>
            </el-table-column>
            <el-table-column prop="nodes" label="节点数" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small">{{ row.nodes?.length || 0 }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="创建时间" width="160">
              <template #default="{ row }">
                {{ formatDate(row.created_at) }}
              </template>
            </el-table-column>
            <el-table-column label="操作" width="220" align="center">
              <template #default="{ row }">
                <el-button-group>
                  <el-tooltip content="编辑工作流" placement="top">
                    <el-button size="small" type="primary" @click="editWorkflow(row)">
                      <el-icon><Edit /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="运行工作流" placement="top">
                    <el-button size="small" type="success" @click="runWorkflow(row)">
                      <el-icon><VideoPlay /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="导出JSON" placement="top">
                    <el-button size="small" @click="exportWorkflow(row)">
                      <el-icon><Download /></el-icon>
                    </el-button>
                  </el-tooltip>
                  <el-tooltip content="删除" placement="top">
                    <el-button size="small" type="danger" @click="deleteSavedWorkflow(row.id)">
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </el-tooltip>
                </el-button-group>
              </template>
            </el-table-column>
          </el-table>

          <el-empty v-else description="暂无已保存的工作流">
            <el-button type="primary" @click="goToWorkflowDesigner">创建第一个工作流</el-button>
          </el-empty>
        </el-tab-pane>
      </el-tabs>
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
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, View, VideoPlay, Delete, Plus, Edit, Download, Operation } from '@element-plus/icons-vue'
import { taskApi } from '@/services/api'

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

const router = useRouter()
const tasks = ref<Task[]>([])
const searchKeyword = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = ref(10)
const totalTasks = ref(0)
const selectedTasks = ref<Task[]>([])
const detailDialogVisible = ref(false)
const currentTask = ref<Task | null>(null)
const activeTab = ref('tasks')

// 工作流相关
const savedWorkflows = ref<any[]>([])

interface WorkflowData {
  id: string
  name: string
  nodes: any[]
  edges: any[]
  actions: any[]
  created_at: string
}

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
    const response = await taskApi.list(statusFilter.value || undefined, 100, 0)
    tasks.value = response.tasks.map((task: any) => ({
      ...task,
      actions_count: task.actions?.length || 0
    }))
    totalTasks.value = response.total
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

    const response = await taskApi.retry(task.id)

    ElMessage.success(`任务已重新提交，新任务ID: ${response.task_id}`)
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

    await taskApi.delete(taskId)
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

// ========== 工作流管理相关函数 ==========

function handleTabChange(tab: string) {
  if (tab === 'workflows') {
    loadSavedWorkflows()
  }
}

function loadSavedWorkflows() {
  savedWorkflows.value = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith('workflow_')) {
      try {
        const data = JSON.parse(localStorage.getItem(key) || '{}')
        savedWorkflows.value.push(data)
      } catch (e) {
        console.error('解析工作流数据失败:', e)
      }
    }
  }
  // 按创建时间倒序排列
  savedWorkflows.value.sort((a, b) => {
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  })
}

function editWorkflow(workflow: WorkflowData) {
  // 跳转到工作流设计器并加载该工作流
  router.push({
    path: '/workflow',
    query: { workflowId: workflow.id }
  })
}

function runWorkflow(workflow: WorkflowData) {
  // 将工作流转换为任务并执行
  const taskData = {
    url: workflow.actions.find((a: any) => a.type === 'goto')?.url || '',
    actions: workflow.actions,
    workflow_name: workflow.name
  }

  ElMessageBox.confirm(
    `确定要运行工作流 "${workflow.name}" 吗？\n目标URL: ${taskData.url}\n操作数: ${workflow.actions.length}`,
    '确认运行',
    {
      confirmButtonText: '确定运行',
      cancelButtonText: '取消',
      type: 'info'
    }
  ).then(async () => {
    try {
      const response = await taskApi.create(taskData)
      ElMessage.success(`任务已创建，ID: ${response.task_id}`)
      activeTab.value = 'tasks'
      fetchTasks()
    } catch (error: any) {
      console.error('创建任务失败:', error)
      ElMessage.error(error.response?.data?.detail || '创建任务失败')
    }
  }).catch(() => {
    ElMessage.info('取消运行')
  })
}

function exportWorkflow(workflow: WorkflowData) {
  const dataStr = JSON.stringify(workflow, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${workflow.name}.json`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
  ElMessage.success('工作流已导出')
}

function deleteSavedWorkflow(workflowId: string) {
  ElMessageBox.confirm(
    '确定要删除该工作流吗？此操作不可恢复。',
    '警告',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(() => {
    localStorage.removeItem(`workflow_${workflowId}`)
    savedWorkflows.value = savedWorkflows.value.filter(w => w.id !== workflowId)
    ElMessage.success('工作流已删除')
  }).catch(() => {
    ElMessage.info('取消删除')
  })
}

function goToWorkflowDesigner() {
  router.push('/workflow')
}

// ========== 任务管理相关函数 ==========

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

  .filter-bar {
    margin-bottom: 16px;
  }

  .url-text {
    display: inline-block;
    max-width: 300px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    vertical-align: bottom;
  }

  .workflow-count {
    font-size: 14px;
    color: #606266;
    line-height: 32px;
  }

  .workflow-name {
    display: flex;
    align-items: center;
    gap: 8px;
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
