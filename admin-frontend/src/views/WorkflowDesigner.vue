<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox, ElNotification } from 'element-plus'
import { VueFlow, useVueFlow, type Node, type Edge, type Connection } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import { Background } from '@vue-flow/background'
import WorkflowNode from '@/components/workflow/WorkflowNode.vue'
import WorkflowEdge from '@/components/workflow/WorkflowEdge.vue'
import NodeConfigPanel from '@/components/workflow/NodeConfigPanel.vue'
import ExecutionMonitor from '@/components/ExecutionMonitor.vue'
import { useWorkflowStore, type ActionNode } from '@/stores/workflow'
import { taskApi } from '@/services/api'
import { useWebSocket, wsService } from '@/services/websocket'
import { useWorkflowValidation } from '@/composables/useWorkflowValidation'
import { useNodeSearch } from '@/composables/useNodeSearch'
import { 
  DocumentChecked, 
  VideoPlay, 
  Delete, 
  Upload, 
  Download, 
  FolderOpened,
  Warning,
  CircleCheck,
  CircleClose,
  Search,
  Filter,
  Close,
  Clock
} from '@element-plus/icons-vue'

const store = useWorkflowStore()
const route = useRoute()
const router = useRouter()
const { connect: wsConnect, subscribe: wsSubscribe } = useWebSocket()

const {
  addEdges,
  addNodes,
  onNodeDragStop,
  onPaneReady,
  project,
  vueFlowRef
} = useVueFlow()

const selectedNode = ref<ActionNode | null>(null)
const selectedEdgeId = ref<string | null>(null)
const expandedCategories = ref(['browser', 'interaction', 'extraction', 'ai', 'control', 'file'])
const workflowName = ref('')
const workflowId = ref<string | null>(null)
const savedWorkflows = ref<Array<{ id: string; name: string; created_at: string }>>([])
const saveDialogVisible = ref(false)
const loadDialogVisible = ref(false)
const isRunning = ref(false)
const showMonitor = ref(false)
const currentTaskId = ref<string | null>(null)
const monitorRef = ref<any>(null)
const showValidationPanel = ref(false)
const showSearchPanel = ref(false)
const runDialogVisible = ref(false)  // 运行确认对话框
const headlessMode = ref(false)  // 无头模式

const {
  validateWorkflow,
  isValid,
  errors,
  warnings
} = useWorkflowValidation()

const nodesByCategory = computed(() => store.nodesByCategory)

const workflowNodes = ref<Node[]>([])
const workflowEdges = ref<Edge[]>([])

const {
  filters,
  searchHistory,
  filteredNodes,
  search,
  setCategoryFilter,
  setTypeFilter,
  setErrorFilter,
  clearFilters,
  clearHistory,
  clearHighlights,
  jumpToNode,
  getNodeLabel,
  getAllNodeTypes,
  getAllCategories
} = useNodeSearch(workflowNodes)

// WebSocket连接状态管理
let wsReconnectTimer: ReturnType<typeof setTimeout> | null = null

// 等待WebSocket连接建立的辅助函数
async function waitForConnection(timeout = 5000): Promise<boolean> {
  const startTime = Date.now()
  while (Date.now() - startTime < timeout) {
    if (wsService.isOpen()) {
      return true
    }
    await new Promise(resolve => setTimeout(resolve, 100))
  }
  return false
}

// 从URL参数加载工作流
onMounted(() => {
  const workflowIdFromQuery = route.query.workflowId as string
  const templateIdFromQuery = route.query.templateId as string

  if (workflowIdFromQuery) {
    // 从localStorage加载指定的工作流
    const storedData = localStorage.getItem(`workflow_${workflowIdFromQuery}`)
    if (storedData) {
      try {
        const data = JSON.parse(storedData)
        loadWorkflowData(data)
        ElMessage.success(`已加载工作流: ${data.name}`)
        // 清除URL参数，防止刷新时重复加载
        router.replace({ query: {} })
      } catch (e) {
        console.error('加载工作流失败:', e)
        ElMessage.error('加载工作流失败')
      }
    } else {
      ElMessage.warning('工作流不存在或已被删除')
      router.replace({ query: {} })
    }
  } else if (templateIdFromQuery) {
    // 处理模板ID（如果需要）
    ElMessage.info('模板功能开发中')
    router.replace({ query: {} })
  }

  // 加载工作流列表
  loadSavedWorkflows()
})

// 监听节点变化，同步 selectedNode 状态
watch(workflowNodes, () => {
  if (selectedNode.value) {
    const node = workflowNodes.value.find(n => n.id === selectedNode.value?.id)
    if (!node) {
      selectedNode.value = null
    }
  }
}, { deep: true })

function loadWorkflowData(data: any) {
  workflowName.value = data.name || ''
  workflowId.value = data.id || null

  // 转换VueFlow格式的节点
  if (data.nodes && Array.isArray(data.nodes)) {
    workflowNodes.value = data.nodes.map((node: any) => ({
      id: node.id,
      type: node.type,
      position: node.position,
      data: node.data,
      label: node.label
    }))
  }

  // 转换边
  if (data.edges && Array.isArray(data.edges)) {
    workflowEdges.value = data.edges.map((edge: any) => ({
      id: edge.id,
      source: edge.source,
      target: edge.target,
      type: edge.type || 'default',
      animated: edge.animated,
      style: edge.style,
      label: edge.label
    }))
  }

  // 更新nodeIdCounter
  if (workflowNodes.value.length > 0) {
    const maxId = workflowNodes.value.reduce((max: number, node: any) => {
      const match = node.id.match(/node-(\d+)-/)
      if (match) {
        return Math.max(max, parseInt(match[1]))
      }
      return max
    }, 0)
    nodeIdCounter = maxId
  }
}

