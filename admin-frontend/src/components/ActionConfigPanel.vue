<template>
  <div class="action-config-panel">
    <el-card shadow="never" class="config-card">
      <template #header>
        <div class="card-header">
          <span><el-icon><Setting /></el-icon> {{ title }}</span>
          <el-button size="small" @click="resetConfig">重置</el-button>
        </div>
      </template>
      
      <el-form :model="config" label-position="top" size="small">
        <template v-if="actionType === 'goto'">
          <el-form-item label="目标URL" required>
            <el-input 
              v-model="config.url" 
              placeholder="https://example.com"
            >
              <template #prepend>URL</template>
            </el-input>
          </el-form-item>
          <el-form-item label="等待加载">
            <el-select v-model="config.wait_until" style="width: 100%">
              <el-option label="DOM加载完成" value="domcontentloaded" />
              <el-option label="网络空闲" value="networkidle" />
              <el-option label="所有资源加载" value="load" />
            </el-select>
          </el-form-item>
        </template>
        
        <template v-if="actionType === 'click'">
          <el-form-item label="选择器" required>
            <el-input 
              v-model="config.selector" 
              placeholder="#submit-btn, .clickable, button"
            />
            <div class="selector-tips">
              <el-link type="primary" @click="insertSelector('#id')">#id</el-link>
              <el-link type="primary" @click="insertSelector('.class')">.class</el-link>
              <el-link type="primary" @click="insertSelector('[name]')">[name]</el-link>
            </div>
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="config.by_image">使用图像识别点击</el-checkbox>
          </el-form-item>
          <template v-if="config.by_image">
            <el-form-item label="模板图片">
              <el-input 
                v-model="config.template_path" 
                placeholder="button.png"
              >
                <template #append>
                  <el-upload
                    action="#"
                    :auto-upload="false"
                    :show-file-list="false"
                    accept=".png,.jpg,.jpeg"
                  >
                    <el-icon><Upload /></el-icon>
                  </el-upload>
                </template>
              </el-input>
            </el-form-item>
          </template>
          <el-form-item label="超时时间(ms)">
            <el-input-number 
              v-model="config.timeout" 
              :min="0" 
              :max="60000"
              style="width: 100%"
            />
          </el-form-item>
        </template>
        
        <template v-if="actionType === 'input'">
          <el-form-item label="选择器" required>
            <el-input 
              v-model="config.selector" 
              placeholder="#input-id, input[name='keyword']"
            />
          </el-form-item>
          <el-form-item label="输入内容" required>
            <el-input 
              v-model="config.value" 
              type="textarea"
              :rows="2"
              placeholder="要输入的内容"
            />
          </el-form-item>
          <el-form-item>
            <el-checkbox v-model="config.clear">清空原有内容</el-checkbox>
            <el-checkbox v-model="config.press_enter" style="margin-left: 20px">按回车键</el-checkbox>
          </el-form-item>
        </template>
        
        <template v-if="actionType === 'wait'">
          <el-form-item label="等待类型">
            <el-radio-group v-model="config.wait_type">
              <el-radio label="selector">等待元素</el-radio>
              <el-radio label="timeout">等待时间</el-radio>
            </el-radio-group>
          </el-form-item>
          <template v-if="config.wait_type === 'selector'">
            <el-form-item label="元素选择器">
              <el-input 
                v-model="config.selector" 
                placeholder=".loaded-element"
              />
            </el-form-item>
            <el-form-item label="元素状态">
              <el-select v-model="config.state" style="width: 100%">
                <el-option label="可见" value="visible" />
                <el-option label="隐藏" value="hidden" />
                <el-option label="附加到DOM" value="attached" />
                <el-option label="从DOM移除" value="detached" />
              </el-select>
            </el-form-item>
          </template>
          <template v-else>
            <el-form-item label="等待时间(ms)">
              <el-input-number 
                v-model="config.timeout" 
                :min="0" 
                :max="60000"
                :step="100"
                style="width: 100%"
              />
            </el-form-item>
          </template>
        </template>
        
        <template v-if="actionType === 'extract'">
          <el-form-item label="选择器列表">
            <el-row 
              v-for="(selector, index) in config.selectors" 
              :key="index"
              :gutter="10"
              style="margin-bottom: 10px"
            >
              <el-col :span="20">
                <el-input 
                  v-model="config.selectors[index]" 
                  placeholder=".data-item"
                />
              </el-col>
              <el-col :span="4">
                <el-button 
                  type="danger" 
                  size="small"
                  @click="removeSelector(index)"
                >
                  <el-icon><Delete /></el-icon>
                </el-button>
              </el-col>
            </el-row>
            <el-button size="small" @click="addSelector">
              <el-icon><Plus /></el-icon> 添加选择器
            </el-button>
          </el-form-item>
          <el-form-item label="提取类型">
            <el-select v-model="config.extract_type" style="width: 100%">
              <el-option label="HTML内容" value="html" />
              <el-option label="纯文本" value="text" />
              <el-option label="属性值" value="attribute" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="config.extract_type === 'attribute'" label="属性名">
            <el-input 
              v-model="config.attribute" 
              placeholder="href, src, data-*"
            />
          </el-form-item>
        </template>
        
        <template v-if="actionType === 'screenshot'">
          <el-form-item>
            <el-checkbox v-model="config.full_page">截取整个页面</el-checkbox>
          </el-form-item>
          <el-form-item label="元素截图">
            <el-input 
              v-model="config.selector" 
              placeholder=".element-to-capture（留空则截取整个页面）"
            />
          </el-form-item>
          <el-form-item label="保存路径">
            <el-input 
              v-model="config.path" 
              placeholder="./screenshots/screenshot.png"
            />
          </el-form-item>
        </template>
        
        <template v-if="actionType === 'evaluate'">
          <el-form-item label="JavaScript代码" required>
            <el-input 
              v-model="config.script" 
              type="textarea"
              :rows="6"
              placeholder="() => { return document.title; }"
            />
          </el-form-item>
          <el-form-item label="参数">
            <el-input 
              v-model="scriptArg" 
              type="textarea"
              :rows="2"
              placeholder='{"key": "value"}'
              @blur="updateScriptArg"
            />
          </el-form-item>
        </template>
        
        <template v-if="actionType === 'scroll'">
          <el-form-item label="滚动类型">
            <el-radio-group v-model="config.scroll_type">
              <el-radio label="position">指定位置</el-radio>
              <el-radio label="element">滚动到元素</el-radio>
              <el-radio label="bottom">滚动到底部</el-radio>
              <el-radio label="top">滚动到顶部</el-radio>
            </el-radio-group>
          </el-form-item>
          <template v-if="config.scroll_type === 'position'">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="X偏移">
                  <el-input-number v-model="config.x" :min="0" style="width: 100%" />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="Y偏移">
                  <el-input-number v-model="config.y" :min="0" style="width: 100%" />
                </el-form-item>
              </el-col>
            </el-row>
          </template>
          <template v-if="config.scroll_type === 'element'">
            <el-form-item label="元素选择器">
              <el-input v-model="config.selector" placeholder=".load-more" />
            </el-form-item>
          </template>
        </template>
        
        <template v-if="actionType === 'press'">
          <el-form-item label="元素选择器">
            <el-input v-model="config.selector" placeholder="body（留空则全局）" />
          </el-form-item>
          <el-form-item label="按键" required>
            <el-select v-model="config.key" style="width: 100%">
              <el-option label="Enter" value="Enter" />
              <el-option label="Escape" value="Escape" />
              <el-option label="Tab" value="Tab" />
              <el-option label="Backspace" value="Backspace" />
              <el-option label="ArrowDown" value="ArrowDown" />
              <el-option label="ArrowUp" value="ArrowUp" />
              <el-option label="ArrowLeft" value="ArrowLeft" />
              <el-option label="ArrowRight" value="ArrowRight" />
            </el-select>
          </el-form-item>
        </template>
        
        <template v-if="actionType === 'hover'">
          <el-form-item label="元素选择器" required>
            <el-input v-model="config.selector" placeholder=".hover-element" />
          </el-form-item>
          <el-form-item label="超时时间(ms)">
            <el-input-number v-model="config.timeout" :min="0" :max="60000" style="width: 100%" />
          </el-form-item>
        </template>
        
        <template v-if="actionType === 'upload'">
          <el-form-item label="文件输入框选择器" required>
            <el-input v-model="config.selector" placeholder="input[type='file']" />
          </el-form-item>
          <el-form-item label="文件路径列表">
            <el-input 
              v-model="filePathsInput" 
              type="textarea"
              :rows="3"
              placeholder="/path/to/file1.png&#10;/path/to/file2.png"
              @blur="updateFilePaths"
            />
          </el-form-item>
        </template>
      </el-form>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, computed } from 'vue'
