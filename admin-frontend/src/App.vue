<template>
  <el-config-provider :locale="locale">
    <el-container class="app-container">
      <el-aside width="200px" class="sidebar">
        <div class="logo">
          <el-icon size="24"><Monitor /></el-icon>
          <span>智能爬虫</span>
        </div>
        <el-menu
          :default-active="activeMenu"
          router
          class="sidebar-menu"
        >
          <el-menu-item index="/workflow">
            <el-icon><Operation /></el-icon>
            <span>工作流设计</span>
          </el-menu-item>
          <el-menu-item index="/tasks">
            <el-icon><List /></el-icon>
            <span>任务管理</span>
          </el-menu-item>
          <el-menu-item index="/templates">
            <el-icon><Document /></el-icon>
            <span>爬虫模板</span>
          </el-menu-item>
          <el-menu-item index="/data">
            <el-icon><DataLine /></el-icon>
            <span>数据预览</span>
          </el-menu-item>
          <el-menu-item index="/settings">
            <el-icon><Setting /></el-icon>
            <span>系统配置</span>
          </el-menu-item>
        </el-menu>
      </el-aside>
      
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-config-provider>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { Monitor, Operation, List, Document, DataLine, Setting } from '@element-plus/icons-vue'
import zhCn from 'element-plus/es/locale/lang/zh-cn'

const locale = zhCn
const route = useRoute()

const activeMenu = computed(() => route.path)
</script>

<style scoped>
.app-container {
  height: 100vh;
}

.sidebar {
  background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
  color: white;
}

.logo {
  height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  font-size: 18px;
  font-weight: bold;
  border-bottom: 1px solid rgba(255,255,255,0.1);
}

.sidebar-menu {
  border-right: none;
  background: transparent;
}

.sidebar-menu .el-menu-item {
  color: rgba(255,255,255,0.7);
}

.sidebar-menu .el-menu-item:hover {
  background: rgba(255,255,255,0.1);
}

.sidebar-menu .el-menu-item.is-active {
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
}

.main-content {
  background: #f5f7fa;
  padding: 20px;
}
</style>