let nodeIdCounter = 0

function generateNodeId(): string {
  return `node-${++nodeIdCounter}-${Date.now()}`
}

function getCategoryName(category: string): string {
  const names: Record<string, string> = {
    browser: '浏览器',
    interaction: '交互',
    extraction: '提取',
    ai: 'AI智能',
    control: '控制',
    file: '文件'
  }
  return names[category] || category
}

function onDragStart(event: DragEvent, node: ActionNode) {
  if (event.dataTransfer) {
    event.dataTransfer.setData('application/vueflow', JSON.stringify(node))
    event.dataTransfer.effectAllowed = 'copy'
  }
}

function onDragOver(event: DragEvent) {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'copy'
  }
}

function onDrop(event: DragEvent) {
  const data = event.dataTransfer?.getData('application/vueflow')
  if (!data) return
  
  try {
    const nodeData = JSON.parse(data) as ActionNode
    const { left, top } = vueFlowRef.value?.getBoundingClientRect() || { left: 0, top: 0 }
    const position = project({
      x: event.clientX - left,
      y: event.clientY - top
    })
    
    const newNode: Node = {
      id: generateNodeId(),
      type: 'workflow-node',
      position,
      data: {
        ...nodeData,
        id: generateNodeId()
      }
    }
    
    newNode.data.id = newNode.id
    
    addNodes([newNode])
    
    if (workflowNodes.value.length > 0) {
      const lastNode = workflowNodes.value[workflowNodes.value.length - 1]
      if (lastNode.id !== newNode.id) {
        const edge: Edge = {
          id: `e-${lastNode.id}-${newNode.id}`,
          type: 'workflow-edge',
          source: lastNode.id,
          target: newNode.id
        }
        addEdges([edge])
      }
    }
  } catch (e) {
    console.error('Failed to parse node data:', e)
  }
}

function handleConnect(params: Connection) {
  const edge: Edge = {
    id: `e-${params.source}-${params.target}`,
    type: 'workflow-edge',
    source: params.source,
    target: params.target
  }
  addEdges([edge])
}

onNodeDragStop((event) => {
  const node = event.node
  const nodeData = workflowNodes.value.find(n => n.id === node.id)
  if (nodeData) {
    store.updateNodePosition(node.id, node.position)
  }
})

onPaneReady(() => {
  console.log('Flow ready')
})

function selectNode(nodeId: string) {
  const node = workflowNodes.value.find(n => n.id === nodeId)
  if (node) {
    selectedNode.value = node.data as ActionNode
    store.selectedNodeId = nodeId
  }
}

function deleteNode(nodeId: string) {
  workflowNodes.value = workflowNodes.value.filter(n => n.id !== nodeId)
  workflowEdges.value = workflowEdges.value.filter(e => e.source !== nodeId && e.target !== nodeId)
  selectedEdgeId.value = null
  
  if (selectedNode.value?.id === nodeId) {
    selectedNode.value = null
  }
}

function updateSelectedNode(config: Record<string, any>) {
  if (selectedNode.value) {
    selectedNode.value.config = { ...selectedNode.value.config, ...config }
    const node = workflowNodes.value.find(n => n.id === selectedNode.value?.id)
    if (node) {
      node.data = { ...selectedNode.value }
    }
  }
}

async function saveWorkflow() {
  if (workflowNodes.value.length === 0) {
    ElMessage.warning('工作流为空，无法保存')
    return
  }
  
  const validation = validateWorkflow(workflowNodes.value, workflowEdges.value)
  
  if (!validation.isValid) {
    showValidationPanel.value = true
    ElMessageBox.confirm(
      `工作流存在 ${validation.errors.length} 个错误和 ${validation.warnings.length} 个警告，是否仍要保存？`,
      '验证警告',
      {
        confirmButtonText: '仍要保存',
        cancelButtonText: '取消',
        type: 'warning'
      }
    ).then(async () => {
      await doSaveWorkflow()
    }).catch(() => {
      ElMessage.info('已取消保存')
    })
    return
  }

  if (validation.warnings.length > 0) {
    ElNotification({
      title: '验证提示',
      message: `工作流验证通过，但存在 ${validation.warnings.length} 个建议`,
      type: 'info',
      duration: 3000
    })
  }
  
  await doSaveWorkflow()
}