import { Setting, Delete, Plus, Upload } from '@element-plus/icons-vue'

const props = defineProps<{
  actionType: string
  modelValue: Record<string, any>
  title?: string
}>()

const emit = defineEmits<{
  (e: 'update:modelValue', value: Record<string, any>): void
}>()

const config = reactive<Record<string, any>>({
  url: '',
  selector: '',
  value: '',
  timeout: 5000,
  by_image: false,
  template_path: '',
  clear: true,
  press_enter: false,
  wait_type: 'timeout',
  state: 'visible',
  selectors: ['.data-item'],
  extract_type: 'html',
  attribute: '',
  full_page: false,
  path: '',
  script: '',
  scroll_type: 'position',
  x: 0,
  y: 500,
  key: 'Enter',
  wait_until: 'networkidle',
  file_paths: []
})

const scriptArg = ref('')
const filePathsInput = ref('')

watch(() => props.modelValue, (newVal) => {
  if (newVal) {
    Object.assign(config, newVal)
  }
}, { immediate: true })

watch(config, (newVal) => {
  emit('update:modelValue', newVal)
}, { deep: true })

function insertSelector(pattern: string) {
  config.selector += pattern
}

function addSelector() {
  config.selectors.push('')
}

function removeSelector(index: number) {
  config.selectors.splice(index, 1)
}

function updateScriptArg() {
  try {
    if (scriptArg.value) {
      config.arg = JSON.parse(scriptArg.value)
    }
  } catch (e) {
    console.error('Invalid JSON argument')
  }
}

function updateFilePaths() {
  if (filePathsInput.value) {
    config.file_paths = filePathsInput.value.split('\n').map(s => s.trim()).filter(Boolean)
  }
}

function resetConfig() {
  Object.assign(config, {
    url: '',
    selector: '',
    value: '',
    timeout: 5000,
    by_image: false,
    template_path: '',
    clear: true,
    press_enter: false,
    selectors: ['.data-item'],
    extract_type: 'html',
    attribute: '',
    full_page: false,
    path: '',
    script: '',
    key: 'Enter'
  })
}
</script>

<style scoped lang="scss">
.action-config-panel {
  height: 100%;
}

.config-card {
  height: 100%;
  
  :deep(.el-card__body) {
    height: calc(100% - 50px);
    overflow-y: auto;
  }
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.selector-tips {
  margin-top: 8px;
  display: flex;
  gap: 12px;
}
</style>
