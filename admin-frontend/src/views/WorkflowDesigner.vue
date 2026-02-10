<template>
  <div class="workflow-designer">
    <el-row :gutter="20" class="header">
      <el-col :span="12">
        <h2>拖拽式工作流设计器</h2>
      </el-col>
      <el-col :span="12" class="actions">
        <el-button type="primary" @click="saveWorkflow">
          <el-icon><DocumentChecked /></el-icon>
          保存
        </el-button>
        <el-button type="success" @click="runWorkflow">
          <el-icon><VideoPlay /></el-icon>
          运行
        </el-button>
        <el-button @click="clearWorkflow">
          <el-icon><Delete /></el-icon>
          清空
        </el-button>
      </el-col>
    </el-row>
    
    <el-row :gutter="20" class="content">
      <el-col :span="5" class="component-panel">
        <el-card shadow="never">
          <template #header>
            <span>组件库</span>
          </template>
          <el-collapse v-model="expandedCategories">
            <el-collapse-item 
              v-for="(nodes, category) in nodesByCategory" 
              :key="category" 
              :name="category"
              :title="getCategoryName(category)"
            >
              <draggable
                :list="nodes"
                :group="{ name: 'workflow', pull: 'clone', put: false }"
                :sort="false"
                item-key="type"
                class="component-list"
                :clone="cloneNode"
              >
                <template #item="{ element }">
                  <div class="component-item" draggable="true">
                    <el-icon size="16"><component :is="element.icon" /></el-icon>
                    <span>{{ element.label }}</span>
                  </div>
                </template>
              </draggable>
            </el-collapse-item>
          </el-collapse>
        </el-card>
      </el-col>
      
      <el-col :span="13" class="canvas-panel">
        <el-card shadow="never">
          <template #header>
            <div class="canvas-header">
              <span>工作流画布</span>
              <span class="node-count">共 {{ currentWorkflow.length }} 个节点</span>
            </div>
          </template>
          <div 
            class="workflow-canvas"
            @dragover.prevent
            @drop="onCanvasDrop"
          >
            <el-empty v-if="currentWorkflow.length === 0" description="从左侧拖拽组件到此处">
              <template #image>
                <el-icon size="64" color="#909399"><Plus /></el-icon>
              </template>
            </el-empty>
            <draggable
              v-else
              v-model="currentWorkflow"
              group="workflow"
              item-key="id"
              class="workflow-list"
              ghost-class="ghost"
              handle=".node-header"
              animation="200"
              @change="onWorkflowChange"
            >
              <template #item="{ element, index }">
                <div 
                  class="workflow-node"
                  :class="{ 'selected': selectedNodeId === element.id }"
                  @click="selectNode(element.id)"
                >
                  <div class="node-header">
                    <el-icon size="16"><component :is="element.icon" /></el-icon>
                    <span>{{ element.label }}</span>
                    <el-tag size="small" :type="getNodeTagType(element.category)">
                      {{ getCategoryName(element.category) }}
                    </el-tag>
                  </div>
                  <div class="node-body" v-if="Object.keys(element.config).length > 0">
                    <template v-if="element.type === 'goto'">
                      <div class="config-item">
                        <label>URL:</label>
                        <el-input 
                          v-model="element.config.url" 
                          size="small" 
                          placeholder="https://example.com"
                        />
                      </div>
                    </template>
                    <template v-else-if="element.type === 'click'">
                      <div class="config-item">
                        <label>选择器:</label>
                        <el-input 
                          v-model="element.config.selector" 
                          size="small" 
                          placeholder="#submit-btn"
                        />
                      </div>
                      <div class="config-item">
                        <el-checkbox v-model="element.config.byImage">
                          图像识别
                        </el-checkbox>
                      </div>
                      <template v-if="element.config.byImage">
                        <div class="config-item">
                          <label>模板图:</label>
                          <el-input 
                            v-model="element.config.templatePath" 
                            size="small" 
                            placeholder="button.png"
                          />
                        </div>
                      </template>
                    </template>
                    <template v-else-if="element.type === 'input'">
                      <div class="config-item">
                        <label>选择器:</label>
                        <el-input 
                          v-model="element.config.selector" 
                          size="small" 
                          placeholder="#search-input"
                        />
                      </div>
                      <div class="config-item">
                        <label>内容:</label>
                        <el-input 
                          v-model="element.config.value" 
                          size="small" 
                          placeholder="要输入的内容"
                        />
                      </div>
                    </template>
                    <template v-else-if="element.type === 'wait'">
                      <div class="config-item">
                        <label>等待(ms):</label>
                        <el-input-number 
                          v-model="element.config.timeout" 
                          :min="0" 
                          :max="60000"
                          size="small"
                        />
                      </div>
                    </template>
                    <template v-else-if="element.type === 'wait_element'">
                      <div class="config-item">
                        <label>选择器:</label>
                        <el-input 
                          v-model="element.config.selector" 
                          size="small" 
                          placeholder=".element"
                        />
                      </div>
                      <div class="config-item">
                        <el-select v-model="element.config.state" size="small" style="width: 100%">
                          <el-option label="出现" value="present" />
                          <el-option label="消失" value="hidden" />
                        </el-select>
                      </div>
                    </template>
                    <template v-else-if="element.type === 'scroll'">
                      <div class="config-item">
                        <el-select v-model="element.config.direction" size="small">
                          <el-option label="向下" value="down" />
                          <el-option label="向上" value="up" />
                          <el-option label="到顶部" value="top" />
                          <el-option label="到底部" value="bottom" />
                        </el-select>
                      </div>
                    </template>
                    <template v-else-if="element.type === 'screenshot'">
                      <div class="config-item">
                        <el-checkbox v-model="element.config.fullPage">
                          整页截图
                        </el-checkbox>
                      </div>
                    </template>
                    <template v-else-if="element.type === 'ocr'">
                      <div class="config-item">
                        <label>语言:</label>
                        <el-select 
                          v-model="element.config.languages" 
                          size="small" 
                          multiple
                          style="width: 100%"
                        >
                          <el-option label="简体中文" value="chi_sim" />
                          <el-option label="英文" value="eng" />
                          <el-option label="繁体中文" value="chi_tra" />
                        </el-select>
                      </div>
                    </template>
                    <template v-else-if="element.type === 'image_match'">
                      <div class="config-item">
                        <label>模板图:</label>
                        <el-input 
                          v-model="element.config.templatePath" 
                          size="small" 
                          placeholder="target.png"
                        />
                      </div>
                      <div class="config-item">
                        <label>相似度:</label>
                        <el-slider 
                          v-model="element.config.threshold" 
                          :min="0.5" 
                          :max="1" 
                          :step="0.05"
                          size="small"
                        />
                      </div>
                    </template>
                    <template v-else-if="element.type === 'keyboard'">
                      <div class="config-item">
                        <label>文本:</label>
                        <el-input 
                          v-model="element.config.text" 
                          size="small" 
                          placeholder="要输入的文本"
                        />
                      </div>
                      <div class="config-item">
                        <el-checkbox v-model="element.config.pressEnter">
                          按回车键
                        </el-checkbox>
                      </div>
                    </template>
                    <template v-else-if="element.type === 'js'">
                      <div class="config-item">
                        <el-input 
                          v-model="element.config.code" 
                          type="textarea"
                          :rows="3"
                          size="small" 
                          placeholder="JavaScript 代码"
                        />
                      </div>
                    </template>
                    <template v-else-if="['new_tab', 'switch_tab'].includes(element.type)">
                      <div class="config-item">
                        <label>URL:</label>
                        <el-input 
                          v-model="element.config.url" 
                          size="small" 
                          placeholder="https://example.com"
                        />
                      </div>
                    </template>
                    <template v-else-if="element.type === 'loop'">
                      <div class="config-item">
                        <el-select v-model="element.config.type" size="small" style="width: 100%">
                          <el-option label="固定次数" value="times" />
                          <el-option label="元素列表" value="selector" />
                        </el-select>
                      </div>
                      <div class="config-item" v-if="element.config.type === 'times'">
                        <label>次数:</label>
                        <el-input-number 
                          v-model="element.config.times" 
                          :min="1" 
                          :max="1000"
                          size="small"
                        />
                      </div>
                    </template>
                    <template v-else-if="element.type === 'switch_frame'">
                      <div class="config-item">
                        <label>框架选择器:</label>
                        <el-input 
                          v-model="element.config.selector" 
                          size="small" 
                          placeholder="iframe"
                        />
                      </div>
                    </template>
                    <template v-else-if="['download', 'upload', 'hover', 'drag'].includes(element.type)">
                      <div class="config-item">
                        <label>选择器:</label>
                        <el-input 
                          v-model="element.config.selector" 
                          size="small" 
                          placeholder="#element"
                        />
                      </div>
                    </template>
                  </div>
                  <div class="node-footer">
                    <el-button 
                      size="small" 
                      type="danger" 
                      circle
                      @click.stop="removeNode(element.id)"
                    >
                      <el-icon><Delete /></el-icon>
                    </el-button>
                  </div>
                  <div class="node-connector" v-if="index < currentWorkflow.length - 1">
                    <el-icon size="20"><Bottom /></el-icon>
                  </div>
                </div>
              </template>
            </draggable>
          </div>
        </el-card>
      </el-col>
      
      <el-col :span="6" class="property-panel">
        <el-card shadow="never">
          <template #header>
            <span>节点配置</span>
          </template>
          <div v-if="selectedNode" class="property-content">
            <el-form label-position="top" size="small">
              <el-form-item label="节点ID">
                <el-input :value="selectedNode.id" disabled />
              </el-form-item>
              <el-form-item label="节点类型">
                <el-tag>{{ selectedNode.type }}</el-tag>
              </el-form-item>
              <el-form-item label="描述">
                <el-input 
                  v-model="selectedNode.description" 
                  type="textarea" 
                  :rows="2"
                />
              </el-form-item>
            </el-form>
          </div>
          <el-empty v-else description="请选择节点" />
        </el-card>
        
        <el-card shadow="never" class="preview-card">
          <template #header>
            <span>预览</span>
          </template>
          <el-tree
            :data="workflowTreeData"
            :props="{ label: 'label', children: 'children' }"
            default-expand-all
            expand-on-click-node
          >
            <template #default="{ node, data }">
              <span class="tree-node">
                <el-icon size="14"><component :is="data.icon" /></el-icon>
                <span>{{ node.label }}</span>
              </span>
            </template>
          </el-tree>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import draggable from 'vuedraggable'