async function doSaveWorkflow() {
  try {
    await ElMessageBox.confirm('确定要保存当前工作流吗？', '确认保存', {       
      confirmButtonText: '保存',
      cancelButtonText: '取消'
    })
    
    const actions = workflowNodes.value.map(node => {
      const nodeData = node.data as ActionNode & { id: string }
      return {
        type: nodeData.type,
        id: nodeData.id,
        selector: nodeData.config?.selector || '',
        value: nodeData.config?.value || '',
        url: nodeData.config?.url || '',
        timeout: nodeData.config?.timeout || 5000,
        by_image: nodeData.config?.byImage || false,
        template_path: nodeData.config?.templatePath || '',
        clear: nodeData.config?.clear ?? true,
        press_enter: nodeData.config?.pressEnter ?? false,
        state: nodeData.config?.state || 'visible',
        script: nodeData.config?.code || '',
        selectorList: nodeData.config?.selectorList || [],
        extract_type: nodeData.config?.extractType || 'text',
        attribute: nodeData.config?.attribute || '',
        direction: nodeData.config?.direction || 'down',
        amount: nodeData.config?.amount || 500,
        fullPage: nodeData.config?.fullPage || false,
        savePath: nodeData.config?.savePath || '',
        imagePath: nodeData.config?.imagePath || '',
        threshold: nodeData.config?.threshold || 0.8,
        x: nodeData.config?.offsetX || 0,
        y: nodeData.config?.offsetY || 0,
        filePaths: nodeData.config?.filePaths || [],
        keys: nodeData.config?.keys || [],
        selectors: nodeData.config?.selectors || [],
        conditions: nodeData.config?.conditions || [],
        logic: nodeData.config?.logic || 'and',
        loopType: nodeData.config?.type || 'times',
        loopTimes: nodeData.config?.times || 10,
        targetX: nodeData.config?.targetX || 0,
        targetY: nodeData.config?.targetY || 0,
        targetSelector: nodeData.config?.targetSelector || '',
        sourceSelector: nodeData.config?.sourceSelector || '',
        action: nodeData.config?.action || 'next',
        index: nodeData.config?.index || 0
      }
    })
    
    const workflowData = {
      id: workflowId.value || `workflow-${Date.now()}`,
      name: workflowName.value || `未命名工作流-${new Date().toLocaleDateString()}`,
      nodes: workflowNodes.value,
      edges: workflowEdges.value,
      actions: actions,
      created_at: new Date().toISOString()
    }
    
    localStorage.setItem(`workflow_${workflowData.id}`, JSON.stringify(workflowData))
    
    if (!workflowId.value) {
      workflowId.value = workflowData.id
    }
    
    ElMessage.success(`工作流 "${workflowData.name}" 保存成功`)
  } catch {
    ElMessage.info('取消保存')
  }
}

async function runWorkflow() {
  if (workflowNodes.value.length === 0) {
    ElMessage.warning('请先添加节点到工作流')
    return
  }

  const validation = validateWorkflow(workflowNodes.value, workflowEdges.value)

  if (!validation.isValid) {
    showValidationPanel.value = true
    ElMessage.error(`工作流存在 ${validation.errors.length} 个错误，无法运行`)
    return
  }

  if (validation.warnings.length > 0) {
    ElNotification({
      title: '验证建议',
      message: `工作流存在 ${validation.warnings.length} 个建议，建议查看验证面板`,
      type: 'warning',
      duration: 4000
    })
  }

  // 显示运行确认对话框
  runDialogVisible.value = true
}

async function confirmRun() {
  runDialogVisible.value = false
  isRunning.value = true

  try {
    const actions = workflowNodes.value.map(node => {
      const nodeData = node.data as ActionNode & { id: string }
      return {
        type: nodeData.type,
        id: nodeData.id,
        selector: nodeData.config?.selector || '',
        value: nodeData.config?.value || '',
        url: nodeData.config?.url || '',
        timeout: nodeData.config?.timeout || 5000,
        by_image: nodeData.config?.byImage || false,
        template_path: nodeData.config?.templatePath || '',
        clear: nodeData.config?.clear ?? true,
        press_enter: nodeData.config?.pressEnter ?? false,
        state: nodeData.config?.state || 'visible',
        script: nodeData.config?.code || '',
        selectorList: nodeData.config?.selectorList || [],
        extract_type: nodeData.config?.extractType || 'text',
        attribute: nodeData.config?.attribute || '',
        direction: nodeData.config?.direction || 'down',
        amount: nodeData.config?.amount || 500,
        fullPage: nodeData.config?.fullPage || false,
        savePath: nodeData.config?.savePath || '',
        imagePath: nodeData.config?.imagePath || '',
        threshold: nodeData.config?.threshold || 0.8,
        x: nodeData.config?.offsetX || 0,
        y: nodeData.config?.offsetY || 0,
        filePaths: nodeData.config?.filePaths || [],
        keys: nodeData.config?.keys || [],
        selectors: nodeData.config?.selectors || [],
        conditions: nodeData.config?.conditions || [],
        logic: nodeData.config?.logic || 'and',
        loopType: nodeData.config?.type || 'times',
        loopTimes: nodeData.config?.times || 10,
        targetX: nodeData.config?.targetX || 0,
        targetY: nodeData.config?.targetY || 0,
        targetSelector: nodeData.config?.targetSelector || '',
        sourceSelector: nodeData.config?.sourceSelector || '',
        action: nodeData.config?.action || 'next',
        index: nodeData.config?.index || 0
      }
    })

    // 查找第一个需要URL的节点（goto类型）
    const gotoNode = workflowNodes.value.find(node => (node.data as ActionNode)?.type === 'goto')
    const startUrl = gotoNode ? (gotoNode.data as ActionNode).config?.url || '' : ''

    if (!startUrl) {
      ElMessage.warning('请添加访问页面节点并设置起始URL')
      isRunning.value = false
      return
    }

    const taskData = {
      url: startUrl,
      actions: actions as any[],
      priority: 1,
      max_retries: 3,
      headless: headlessMode.value,
      metadata: {
        workflow_id: workflowId.value || 'unknown',
        workflow_name: workflowName.value || '未命名工作流',
        created_at: new Date().toISOString()
      }
    }

    const response = await taskApi.create(taskData)
    ElMessage.success(`任务已提交成功！任务ID: ${response.task_id}`)

    currentTaskId.value = response.task_id

    // 确保WebSocket连接已建立
    if (!wsService.isOpen()) {
      wsConnect()
      const connected = await waitForConnection()
      if (!connected) {
        ElMessage.error('WebSocket连接失败，请检查后端服务')
        isRunning.value = false
        return
      }
    }
    wsSubscribe(response.task_id)

    showMonitor.value = true

  } catch (error: any) {
    console.error('Failed to create task:', error)
    ElMessage.error(`任务提交失败: ${error.response?.data?.detail || error.message || '未知错误'}`)
  } finally {
    isRunning.value = false
  }
}

