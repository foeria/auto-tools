<template>
  <div class="system-settings">
    <el-row :gutter="20" class="header">
      <el-col :span="12">
        <h2>系统配置</h2>
      </el-col>
      <el-col :span="12" class="actions">
        <el-button type="primary" @click="saveSettings">
          <el-icon><DocumentChecked /></el-icon>
          保存配置
        </el-button>
        <el-button @click="resetSettings">
          <el-icon><Refresh /></el-icon>
          重置
        </el-button>
      </el-col>
    </el-row>
    
    <el-row :gutter="20">
      <el-col :span="16">
        <el-card shadow="never" class="config-card">
          <template #header>
            <span><el-icon><Setting /></el-icon> 爬虫配置</span>
          </template>
          <el-form :model="settings.crawler" label-position="top">
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="最大重试次数">
                  <el-input-number 
                    v-model="settings.crawler.max_retry" 
                    :min="0" 
                    :max="10"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="请求超时(秒)">
                  <el-input-number 
                    v-model="settings.crawler.timeout" 
                    :min="5" 
                    :max="300"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            <el-row :gutter="20">
              <el-col :span="12">
                <el-form-item label="下载延迟(秒)">
                  <el-input-number 
                    v-model="settings.crawler.download_delay" 
                    :min="0" 
                    :max="60"
                    :step="0.1"
                  />
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="并发请求数">
                  <el-input-number 
                    v-model="settings.crawler.concurrent_requests" 
                    :min="1" 
                    :max="16"
                  />
                </el-form-item>
              </el-col>
            </el-row>
            <el-form-item label="User-Agent">
              <el-input 
                v-model="settings.crawler.user_agent" 
                placeholder="Mozilla/5.0..."
              />
            </el-form-item>
          </el-form>
        </el-card>
        
        <el-card shadow="never" class="config-card">
          <template #header>
            <span><el-icon><Picture /></el-icon> 图像识别配置</span>
          </template>
          <el-form :model="settings.image" label-position="top">
            <el-form-item label="模板匹配阈值 (0.0-1.0)">
              <el-slider 
                v-model="settings.image.match_threshold" 
                :min="0.5" 
                :max="1.0" 
                :step="0.01"
                :format-tooltip="(val: number) => `${(val * 100).toFixed(0)}%`"
              />
            </el-form-item>
            <el-form-item label="截图保存目录">
              <el-input 
                v-model="settings.image.screenshot_dir" 
                placeholder="./screenshots"
              />
            </el-form-item>
          </el-form>
        </el-card>
        
        <el-card shadow="never" class="config-card">
          <template #header>
            <span><el-icon><Link /></el-icon> API配置</span>
          </template>
          <el-form :model="settings.api" label-position="top">
            <el-form-item label="API基础URL">
              <el-input 
                v-model="settings.api.base_url" 
                placeholder="http://localhost:8000"
              />
            </el-form-item>
            <el-form-item label="数据转发目标URL">
              <el-input 
                v-model="settings.api.forward_url" 
                placeholder="https://target-api.com/data"
              />
            </el-form-item>
            <el-form-item label="启用认证">
              <el-switch v-model="settings.api.auth_enabled" />
            </el-form-item>
            <el-form-item label="API密钥" v-if="settings.api.auth_enabled">
              <el-input 
                v-model="settings.api.api_key" 
                type="password"
                show-password
                placeholder="请输入API密钥"
              />
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
      
      <el-col :span="8">
        <el-card shadow="never" class="config-card">
          <template #header>
            <span><el-icon><Monitor /></el-icon> 服务状态</span>
          </template>
          <el-descriptions :column="1" border>
            <el-descriptions-item label="API服务">
              <el-tag type="success" size="small">运行中</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="爬虫服务">
              <el-tag type="success" size="small">运行中</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="Redis">
              <el-tag type="success" size="small">已连接</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="MongoDB">
              <el-tag type="success" size="small">已连接</el-tag>
            </el-descriptions-item>
          </el-descriptions>
        </el-card>
        
        <el-card shadow="never" class="config-card">
          <template #header>
            <span><el-icon><Bell /></el-icon> 通知设置</span>
          </template>
          <el-form :model="settings.notification" label-position="top">
            <el-form-item label="任务完成通知">
              <el-switch v-model="settings.notification.task_complete" />
            </el-form-item>
            <el-form-item label="错误告警">
              <el-switch v-model="settings.notification.error_alert" />
            </el-form-item>
            <el-form-item label="邮件通知">
              <el-switch v-model="settings.notification.email_enabled" />
            </el-form-item>
            <el-form-item label="通知邮箱" v-if="settings.notification.email_enabled">
              <el-input 
                v-model="settings.notification.email" 
                placeholder="your@email.com"
              />
            </el-form-item>
          </el-form>
        </el-card>
        
        <el-card shadow="never" class="config-card">
          <template #header>
            <span><el-icon><InfoFilled /></el-icon> 系统信息</span>
          </template>
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="版本">v1.0.0</el-descriptions-item>
            <el-descriptions-item label="运行时间">5天 12小时</el-descriptions-item>
            <el-descriptions-item label="已采集数据">1,234条</el-descriptions-item>
            <el-descriptions-item label="完成任务">56个</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'
import { ElMessage } from 'element-plus'
import { 
  DocumentChecked, Refresh, Setting, Picture, Link,
  Monitor, Bell, InfoFilled
} from '@element-plus/icons-vue'

const settings = reactive({
  crawler: {
    max_retry: 3,
    timeout: 60,
    download_delay: 1.0,
    concurrent_requests: 4,
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
  },
  image: {
    match_threshold: 0.8,
    screenshot_dir: './screenshots'
  },
  api: {
    base_url: 'http://localhost:8000',
    forward_url: '',
    auth_enabled: false,
    api_key: ''
  },
  notification: {
    task_complete: true,
    error_alert: true,
    email_enabled: false,
    email: ''
  }
})

function saveSettings() {
  localStorage.setItem('crawler-settings', JSON.stringify(settings))
  ElMessage.success('配置已保存')
}

function resetSettings() {
  Object.assign(settings, {
    crawler: {
      max_retry: 3,
      timeout: 60,
      download_delay: 1.0,
      concurrent_requests: 4,
      user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    },
    image: {
      match_threshold: 0.8,
      screenshot_dir: './screenshots'
    },
    api: {
      base_url: 'http://localhost:8000',
      forward_url: '',
      auth_enabled: false,
      api_key: ''
    },
    notification: {
      task_complete: true,
      error_alert: true,
      email_enabled: false,
      email: ''
    }
  })
  ElMessage.success('配置已重置')
}
</script>

<style scoped lang="scss">
.system-settings {
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
  
  .config-card {
    margin-bottom: 20px;
  }
}
</style>