import { 
  DocumentChecked, VideoPlay, Delete, Bottom, Plus,
  Operation
} from '@element-plus/icons-vue'
import { useWorkflowStore, type ActionNode } from '@/stores/workflow'

const store = useWorkflowStore()

const currentWorkflow = computed(() => store.currentWorkflow)
const selectedNodeId = computed(() => store.selectedNodeId)
const nodesByCategory = computed(() => store.nodesByCategory)

const selectedNode = computed(() => 
  currentWorkflow.value.find(n => n.id === selectedNodeId.value)
)

const expandedCategories = ref(['browser', 'interaction', 'extraction', 'ai', 'control', 'file'])

const workflowTreeData = computed(() => [
  {
    label: '工作流',
    icon: 'Operation',
    children: currentWorkflow.value.map(node => ({
      id: node.id,
      label: node.label,
      icon: node.icon,
      type: node.type
    }))
  }
])

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

function getNodeTagType(category: string): string {
  const types: Record<string, string> = {
    browser: 'primary',
    interaction: 'warning',
    extraction: 'success',
    ai: 'danger',
    control: 'info',
    file: ''
  }
  return types[category] || ''
}

function cloneNode(node: ActionNode): ActionNode {
  return {
    ...node,
    id: `${node.type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
  }
}

function onCanvasDrop(event: DragEvent) {
  console.log('Dropped on canvas:', event)
}

function selectNode(nodeId: string) {
  store.selectedNodeId = nodeId
}

function removeNode(nodeId: string) {
  store.removeNodeFromWorkflow(nodeId)
}

function onWorkflowChange(evt: any) {
  console.log('Workflow changed:', evt)
}

async function saveWorkflow() {
  try {
    await ElMessageBox.confirm('确定要保存当前工作流吗？', '确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
    
    const workflowData = JSON.stringify(currentWorkflow.value, null, 2)
    console.log('Saved workflow:', workflowData)
    ElMessage.success('工作流已保存')
  } catch {
    ElMessage.info('取消保存')
  }
}

async function runWorkflow() {
  if (currentWorkflow.value.length === 0) {
    ElMessage.warning('请先添加节点到工作流')
    return
  }
  
  try {
    await ElMessageBox.confirm('确定要运行当前工作流吗？', '确认', {
      confirmButtonText: '确定',
      cancelButtonText: '取消'
    })
    
    ElMessage.info('正在提交任务，请稍候...')
    console.log('Running workflow:', currentWorkflow.value)
    ElMessage.success('任务已提交，请前往任务管理查看进度')
  } catch {
    ElMessage.info('取消运行')
  }
}

function clearWorkflow() {
  try {
    ElMessageBox.confirm('确定要清空当前工作流吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }).then(() => {
      store.clearWorkflow()
      ElMessage.success('工作流已清空')
    })
  } catch {
    ElMessage.info('取消清空')
  }
}
</script>

<style scoped lang="scss">
.workflow-designer {
  height: 100%;
  display: flex;
  flex-direction: column;
  
  .header {
    margin-bottom: 20px;
    
    h2 {
      margin: 0;
      font-size: 20px;
      color: #303133;
    }
    
    .actions {
      text-align: right;
    }
  }
  
  .content {
    flex: 1;
  }
  
  .component-panel {
    :deep(.el-card__body) {
      max-height: calc(100vh - 200px);
      overflow-y: auto;
    }
    
    .component-list {
      display: flex;
      flex-direction: column;
      gap: 6px;
    }
    
    .component-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
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
      font-size: 14px;
      font-weight: 500;
    }
    
    :deep(.el-collapse-item__content) {
      padding-bottom: 10px;
    }
  }
  
  .canvas-panel {
    .canvas-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      
      .node-count {
        font-size: 12px;
        color: #909399;
      }
    }
    
    .workflow-canvas {
      min-height: 500px;
      padding: 20px;
      background: #fafafa;
      border: 2px dashed #dcdfe6;
      border-radius: 4px;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0;
    }
    
    .workflow-list {
      width: 100%;
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0;
    }
    
    .workflow-node {
      width: 340px;
      background: white;
      border: 1px solid #dcdfe6;
      border-radius: 8px;
      box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
      margin-bottom: 0;
      position: relative;
      transition: all 0.2s;
      
      &:hover {
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
      }
      
      &.selected {
        border-color: #409eff;
        box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.3);
      }
      
      .node-header {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 10px 14px;
        border-bottom: 1px solid #ebeef5;
        font-weight: 500;
        cursor: move;
      }
      
      .node-body {
        padding: 10px 14px;
        
        .config-item {
          margin-bottom: 8px;
          
          label {
            display: block;
            font-size: 12px;
            color: #909399;
            margin-bottom: 4px;
          }
        }
      }
      
      .node-footer {
        padding: 8px 14px;
        border-top: 1px solid #ebeef5;
        text-align: right;
      }
      
      .node-connector {
        position: absolute;
        bottom: -24px;
        left: 50%;
        transform: translateX(-50%);
        color: #409eff;
        z-index: 1;
      }
    }
    
    .ghost {
      opacity: 0.5;
      background: #ecf5ff;
    }
  }
  
  .property-panel {
    .property-content {
      padding: 10px 0;
    }
    
    .preview-card {
      margin-top: 20px;
    }
  }
  
  .tree-node {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
  }
}
</style>
