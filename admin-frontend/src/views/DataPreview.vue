<template>
  <div class="data-preview">
    <el-row :gutter="20" class="header">
      <el-col :span="12">
        <h2>数据预览</h2>
      </el-col>
      <el-col :span="12" class="actions">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索数据..."
          style="width: 200px"
          clearable
        />
        <el-button @click="refreshData">
          <el-icon><Refresh /></el-icon>
          刷新
        </el-button>
        <el-button type="primary" @click="exportData">
          <el-icon><Download /></el-icon>
          导出
        </el-button>
      </el-col>
    </el-row>
    
    <el-card shadow="never">
      <el-table
        :data="filteredData"
        style="width: 100%"
        row-key="id"
        :tree-props="{ children: 'nested_data', hasChildren: 'hasChildren' }"
        default-expand-all
      >
        <el-table-column prop="task_id" label="任务ID" width="200" />
        <el-table-column prop="url" label="来源URL" min-width="200">
          <template #default="{ row }">
            <el-tooltip :content="row.url" placement="top">
              <span class="url-text">{{ row.url }}</span>
            </el-tooltip>
          </template>
        </el-table-column>
        <el-table-column label="数据结构" min-width="300">
          <template #default="{ row }">
            <el-button 
              size="small" 
              @click="viewDataStructure(row)"
            >
              查看数据
            </el-button>
          </template>
        </el-table-column>
        <el-table-column prop="extracted_at" label="提取时间" width="160">
          <template #default="{ row }">
            {{ formatDate(row.extracted_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="data_size" label="数据大小" width="100" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ formatSize(row.data_size) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="120" align="center">
          <template #default="{ row }">
            <el-button-group>
              <el-tooltip content="复制" placement="top">
                <el-button size="small" @click="copyData(row)">
                  <el-icon><CopyDocument /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="删除" placement="top">
                <el-button size="small" type="danger" @click="deleteData(row.id)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-tooltip>
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
    
    <el-dialog
      v-model="dataDialogVisible"
      :title="`数据详情 - ${currentData?.task_id}`"
      width="900px"
      destroy-on-close
    >
      <el-tabs v-model="activeTab" v-if="currentData">
        <el-tab-pane label="JSON视图" name="json">
          <el-input
            type="textarea"
            :rows="20"
            :model-value="JSON.stringify(currentData.data, null, 2)"
            readonly
            class="data-viewer"
          />
        </el-tab-pane>
        <el-tab-pane label="表格视图" name="table">
          <el-table :data="flattenData(currentData.data)" style="width: 100%">
            <el-table-column prop="key" label="字段" width="200" />
            <el-table-column prop="value" label="值" />
          </el-table>
        </el-tab-pane>
        <el-tab-pane label="原始数据" name="raw">
          <pre class="raw-data">{{ currentData }}</pre>
        </el-tab-pane>
      </el-tabs>
      <template #footer>
        <el-button @click="dataDialogVisible = false">关闭</el-button>
        <el-button type="primary" @click="copyCurrentData">
          <el-icon><CopyDocument /></el-icon>
          复制
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Download, CopyDocument, Delete } from '@element-plus/icons-vue'

interface DataRecord {
  id: string
  task_id: string
  url: string
  data: any
  extracted_at: string
  data_size: number
}

interface FlatItem {
  key: string
  value: any
}

const dataList = ref<DataRecord[]>([])
const searchKeyword = ref('')
const dataDialogVisible = ref(false)
const currentData = ref<DataRecord | null>(null)
const activeTab = ref('json')

function generateMockData(): DataRecord[] {
  return [
    {
      id: 'data-001',
      task_id: 'task-001',
      url: 'https://www.example.com',
      data: {
        title: '示例页面标题',
        description: '这是一个示例描述',
        items: [
          { name: '项目1', price: 100 },
          { name: '项目2', price: 200 }
        ],
        total: 2,
        metadata: {
          author: 'admin',
          date: '2024-01-01'
        }
      },
      extracted_at: new Date(Date.now() - 3600000).toISOString(),
      data_size: 1024
    },
    {
      id: 'data-002',
      task_id: 'task-002',
      url: 'https://www.example.org',
      data: {
        results: [
          { id: 1, title: '搜索结果1', url: 'https://link1.com' },
          { id: 2, title: '搜索结果2', url: 'https://link2.com' }
        ],
        count: 2
      },
      extracted_at: new Date(Date.now() - 7200000).toISOString(),
      data_size: 512
    },
    {
      id: 'data-003',
      task_id: 'task-003',
      url: 'https://www.example.net',
      data: {
        user: {
          id: 1001,
          username: 'test_user',
          profile: {
            avatar: 'https://avatar.com/1001.png',
            bio: '这是一个用户简介'
          }
        }
      },
      extracted_at: new Date(Date.now() - 10800000).toISOString(),
      data_size: 2048
    }
  ]
}

const filteredData = computed(() => {
  if (!searchKeyword.value) return dataList.value
  return dataList.value.filter(item => 
    item.task_id.includes(searchKeyword.value) ||
    item.url.includes(searchKeyword.value)
  )
})

function fetchData() {
  dataList.value = generateMockData()
}

function refreshData() {
  fetchData()
  ElMessage.success('已刷新')
}

function viewDataStructure(record: DataRecord) {
  currentData.value = record
  activeTab.value = 'json'
  dataDialogVisible.value = true
}

function flattenData(data: any, prefix = ''): FlatItem[] {
  const result: FlatItem[] = []
  
  if (typeof data !== 'object' || data === null) {
    result.push({ key: prefix, value: data })
    return result
  }
  
  for (const [key, value] of Object.entries(data)) {
    const newKey = prefix ? `${prefix}.${key}` : key
    if (typeof value === 'object' && value !== null && !Array.isArray(value)) {
      result.push(...flattenData(value, newKey))
    } else {
      result.push({ key: newKey, value: Array.isArray(value) ? JSON.stringify(value) : value })
    }
  }
  
  return result
}

function copyData(record: DataRecord) {
  navigator.clipboard.writeText(JSON.stringify(record.data, null, 2))
  ElMessage.success('数据已复制到剪贴板')
}

function copyCurrentData() {
  if (currentData.value) {
    navigator.clipboard.writeText(JSON.stringify(currentData.value.data, null, 2))
    ElMessage.success('数据已复制到剪贴板')
  }
}

function deleteData(dataId: string) {
  dataList.value = dataList.value.filter(d => d.id !== dataId)
  ElMessage.success('数据已删除')
}

function exportData() {
  const exportData = JSON.stringify(filteredData.value, null, 2)
  const blob = new Blob([exportData], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `crawler-data-${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('数据导出成功')
}

function formatDate(dateStr: string): string {
  return new Date(dateStr).toLocaleString('zh-CN')
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped lang="scss">
.data-preview {
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
  }
  
  .data-viewer {
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
  }
  
  .raw-data {
    background: #f5f7fa;
    padding: 16px;
    border-radius: 4px;
    overflow: auto;
    max-height: 500px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
  }
}
</style>