function clearWorkflow() {
  try {
    ElMessageBox.confirm('确定要清空当前工作流吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      workflowNodes.value = []
      workflowEdges.value = []
      selectedNode.value = null
      ElMessage.success('工作流已清空')
    })
  } catch {
    ElMessage.info('取消清空')
  }
}

function onNodeClick(event: { node: Node }) {
  selectNode(event.node.id)
}

function selectNodeById(nodeId: string) {
  selectNode(nodeId)
}

function onEdgeClick(event: { edge: Edge }) {
  selectedEdgeId.value = event.edge.id
}

function deleteEdge(edgeId: string) {
  workflowEdges.value = workflowEdges.value.filter(e => e.id !== edgeId)
  if (selectedEdgeId.value === edgeId) {
    selectedEdgeId.value = null
  }
}

function onPaneClick() {
  selectedNode.value = null
  selectedEdgeId.value = null
  store.selectedNodeId = null
}

function onKeyDown(event: KeyboardEvent) {
  // 如果当前焦点在输入元素中，不处理键盘事件（防止误操作）
  const target = event.target as HTMLElement
  const tagName = target.tagName.toLowerCase()
  const isInputElement = tagName === 'input' || tagName === 'textarea' || tagName === 'select'

  if (isInputElement) {
    return
  }

  if (event.key === 'Delete' || event.key === 'Backspace') {
    if (selectedEdgeId.value) {
      deleteEdge(selectedEdgeId.value)
    } else if (selectedNode.value) {
      deleteNode(selectedNode.value.id)
    }
  }
}

async function loadSavedWorkflows() {
  const workflows: Array<{ id: string; name: string; created_at: string }> = []
  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i)
    if (key?.startsWith('workflow_')) {
      try {
        const data = JSON.parse(localStorage.getItem(key) || '{}')
        workflows.push({
          id: data.id,
          name: data.name || '未命名',
          created_at: data.created_at || ''
        })
      } catch (e) {
        console.error('Failed to parse workflow:', e)
      }
    }
  }
  savedWorkflows.value = workflows.sort((a, b) => 
    new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  )
}

function showSaveDialog() {
  if (!workflowName.value && workflowNodes.value.length > 0) {
    workflowName.value = `工作流-${new Date().toLocaleString()}`
  }
  saveDialogVisible.value = true
}

function showLoadDialog() {
  loadSavedWorkflows()
  loadDialogVisible.value = true
}

function loadWorkflow(id: string) {
  const dataStr = localStorage.getItem(`workflow_${id}`)
  if (!dataStr) {
    ElMessage.error('工作流数据不存在')
    return
  }
  
  try {
    const data = JSON.parse(dataStr)
    workflowNodes.value = data.nodes || []
    workflowEdges.value = data.edges || []
    workflowId.value = data.id
    workflowName.value = data.name || ''
    selectedNode.value = null
    loadDialogVisible.value = false
    ElMessage.success(`已加载工作流: ${data.name}`)
  } catch (e) {
    console.error('Failed to load workflow:', e)
    ElMessage.error('加载工作流失败')
  }
}

function confirmSave() {
  saveDialogVisible.value = false
  saveWorkflow()
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '-'
  try {
    return new Date(dateStr).toLocaleString('zh-CN')
  } catch {
    return '-'
  }
}

function deleteSavedWorkflow(id: string) {
  localStorage.removeItem(`workflow_${id}`)
  loadSavedWorkflows()
  ElMessage.success('工作流已删除')
}

void loadWorkflow
void confirmSave
void deleteSavedWorkflow

function importWorkflow() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.json'
  input.onchange = (e: Event) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (!file) return
    
    const reader = new FileReader()
    reader.onload = (event) => {
      try {
        const data = JSON.parse(event.target?.result as string)
        if (data.nodes && data.edges) {
          workflowNodes.value = data.nodes
          workflowEdges.value = data.edges
          workflowId.value = null
          workflowName.value = data.name || ''
          ElMessage.success('工作流导入成功')
        } else {
          ElMessage.error('文件格式不正确')
        }
      } catch (err) {
        ElMessage.error('解析文件失败')
      }
    }
    reader.readAsText(file)
  }
  input.click()
}

