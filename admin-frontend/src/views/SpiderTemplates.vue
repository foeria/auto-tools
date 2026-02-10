<template>
  <div class="spider-templates">
    <el-row :gutter="20" class="header">
      <el-col :span="12">
        <h2>爬虫模板管理</h2>
      </el-col>
      <el-col :span="12" class="actions">
        <el-button type="primary" @click="showCreateDialog">
          <el-icon><Plus /></el-icon>
          新建模板
        </el-button>
        <el-button @click="refreshTemplates">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
      </el-col>
    </el-row>
    
    <el-card shadow="never">
      <el-table
        :data="templates"
        style="width: 100%"
        row-key="id"
        :tree-props="{ children: 'children' }"
        default-expand-all
      >
        <el-table-column prop="name" label="模板名称" min-width="180">
          <template #default="{ row }">
            <div class="template-name">
              <el-icon size="18"><Document /></el-icon>
              <span>{{ row.name }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="description" label="描述" min-width="200" />
        <el-table-column prop="url_pattern" label="URL模式" width="180" />
        <el-table-column prop="action_count" label="操作数" width="80" align="center" />
        <el-table-column prop="created_at" label="创建时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" align="center">
          <template #default="{ row }">
            <el-button-group>
              <el-tooltip content="编辑" placement="top">
                <el-button size="small" @click="editTemplate(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="复制" placement="top">
                <el-button size="small" @click="copyTemplate(row)">
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="使用模板创建任务" placement="top">
                <el-button size="small" type="success" @click="useTemplate(row)">
                  <el-icon><VideoPlay /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
                <el-button size="small" type="danger" @click="deleteTemplate(row.id)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-tooltip>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <el-dialog
      v-model="dialogVisible"
      :title="isEdit ? '编辑模板' : '新建模板'"
      width="700px"
      destroy-on-close
    >
      <el-form :model="currentTemplate" label-position="top">
        <el-form-item label="模板名称" required>
          <el-input v-model="currentTemplate.name" placeholder="请输入模板名称" />
        </el-form-item>
        <el-form-item label="描述">
          <el-input 
            v-model="currentTemplate.description" 
            type="textarea" 
            :rows="2"
            placeholder="请输入模板描述"
          />
        </el-form-item>
        <el-form-item label="URL模式">
          <el-input v-model="currentTemplate.url_pattern" placeholder="https://*.example.com/*" />
        </el-form-item>
        
        <el-divider content-position="left">操作步骤</el-divider>
        
        <div class="actions-editor">
          <div 
            v-for="(action, index) in currentTemplate.actions" 
            :key="index"
            class="action-item"
          >
            <el-tag :type="getActionTagType(action.type)" size="small">
              {{ getActionLabel(action.type) }}
            </el-tag>
            <el-input 
              v-if="action.type === 'goto'"
              v-model="action.url" 
              placeholder="URL地址"
              style="width: 200px"
              size="small"
            />
            <el-input 
              v-if="action.type === 'click'"
              v-model="action.selector" 
              placeholder="CSS选择器"
              style="width: 150px"
              size="small"
            />
            <el-input 
              v-if="action.type === 'input'"
              v-model="action.value" 
              placeholder="输入内容"
              style="width: 150px"
              size="small"
            />
            <el-input-number 
              v-if="action.type === 'wait'"
              v-model="action.timeout" 
              :min="0"
              :max="60000"
              size="small"
              style="width: 100px"
            />
            <el-button 
              size="small" 
              type="danger" 
              circle
              @click="removeAction(index)"
            >
              <el-icon><Delete /></el-icon>
            </el-button>
          </div>
          
          <el-dropdown @command="(cmd: string) => addAction(cmd)">
            <el-button size="small">
              添加操作 <el-icon class="el-icon--right"><ArrowDown /></el-icon>
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="goto">访问页面</el-dropdown-item>
                <el-dropdown-item command="click">点击元素</el-dropdown-item>
                <el-dropdown-item command="input">输入内容</el-dropdown-item>
                <el-dropdown-item command="wait">等待</el-dropdown-item>
                <el-dropdown-item command="screenshot">截图</el-dropdown-item>
                <el-dropdown-item command="extract">提取数据</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveTemplate">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, Edit, CopyDocument, VideoPlay, Delete, ArrowDown, Document } from '@element-plus/icons-vue'

interface TemplateAction {
  type: string
  [key: string]: any
}

interface Template {
  id: string
  name: string
  description: string
  url_pattern: string
  actions: TemplateAction[]
  action_count?: number
  created_at: string
}

const router = useRouter()
const templates = ref<Template[]>([])
const dialogVisible = ref(false)
const isEdit = ref(false)
const currentTemplate = reactive<Template>({
  id: '',
  name: '',
  description: '',
  url_pattern: '',
  actions: [],
  created_at: new Date().toISOString()
})

function generateMockTemplates(): Template[] {
  return [
    {
      id: 'tpl-001',
      name: '通用搜索流程',
      description: '适用于大多数网站的搜索功能自动化',
      url_pattern: 'https://*/search*',
      actions: [
        { type: 'goto', url: '' },
        { type: 'input', selector: '#search-input', value: '' },
        { type: 'click', selector: '#search-btn' },
        { type: 'wait', timeout: 2000 },
        { type: 'extract', selectors: ['.result-item'] }
      ],
      action_count: 5,
      created_at: new Date(Date.now() - 86400000).toISOString()
    },
    {
      id: 'tpl-002',
      name: '登录流程',
      description: '模拟用户登录操作的标准化流程',
      url_pattern: 'https://*/login*',
      actions: [
        { type: 'goto', url: '' },
        { type: 'input', selector: '#username', value: '' },
        { type: 'input', selector: '#password', value: '' },
        { type: 'click', selector: '#login-btn' },
        { type: 'wait', timeout: 3000 }
      ],
      action_count: 5,
      created_at: new Date(Date.now() - 172800000).toISOString()
    },
    {
      id: 'tpl-003',
      name: '表单提交',
      description: '通用表单填写和提交流程',
      url_pattern: 'https://*/form*',
      actions: [
        { type: 'goto', url: '' },
        { type: 'input', selector: '.form-field', value: '' },
        { type: 'click', selector: '#submit' },
        { type: 'wait', timeout: 5000 }
      ],
      action_count: 4,
      created_at: new Date(Date.now() - 259200000).toISOString()
    }
  ]
}

function fetchTemplates() {
  templates.value = generateMockTemplates()
}

function refreshTemplates() {
  fetchTemplates()
  ElMessage.success('已刷新')
}

function showCreateDialog() {
  isEdit.value = false
  Object.assign(currentTemplate, {
    id: `tpl-${Date.now()}`,
    name: '',
    description: '',
    url_pattern: '',
    actions: []
  })
  dialogVisible.value = true
}

function editTemplate(template: Template) {
  isEdit.value = true
  Object.assign(currentTemplate, JSON.parse(JSON.stringify(template)))
  dialogVisible.value = true
}

function copyTemplate(template: Template) {
  const copy = JSON.parse(JSON.stringify(template))
  copy.id = `tpl-${Date.now()}`
  copy.name = `${copy.name} (副本)`
  templates.value.unshift(copy)
  ElMessage.success('模板已复制')
}

function useTemplate(template: Template) {
  router.push({ 
    path: '/workflow', 
    query: { templateId: template.id } 
  })
}

async function deleteTemplate(templateId: string) {
  try {
    await ElMessageBox.confirm('确定要删除该模板吗？', '警告', {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    })
    templates.value = templates.value.filter(t => t.id !== templateId)
    ElMessage.success('模板已删除')
  } catch {
    ElMessage.info('取消删除')
  }
}

function addAction(type: string) {
  const action: TemplateAction = { type }
  switch (type) {
    case 'goto':
      action.url = ''
      break
    case 'click':
      action.selector = ''
      break
    case 'input':
      action.selector = ''
      action.value = ''
      break
    case 'wait':
      action.timeout = 1000
      break
    case 'screenshot':
      action.path = ''
      break
    case 'extract':
      action.selectors = []
      break
  }
  currentTemplate.actions.push(action)
}

function removeAction(index: number) {
  currentTemplate.actions.splice(index, 1)
}

function saveTemplate() {
  if (!currentTemplate.name) {
    ElMessage.warning('请输入模板名称')
    return
  }
  
  if (isEdit.value) {
    const index = templates.value.findIndex(t => t.id === currentTemplate.id)
    if (index > -1) {
      templates.value[index] = { ...currentTemplate }
    }
  } else {
    templates.value.unshift({ ...currentTemplate })
  }
  
  dialogVisible.value = false
  ElMessage.success(isEdit.value ? '模板已更新' : '模板已创建')
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN')
}

function getActionTagType(type: string): string {
  const typeMap: Record<string, string> = {
    goto: 'primary',
    click: 'warning',
    input: 'info',
    wait: '',
    screenshot: 'success',
    extract: 'danger'
  }
  return typeMap[type] || ''
}

function getActionLabel(type: string): string {
  const labelMap: Record<string, string> = {
    goto: '访问',
    click: '点击',
    input: '输入',
    wait: '等待',
    screenshot: '截图',
    extract: '提取'
  }
  return labelMap[type] || type
}

onMounted(() => {
  fetchTemplates()
})
</script>

<style scoped lang="scss">
.spider-templates {
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
  
  .template-name {
    display: flex;
    align-items: center;
    gap: 8px;
  }
  
  .actions-editor {
    .action-item {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      margin-bottom: 8px;
      background: #f5f7fa;
      border-radius: 4px;
    }
  }
}
</style>
