<script setup lang="ts">
import { computed } from 'vue'
import { Handle, Position, type NodeProps } from '@vue-flow/core'

const props = defineProps<NodeProps>()

const nodeData = computed(() => props.data)

const tagType = computed(() => {
  const category = nodeData.value.category
  const types: Record<string, string> = {
    browser: 'primary',
    interaction: 'warning',
    extraction: 'success',
    ai: 'danger',
    control: 'info',
    file: ''
  }
  return types[category] || ''
})

const getCategoryName = (category: string): string => {
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
</script>

<template>
  <div class="workflow-node" :class="{ 'selected': props.selected }">
    <Handle type="target" :position="Position.Top" class="handle" :connectable="true" />
    
    <div class="node-header">
      <el-icon size="14"><component :is="nodeData.icon" /></el-icon>
      <span class="node-label">{{ nodeData.label }}</span>
      <el-tag size="small" :type="tagType" effect="plain">
        {{ getCategoryName(nodeData.category) }}
      </el-tag>
    </div>
    
    <div class="node-body" v-if="nodeData.config && Object.keys(nodeData.config).length > 0">
      <template v-if="nodeData.type === 'goto'">
        <div class="config-preview">
          <span class="config-key">URL:</span>
          <span class="config-value">{{ nodeData.config.url || '未设置' }}</span>
        </div>
      </template>
      <template v-else-if="nodeData.type === 'click'">
        <div class="config-preview">
          <span class="config-key">选择器:</span>
          <span class="config-value">{{ nodeData.config.selector || '未设置' }}</span>
        </div>
      </template>
      <template v-else-if="nodeData.type === 'input'">
        <div class="config-preview">
          <span class="config-key">输入:</span>
          <span class="config-value">{{ nodeData.config.value || '未设置' }}</span>
        </div>
      </template>
      <template v-else-if="nodeData.type === 'wait'">
        <div class="config-preview">
          <span class="config-key">等待:</span>
          <span class="config-value">{{ nodeData.config.timeout }}ms</span>
        </div>
      </template>
      <template v-else-if="nodeData.type === 'loop'">
        <div class="config-preview">
          <span class="config-key">循环:</span>
          <span class="config-value">{{ nodeData.config.type === 'times' ? `${nodeData.config.times}次` : '元素' }}</span>
        </div>
      </template>
      <template v-else-if="nodeData.type === 'condition'">
        <div class="config-preview">
          <span class="config-value">条件判断</span>
        </div>
      </template>
      <template v-else>
        <div class="config-preview">
          <span class="config-value">{{ nodeData.description || '无描述' }}</span>
        </div>
      </template>
    </div>
    
    <Handle type="source" :position="Position.Bottom" class="handle" :connectable="true" />
  </div>
</template>

<style scoped lang="scss">
.workflow-node {
  min-width: 160px;
  max-width: 220px;
  background: white;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
  padding: 0;
  transition: all 0.2s;
  
  &:hover {
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.15);
  }
  
  &.selected {
    border-color: #409eff;
    box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.3);
  }
  
  .handle {
    width: 12px;
    height: 12px;
    background: #409eff;
    border: 2px solid white;
    border-radius: 50%;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
    
    &:hover {
      background: #66b1ff;
    }
  }
  
  .node-header {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 8px 10px;
    border-bottom: 1px solid #ebeef5;
    background: #fafafa;
    border-radius: 8px 8px 0 0;
    
    .node-label {
      flex: 1;
      font-size: 12px;
      font-weight: 500;
      color: #303133;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }
  }
  
  .node-body {
    padding: 8px 10px;
    
    .config-preview {
      font-size: 11px;
      color: #606266;
      display: flex;
      gap: 4px;
      
      .config-key {
        color: #909399;
        flex-shrink: 0;
      }
      
      .config-value {
        color: #303133;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }
}
</style>