function exportWorkflow() {
  if (workflowNodes.value.length === 0) {
    ElMessage.warning('没有可导出的工作流')
    return
  }
  
  const data = {
    id: workflowId.value || `workflow-${Date.now()}`,
    name: workflowName.value || '未命名工作流',
    nodes: workflowNodes.value,
    edges: workflowEdges.value,
    exported_at: new Date().toISOString()
  }
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${data.name || 'workflow'}.json`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('工作流已导出')
}
</script>

<template>
  <div class="workflow-designer" tabindex="0" @keydown="onKeyDown">
    <el-row :gutter="20" class="header">
      <el-col :span="12">
        <h2>拖拽式工作流设计器</h2>
        <span v-if="workflowName" class="workflow-name">{{ workflowName }}</span>
      </el-col>
      <el-col :span="12" class="actions">
        <el-button @click="importWorkflow">
          <el-icon><Upload /></el-icon>
          导入
        </el-button>
        <el-button @click="exportWorkflow">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
        <el-button @click="showLoadDialog">
          <el-icon><FolderOpened /></el-icon>
          加载
        </el-button>
        <el-button type="primary" @click="showSaveDialog">
          <el-icon><DocumentChecked /></el-icon>
          保存
        </el-button>
        <el-button type="success" @click="runWorkflow" :loading="isRunning">
          <el-icon><VideoPlay /></el-icon>
          {{ isRunning ? '运行中...' : '运行' }}
        </el-button>
        <el-button 
          :type="isValid ? 'info' : 'warning'" 
          @click="showValidationPanel = true; validateWorkflow(workflowNodes, workflowEdges)"
        >
          <el-icon><component :is="isValid ? 'CircleCheck' : 'Warning'" /></el-icon>
          验证{{ workflowNodes.length > 0 ? `(${errors.length + warnings.length})` : '' }}
        </el-button>
        <el-button @click="clearWorkflow">
          <el-icon><Delete /></el-icon>
          清空
        </el-button>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="content">
      <el-col :span="4" class="component-panel">
        <el-card shadow="never">
          <template #header>
            <div class="component-header">
              <span>组件库</span>
              <el-button 
                size="small" 
                :icon="filters.keyword || filters.category.length > 0 || filters.nodeType.length > 0 ? Close : Filter"
                @click="filters.keyword || filters.category.length > 0 || filters.nodeType.length > 0 ? clearFilters() : showSearchPanel = !showSearchPanel"
                :type="showSearchPanel ? 'primary' : 'default'"
                text
              >
                {{ filters.keyword || filters.category.length > 0 || filters.nodeType.length > 0 ? '清除' : '筛选' }}
              </el-button>
            </div>
          </template>
          
          <el-collapse v-model="expandedCategories">
            <el-collapse-item 
              v-for="(nodes, category) in nodesByCategory" 
              :key="category" 
              :name="category"
              :title="getCategoryName(category)"
            >
              <div
                v-for="node in nodes"
                :key="node.type"
                class="component-item"
                draggable="true"
                @dragstart="onDragStart($event, node)"
              >
                <el-icon size="14"><component :is="node.icon" /></el-icon>
                <span>{{ node.label }}</span>
              </div>
            </el-collapse-item>
          </el-collapse>
          
          <el-collapse v-model="expandedCategories" v-if="showSearchPanel" class="search-panel">
            <el-collapse-item title="搜索节点" name="search">
              <div class="search-form">
                <el-input
                  v-model="filters.keyword"
                  placeholder="搜索节点..."
                  :prefix-icon="Search"
                  clearable
                  @input="search(filters.keyword)"
                  class="search-input"
                />
                
                <el-select
                  v-model="filters.category"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="分类筛选"
                  clearable
                  class="filter-select"
                  @change="setCategoryFilter(filters.category)"
                >
                  <el-option
                    v-for="cat in getAllCategories()"
                    :key="cat.value"
                    :label="cat.label"
                    :value="cat.value"
                  />
                </el-select>
                
                <el-select
                  v-model="filters.nodeType"
                  multiple
                  collapse-tags
                  collapse-tags-tooltip
                  placeholder="节点类型"
                  clearable
                  class="filter-select"
                  @change="setTypeFilter(filters.nodeType)"
                >
                  <el-option
                    v-for="type in getAllNodeTypes()"
                    :key="type.value"
                    :label="type.label"
                    :value="type.value"
                  />
                </el-select>
                
                <el-radio-group
                  v-model="filters.hasErrors"
                  size="small"
                  class="error-filter"
                  @change="(val: boolean | null) => setErrorFilter(val)"
                >
                  <el-radio-button :label="null">全部</el-radio-button>
                  <el-radio-button :label="false">正常</el-radio-button>
                  <el-radio-button :label="true">有问题</el-radio-button>
                </el-radio-group>
              </div>
              
              <div class="search-results" v-if="filters.keyword || filters.category.length > 0 || filters.nodeType.length > 0">
                <div class="results-header">
                  <span>找到 {{ filteredNodes.length }} 个节点</span>
                  <el-button 
                    size="small" 
                    text 
                    type="primary"
                    @click="clearHighlights"
                  >
                    清除高亮
                  </el-button>
                </div>
                
                <div 
                  v-for="node in filteredNodes.slice(0, 20)" 
                  :key="node.id"
                  class="result-item"
                  @click="jumpToNode(node.id, (n) => selectNodeById(n.id))"
                >
                  <el-icon><component :is="(node.data as any)?.icon || 'Document'" /></el-icon>
                  <span class="result-label">{{ (node.data as any)?.label }}</span>
                  <el-tag size="small" type="info">
                    {{ getNodeLabel((node.data as any)?.type || '') }}
                  </el-tag>
                </div>
                
                <el-button 
                  v-if="filteredNodes.length > 20"
                  size="small" 
                  type="primary" 
                  text
                  class="view-more"
                >
                  查看更多 ({{ filteredNodes.length - 20 }} 个)
                </el-button>
                
                <el-empty 
                  v-if="filteredNodes.length === 0" 
                  description="未找到匹配的节点" 
                  :image-size="60"
                />
              </div>
              
              <div class="search-history" v-if="searchHistory.length > 0 && !filters.keyword">
                <div class="history-header">
                  <span>搜索历史</span>
                  <el-button 
                    size="small" 
                    text 
                    type="info"
                    @click="clearHistory"
                  >
                    清空
                  </el-button>
                </div>
                <div 
                  v-for="(item, index) in searchHistory.slice(0, 5)" 
                  :key="index"
                  class="history-item"
                  @click="search(item)"
                >
                  <el-icon><Clock /></el-icon>
                  <span>{{ item }}</span>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
          
          <el-alert
            type="info"
            :closable="false"
            show-icon
            class="drag-hint"
          >
            拖拽组件到画布
          </el-alert>
        </el-card>
      </el-col>
      
      <el-col :span="14" class="canvas-panel">
        <el-card shadow="never" class="flow-card">
          <template #header>
            <div class="canvas-header">
              <span>工作流画布</span>
              <span class="node-count">共 {{ workflowNodes.length }} 个节点</span>
            </div>
          </template>
          <div class="flow-container" @drop="onDrop" @dragover="onDragOver">
            <VueFlow
              v-model:nodes="workflowNodes"
              v-model:edges="workflowEdges"
              class="workflow-flow"
              :default-viewport="{ zoom: 1 }"
              :min-zoom="0.2"
              :max-zoom="2"
              :fit-view-on-init="true"
              :selected-edges="selectedEdgeId ? [selectedEdgeId] : []"
              @node-click="onNodeClick"
              @edge-click="onEdgeClick"
              @pane-click="onPaneClick"
              @connect="handleConnect"
            >
              <Background :gap="20" pattern-color="#aaa" />
              
              <template #node-workflow-node="nodeProps">
                <WorkflowNode v-bind="nodeProps" />
              </template>
              
              <template #edge-workflow-edge="edgeProps">
                <WorkflowEdge v-bind="edgeProps" />
              </template>
            </VueFlow>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6" class="property-panel">
        <el-card shadow="never">
          <template #header>
            <span>节点配置</span>
          </template>
          <NodeConfigPanel
            :node="selectedNode"
            @update:node="updateSelectedNode"
            @delete="deleteNode"
          />
        </el-card>
        
        <el-card shadow="never" class="preview-card">
          <template #header>
            <span>工作流概览</span>
          </template>
          <div class="overview-stats">
            <div class="stat-item">
              <span class="label">节点数</span>
              <span class="value">{{ workflowNodes.length }}</span>
            </div>
            <div class="stat-item">
              <span class="label">连接数</span>
              <span class="value">{{ workflowEdges.length }}</span>
            </div>
          </div>
        </el-card>
        
        <el-card shadow="never" class="validation-status-card">
          <template #header>
            <div class="validation-header">
              <span>验证状态</span>
              <el-tag :type="isValid ? 'success' : 'danger'" size="small">
                {{ isValid ? '通过' : '存在问题' }}
              </el-tag>
            </div>
          </template>
          <div class="validation-summary">
            <div class="summary-item error" v-if="errors.length > 0">
              <el-icon><CircleClose /></el-icon>
              <span>{{ errors.length }} 个错误</span>
            </div>
            <div class="summary-item warning" v-if="warnings.length > 0">
              <el-icon><Warning /></el-icon>
              <span>{{ warnings.length }} 个建议</span>
            </div>
            <div class="summary-item success" v-if="isValid && workflowNodes.length > 0">
              <el-icon><CircleCheck /></el-icon>
              <span>验证通过</span>
            </div>
            <div class="empty-tip" v-if="workflowNodes.length === 0">
              <el-empty description="工作流为空" :image-size="60" />
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>
    
    <el-drawer
      v-model="showMonitor"
      title="执行监控"
      direction="rtl"
      size="500px"
      :show-close="true"
      :close-on-click-modal="false"
    >
      <ExecutionMonitor
        ref="monitorRef"
        :task-id="currentTaskId || undefined"
        :auto-connect="false"
        :show-logs="true"
        :max-logs="100"
      />
    </el-drawer>

    <el-dialog v-model="saveDialogVisible" title="保存工作流" width="400px">
      <el-form label-width="80px">
        <el-form-item label="工作流名称">
          <el-input v-model="workflowName" placeholder="请输入工作流名称" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="saveDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmSave">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="loadDialogVisible" title="加载工作流" width="500px">
      <el-table :data="savedWorkflows" style="width: 100%" max-height="400">
        <el-table-column prop="name" label="工作流名称" min-width="150" />
        <el-table-column label="创建时间" min-width="150">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" @click="loadWorkflow(row.id)">加载</el-button>
            <el-button type="danger" size="small" @click="deleteSavedWorkflow(row.id)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="loadDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 运行确认对话框 -->
    <el-dialog v-model="runDialogVisible" title="运行工作流" width="450px">
      <div class="run-config">
        <el-alert
          title="即将开始执行工作流"
          type="info"
          :closable="false"
          show-icon
          style="margin-bottom: 20px"
        />
        <el-form label-width="100px">
          <el-form-item label="浏览器模式">
            <el-switch
              v-model="headlessMode"
              active-text="无头模式"
              inactive-text="有头模式"
              active-description="不显示浏览器窗口"
              inactive-description="显示浏览器窗口"
            />
          </el-form-item>
          <el-form-item label="运行说明">
            <div class="run-tips">
              <el-tag :type="headlessMode ? 'info' : 'success'" size="small" style="margin-right: 8px">
                {{ headlessMode ? '无头模式' : '有头模式' }}
              </el-tag>
              <span v-if="headlessMode">
                浏览器将在后台运行，不显示窗口界面，适合批量任务
              </span>
              <span v-else>
                浏览器窗口将显示，可以看到实时执行过程
              </span>
            </div>
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="runDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmRun">开始运行</el-button>
      </template>
    </el-dialog>

    <el-drawer
      v-model="showValidationPanel"
      title="工作流验证"
      direction="rtl"
      size="400px"
      :show-close="true"
    >
      <div class="validation-panel" v-if="workflowNodes.length > 0">
        <div class="validation-status-banner" :class="{ valid: isValid, invalid: !isValid }">
          <el-icon v-if="isValid" size="48"><CircleCheck /></el-icon>
          <el-icon v-else size="48"><CircleClose /></el-icon>
          <h3>{{ isValid ? '验证通过' : `发现 ${errors.length} 个问题` }}</h3>
        </div>
        
        <el-divider />
        
        <div class="validation-section" v-if="errors.length > 0">
          <h4 class="section-title error">
            <el-icon><CircleClose /></el-icon>
            错误
          </h4>
          <el-timeline>
            <el-timeline-item
              v-for="(error, index) in errors"
              :key="index"
              type="error"
              :timestamp="error.nodeId ? `节点: ${error.nodeId}` : ''"
            >
              <div class="validation-item">
                <p class="item-message">{{ error.message }}</p>
                <p class="item-suggestion" v-if="error.suggestion">
                  建议: {{ error.suggestion }}
                </p>
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>
        
        <div class="validation-section" v-if="warnings.length > 0">
          <h4 class="section-title warning">
            <el-icon><Warning /></el-icon>
            建议
          </h4>
          <el-timeline>
            <el-timeline-item
              v-for="(warning, index) in warnings"
              :key="index"
              type="warning"
              :timestamp="warning.nodeId ? `节点: ${warning.nodeId}` : ''"
            >
              <div class="validation-item">
                <p class="item-message">{{ warning.message }}</p>
                <p class="item-suggestion" v-if="warning.suggestion">
                  建议: {{ warning.suggestion }}
                </p>
              </div>
            </el-timeline-item>
          </el-timeline>
        </div>
        
        <div class="validation-actions">
          <el-button type="primary" @click="showValidationPanel = false">
            关闭
          </el-button>
          <el-button 
            type="primary" 
            plain 
            @click="validateWorkflow(workflowNodes, workflowEdges)"
          >
            重新验证
          </el-button>
        </div>
      </div>
      <el-empty 
        v-else 
        description="工作流为空，无法验证" 
        :image-size="100" 
      />
    </el-drawer>
  </div>
</template>

<script lang="ts">
export default {
  name: 'WorkflowDesigner'
}
</script>

<style scoped lang="scss">
.workflow-designer {
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  outline: none;
  
  .header {
    margin-bottom: 16px;
    
    h2 {
      margin: 0;
      font-size: 20px;
      color: #303133;
      display: inline-block;
      margin-right: 12px;
    }
    
    .workflow-name {
      font-size: 14px;
      color: #409eff;
      background: #ecf5ff;
      padding: 4px 12px;
      border-radius: 4px;
    }
    
    .actions {
      text-align: right;
    }
  }
  
  .content {
    flex: 1;
    min-height: 0;
  }
  
  .component-panel {
    :deep(.el-card__body) {
      max-height: calc(100vh - 160px);
      overflow-y: auto;
    }
    
    .component-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      margin: 4px 0;
      border: 1px solid #e4e7ed;
      border-radius: 4px;
      cursor: grab;
      transition: all 0.2s;
      font-size: 13px;
      
      &:hover {
        background: #ecf5ff;
        border-color: #409eff;
      }
      
      &:active {
        cursor: grabbing;
      }
    }
    
    :deep(.el-collapse-item__header) {
      font-size: 13px;
      font-weight: 500;
      padding-left: 8px;
    }
    
    :deep(.el-collapse-item__content) {
      padding: 4px 8px 8px;
    }
    
    .drag-hint {
      margin-top: 12px;
      font-size: 12px;
    }
  }
  
  .canvas-panel {
    .flow-card {
      height: 100%;
      
      :deep(.el-card__body) {
        height: calc(100% - 60px);
        padding: 0;
      }
    }
    
    .canvas-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .node-count {
        font-size: 12px;
        color: #909399;
      }
    }
    
    .flow-container {
      height: 100%;
      width: 100%;
    }
    
    .workflow-flow {
      height: 100%;
      width: 100%;
      background: #fafafa;
    }
  }
  
  .property-panel {
    :deep(.el-card__body) {
      max-height: calc(50vh - 100px);
      overflow-y: auto;
    }
    
    .preview-card {
      margin-top: 16px;
      
      .overview-stats {
        display: flex;
        gap: 16px;
        
        .stat-item {
          flex: 1;
          text-align: center;
          padding: 12px;
          background: #f5f7fa;
          border-radius: 4px;
          
          .label {
            display: block;
            font-size: 12px;
            color: #909399;
            margin-bottom: 4px;
          }
          
          .value {
            font-size: 24px;
            font-weight: 600;
            color: #409eff;
          }
        }
      }
      
      .validation-status-card {
        margin-top: 16px;
        
        .validation-header {
          display: flex;
          justify-content: space-between;
          align-items: center;
        }
        
        .validation-summary {
          .summary-item {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px 0;
            border-bottom: 1px solid #eee;
            
            &.error {
              color: #f56c6c;
            }
            
            &.warning {
              color: #e6a23c;
            }
            
            &.success {
              color: #67c23a;
            }
          }
          
          .empty-tip {
            padding: 20px 0;
          }
        }
      }
    }
  }
  
  .validation-panel {
    padding: 0 8px;
    
    .validation-status-banner {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding: 24px;
      border-radius: 8px;
      margin-bottom: 16px;
      
      &.valid {
        background: linear-gradient(135deg, #f0f9eb 0%, #e1f3d8 100%);
        color: #67c23a;
      }
      
      &.invalid {
        background: linear-gradient(135deg, #fef0f0 0%, #fde2e2 100%);
        color: #f56c6c;
      }
      
      h3 {
        margin-top: 12px;
        font-size: 18px;
      }
    }
    
    .validation-section {
      margin-bottom: 24px;
      
      .section-title {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 16px;
        font-size: 16px;
        
        &.error {
          color: #f56c6c;
        }
        
        &.warning {
          color: #e6a23c;
        }
      }
      
      .validation-item {
        background: #fafafa;
        padding: 12px;
        border-radius: 4px;
        border-left: 3px solid;
        
        .error & {
          border-left-color: #f56c6c;
        }
        
        .warning & {
          border-left-color: #e6a23c;
        }
        
        .item-message {
          margin: 0;
          font-size: 14px;
          color: #303133;
        }
        
        .item-suggestion {
          margin: 8px 0 0 0;
          font-size: 12px;
          color: #909399;
        }
      }
    }
    
    .validation-actions {
      display: flex;
      justify-content: flex-end;
      gap: 12px;
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid #eee;
    }
  }
  
  .component-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }
  
  .search-panel {
    margin-top: 12px;
    border: 1px solid var(--el-border-color-lighter);
    border-radius: 4px;
    
    :deep(.el-collapse-item__header) {
      padding: 8px 12px;
      font-size: 13px;
    }
    
    :deep(.el-collapse-item__content) {
      padding: 12px;
    }
    
    .search-form {
      display: flex;
      flex-direction: column;
      gap: 8px;
      
      .search-input {
        width: 100%;
      }
      
      .filter-select {
        width: 100%;
      }
      
      .error-filter {
        display: flex;
        width: 100%;
        
        .el-radio-button__inner {
          flex: 1;
          text-align: center;
        }
      }
    }
    
    .search-results {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid var(--el-border-color-lighter);
      
      .results-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
      
      .result-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px;
        border-radius: 4px;
        cursor: pointer;
        transition: background-color 0.2s;
        
        &:hover {
          background: var(--el-fill-color-light);
        }
        
        .result-label {
          flex: 1;
          font-size: 13px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
      
      .view-more {
        width: 100%;
        margin-top: 8px;
      }
    }
    
    .search-history {
      margin-top: 12px;
      padding-top: 12px;
      border-top: 1px solid var(--el-border-color-lighter);
      
      .history-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 8px;
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
      
      .history-item {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 6px 8px;
        border-radius: 4px;
        cursor: pointer;
        font-size: 12px;
        color: var(--el-text-color-regular);
        transition: background-color 0.2s;

        &:hover {
          background: var(--el-fill-color-light);
        }
      }
    }
  }

  .run-config {
    .run-tips {
      color: var(--el-text-color-secondary);
      font-size: 13px;
      line-height: 1.6;
    }
  }
}
</style>
