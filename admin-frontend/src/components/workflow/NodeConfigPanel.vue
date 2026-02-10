<script setup lang="ts">
import { type PropType } from 'vue'
import { ElMessage } from 'element-plus'
import type { ActionNode } from '@/stores/workflow'

interface Condition {
  selector: string
  operator: 'exists' | 'not_exists' | 'equals' | 'not_equals' | 'contains' | 'not_contains' | 'greater' | 'less'
  value: string
}

const props = defineProps({
  node: {
    type: Object as PropType<ActionNode | null>,
    default: null
  }
})

const emit = defineEmits(['update:node', 'delete', 'duplicate'])

// @ts-expect-error - Used in template
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

// @ts-expect-error - Used in template
function copyNodeId() {
  if (props.node) {
    navigator.clipboard.writeText(props.node.id)
    ElMessage.success('节点ID已复制到剪贴板')
  }
}

// @ts-expect-error - Used in template
function addCondition() {
  if (props.node) {
    if (!props.node.config.conditions) {
      props.node.config.conditions = []
    }
    props.node.config.conditions.push({
      selector: '',
      operator: 'exists',
      value: ''
    } as Condition)
  }
}

// @ts-expect-error - Used in template
function removeCondition(index: number) {
  if (props.node && props.node.config.conditions) {
    props.node.config.conditions.splice(index, 1)
  }
}

// @ts-expect-error - Used in template
function addSelector() {
  if (props.node) {
    if (!props.node.config.selectors) {
      props.node.config.selectors = []
    }
    props.node.config.selectors.push({ name: '', selector: '', extractType: 'text', attribute: '' })
  }
}

// @ts-expect-error - Used in template
function removeSelector(index: number) {
  if (props.node && props.node.config.selectors) {
    props.node.config.selectors.splice(index, 1)
  }
}
</script>

<template>
  <div class="node-config-panel" v-if="node">
    <div class="panel-header">
      <span class="title">节点配置</span>
      <el-tag size="small">{{ node.type }}</el-tag>
    </div>
    
    <el-form label-position="top" size="small" class="config-form">
      <el-form-item label="节点ID">
        <div class="id-wrapper">
          <el-input :value="node.id" disabled />
          <el-button size="small" @click="copyNodeId">复制</el-button>
        </div>
      </el-form-item>
      
      <el-form-item label="类型">
        <el-tag>{{ getCategoryName(node.category) }}</el-tag>
      </el-form-item>
      
      <el-form-item label="描述">
        <el-input
          v-model="node.description"
          type="textarea"
          :rows="2"
          placeholder="节点描述"
        />
      </el-form-item>
      
      <template v-if="node.type === 'start'">
        <el-alert type="info" :closable="false" show-icon>
          开始节点，工作流入口，无需配置
        </el-alert>
      </template>
      
      <template v-else-if="node.type === 'end'">
        <el-alert type="info" :closable="false" show-icon>
          结束节点，工作流终点，无需配置
        </el-alert>
      </template>
      
      <template v-else-if="node.type === 'goto'">
        <el-form-item label="URL">
          <el-input v-model="node.config.url" placeholder="https://example.com" />
        </el-form-item>
        <el-form-item label="等待条件">
          <el-select v-model="node.config.waitUntil" style="width: 100%">
            <el-option label="DOM加载完成" value="domcontentloaded" />
            <el-option label="网络空闲" value="networkidle" />
            <el-option label="加载完成" value="load" />
          </el-select>
        </el-form-item>
        <el-form-item label="超时时间(ms)">
          <el-input-number v-model="node.config.timeout" :min="1000" :max="60000" style="width: 100%" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'click'">
        <el-form-item label="选择器">
          <el-input v-model="node.config.selector" placeholder="#submit-btn" />
        </el-form-item>
        <el-form-item label="点击方式">
          <el-select v-model="node.config.clickType" style="width: 100%">
            <el-option label="左键单击" value="left" />
            <el-option label="左键双击" value="double" />
            <el-option label="右键单击" value="right" />
          </el-select>
        </el-form-item>
        <el-form-item label="图像识别">
          <el-switch v-model="node.config.byImage" />
        </template>
        <template v-if="node.config.byImage">
          <el-form-item label="模板图">
            <el-input v-model="node.config.templatePath" placeholder="button.png" />
          </el-form-item>
        </template>
        <el-form-item label="偏移X">
          <el-input-number v-model="node.config.offsetX" :min="-1000" :max="1000" style="width: 100%" />
        </el-form-item>
        <el-form-item label="偏移Y">
          <el-input-number v-model="node.config.offsetY" :min="-1000" :max="1000" style="width: 100%" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'input'">
        <el-form-item label="选择器">
          <el-input v-model="node.config.selector" placeholder="#search-input" />
        </el-form-item>
        <el-form-item label="内容">
          <el-input v-model="node.config.value" placeholder="要输入的内容" />
        </el-form-item>
        <el-form-item label="清空原内容">
          <el-switch v-model="node.config.clear" />
        </el-form-item>
        <el-form-item label="输入后按回车">
          <el-switch v-model="node.config.pressEnter" />
        </el-form-item>
        <el-form-item label="模拟人机输入">
          <el-switch v-model="node.config.humanInput" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'wait'">
        <el-form-item label="等待时间(ms)">
          <el-input-number v-model="node.config.timeout" :min="0" :max="600000" style="width: 100%" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'wait_element'">
        <el-form-item label="选择器">
          <el-input v-model="node.config.selector" placeholder=".element" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="node.config.state">
            <el-option label="出现" value="present" />
            <el-option label="消失" value="hidden" />
          </el-select>
        </el-form-item>
        <el-form-item label="超时时间(ms)">
          <el-input-number v-model="node.config.timeout" :min="1000" :max="60000" style="width: 100%" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'scroll'">
        <el-form-item label="方向">
          <el-select v-model="node.config.direction">
            <el-option label="向下" value="down" />
            <el-option label="向上" value="up" />
            <el-option label="到顶部" value="top" />
            <el-option label="到底部" value="bottom" />
          </el-select>
        </el-form-item>
        <template v-if="node.config.direction === 'down' || node.config.direction === 'up'">
          <el-form-item label="滚动距离(px)">
            <el-input-number v-model="node.config.amount" :min="100" :max="5000" style="width: 100%" />
          </el-form-item>
        </template>
        <el-form-item label="选择器滚动">
          <el-input v-model="node.config.selector" placeholder="滚动到指定元素（可选）" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'screenshot'">
        <el-form-item label="截图类型">
          <el-select v-model="node.config.screenshotType" style="width: 100%">
            <el-option label="整页截图" value="fullpage" />
            <el-option label="可视区域" value="viewport" />
            <el-option label="指定元素" value="selector" />
          </el-select>
        </el-form-item>
        <template v-if="node.config.screenshotType === 'selector'">
          <el-form-item label="元素选择器">
            <el-input v-model="node.config.selector" placeholder="#element" />
          </el-form-item>
        </template>
        <el-form-item label="保存路径">
          <el-input v-model="node.config.savePath" placeholder="./screenshots/page.png" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'extract'">
        <el-form-item label="提取规则">
          <div class="selector-list">
            <div v-for="(sel, index) in node.config.selectors" :key="index" class="selector-item">
              <el-input v-model="sel.name" placeholder="字段名" style="width: 80px" />
              <el-input v-model="sel.selector" placeholder="CSS选择器" style="flex: 1" />
              <el-select v-model="sel.extractType" style="width: 90px">
                <el-option label="文本" value="text" />
                <el-option label="HTML" value="html" />
                <el-option label="属性" value="attribute" />
              </el-select>
              <el-input v-model="sel.attribute" placeholder="属性名" style="width: 80px" v-if="sel.extractType === 'attribute'" />
              <el-button type="danger" :icon="'Delete'" size="small" @click="removeSelector(index)" />
            </div>
            <el-button type="primary" size="small" @click="addSelector" style="width: 100%; margin-top: 8px">
              添加提取字段
            </el-button>
          </div>
        </el-form-item>
        <el-form-item label="输出格式">
          <el-select v-model="node.config.outputFormat" style="width: 100%">
            <el-option label="JSON" value="json" />
            <el-option label="CSV" value="csv" />
            <el-option label="Excel" value="xlsx" />
          </el-select>
        </el-form-item>
        <el-form-item label="保存路径">
          <el-input v-model="node.config.savePath" placeholder="./data/result.json" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'ocr'">
        <el-form-item label="图像路径">
          <el-input v-model="node.config.imagePath" placeholder="./screenshots/captcha.png" />
        </el-form-item>
        <el-form-item label="识别区域">
          <el-row :gutter="8">
            <el-col :span="6">
              <el-input-number v-model="node.config.regionX" :min="0" placeholder="X" style="width: 100%" />
            </el-col>
            <el-col :span="6">
              <el-input-number v-model="node.config.regionY" :min="0" placeholder="Y" style="width: 100%" />
            </el-col>
            <el-col :span="6">
              <el-input-number v-model="node.config.regionWidth" :min="0" placeholder="宽" style="width: 100%" />
            </el-col>
            <el-col :span="6">
              <el-input-number v-model="node.config.regionHeight" :min="0" placeholder="高" style="width: 100%" />
            </el-col>
          </el-input>
        </el-form-item>
        <el-form-item label="语言">
          <el-select v-model="node.config.languages" multiple style="width: 100%">
            <el-option label="简体中文" value="chi_sim" />
            <el-option label="英文" value="eng" />
            <el-option label="繁体中文" value="chi_tra" />
            <el-option label="日文" value="jpn" />
            <el-option label="韩文" value="kor" />
          </el-select>
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'image_match'">
        <el-form-item label="模板图路径">
          <el-input v-model="node.config.templatePath" placeholder="target.png" />
        </el-form-item>
        <el-form-item label="相似度阈值">
          <el-slider v-model="node.config.threshold" :min="0.5" :max="1" :step="0.05" :marks="{0.5: '50%', 0.8: '80%', 1: '100%'}" />
        </el-form-item>
        <el-form-item label="匹配成功后动作">
          <el-select v-model="node.config.action" style="width: 100%">
            <el-option label="点击" value="click" />
            <el-option label="悬停" value="hover" />
            <el-option label="返回坐标" value="return" />
          </el-select>
        </el-form-item>
        <el-form-item label="点击偏移X">
          <el-input-number v-model="node.config.offsetX" :min="-100" :max="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="点击偏移Y">
          <el-input-number v-model="node.config.offsetY" :min="-100" :max="100" style="width: 100%" />
        </el-form-item>
        <el-form-item label="超时时间(ms)">
          <el-input-number v-model="node.config.timeout" :min="1000" :max="30000" style="width: 100%" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'captcha'">
        <el-form-item label="验证码类型">
          <el-select v-model="node.config.captchaType" style="width: 100%">
            <el-option label="滑块验证码" value="slider" />
            <el-option label="点选验证码" value="click" />
            <el-option label="文字验证码" value="text" />
            <el-option label="图片验证码" value="image" />
          </el-select>
        </el-form-item>
        <el-form-item label="模板路径">
          <el-input v-model="node.config.templatePath" placeholder="captcha_template.png" />
        </el-form-item>
        <el-form-item label="使用打码平台">
          <el-switch v-model="node.config.useApi" />
        </el-form-item>
        <template v-if="node.config.useApi">
          <el-form-item label="API地址">
            <el-input v-model="node.config.apiUrl" placeholder="http://api.captcha.com/solve" />
          </el-form-item>
          <el-form-item label="API密钥">
            <el-input v-model="node.config.apiKey" placeholder="your-api-key" type="password" show-password />
          </el-form-item>
        </template>
      </template>
      
      <template v-else-if="node.type === 'hover'">
        <el-form-item label="选择器">
          <el-input v-model="node.config.selector" placeholder="#element" />
        </el-form-item>
        <el-form-item label="偏移X">
          <el-input-number v-model="node.config.offsetX" :min="-1000" :max="1000" style="width: 100%" />
        </el-form-item>
        <el-form-item label="偏移Y">
          <el-input-number v-model="node.config.offsetY" :min="-1000" :max="1000" style="width: 100%" />
        </el-form-item>
        <el-form-item label="悬停时长(ms)">
          <el-input-number v-model="node.config.duration" :min="0" :max="5000" style="width: 100%" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'drag'">
        <el-form-item label="源元素选择器">
          <el-input v-model="node.config.sourceSelector" placeholder="#draggable" />
        </el-form-item>
        <el-form-item label="目标元素选择器">
          <el-input v-model="node.config.targetSelector" placeholder="#droppable" />
        </el-form-item>
        <template v-if="!node.config.targetSelector">
          <el-form-item label="目标坐标">
            <el-row :gutter="8">
              <el-col :span="12">
                <el-input-number v-model="node.config.targetX" :min="0" placeholder="X" style="width: 100%" />
              </el-col>
              <el-col :span="12">
                <el-input-number v-model="node.config.targetY" :min="0" placeholder="Y" style="width: 100%" />
              </el-col>
            </el-input>
          </el-form-item>
        </template>
      </template>
      
      <template v-else-if="node.type === 'keyboard'">
        <el-form-item label="按键">
          <el-select v-model="node.config.keys" multiple filterable allow-create placeholder="选择按键" style="width: 100%">
            <el-option label="Enter" value="Enter" />
            <el-option label="Tab" value="Tab" />
            <el-option label="Escape" value="Escape" />
            <el-option label="Backspace" value="Backspace" />
            <el-option label="Delete" value="Delete" />
            <el-option label="ArrowUp" value="ArrowUp" />
            <el-option label="ArrowDown" value="ArrowDown" />
            <el-option label="ArrowLeft" value="ArrowLeft" />
            <el-option label="ArrowRight" value="ArrowRight" />
            <el-option label="Control" value="Control" />
            <el-option label="Alt" value="Alt" />
            <el-option label="Shift" value="Shift" />
          </el-select>
        </el-form-item>
        <el-form-item label="输入文本">
          <el-input v-model="node.config.text" placeholder="要输入的文本" />
        </el-form-item>
        <el-form-item label="快捷键组合">
          <el-input v-model="node.config.combo" placeholder="如: Control+Shift+K" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'js'">
        <el-form-item label="JavaScript 代码">
          <el-input
            v-model="node.config.code"
            type="textarea"
            :rows="6"
            placeholder="// JavaScript 代码
// 可使用 window, document 等对象
// 返回值将存储在 result 变量中"
          />
        </el-form-item>
        <el-form-item label="保存返回值">
          <el-switch v-model="node.config.returnValue" />
        </el-form-item>
        <el-form-item label="变量名">
          <el-input v-model="node.config.variableName" placeholder="result" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'condition'">
        <el-form-item label="条件组合逻辑">
          <el-radio-group v-model="node.config.logic">
            <el-radio label="and">且（全部满足）</el-radio>
            <el-radio label="or">或（任一满足）</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="条件列表">
          <div class="condition-list">
            <div v-for="(cond, index) in node.config.conditions" :key="index" class="condition-item">
              <el-input v-model="cond.selector" placeholder="选择器" style="flex: 2" />
              <el-select v-model="cond.operator" style="width: 110px">
                <el-option label="存在" value="exists" />
                <el-option label="不存在" value="not_exists" />
                <el-option label="等于" value="equals" />
                <el-option label="不等于" value="not_equals" />
                <el-option label="包含" value="contains" />
                <el-option label="不包含" value="not_contains" />
              </el-select>
              <el-input v-model="cond.value" placeholder="比较值" style="flex: 1" />
              <el-button type="danger" :icon="'Delete'" size="small" @click="removeCondition(index)" />
            </div>
            <el-button type="primary" size="small" @click="addCondition" style="width: 100%; margin-top: 8px">
              添加条件
            </el-button>
          </div>
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'loop'">
        <el-form-item label="循环类型">
          <el-select v-model="node.config.type" style="width: 100%">
            <el-option label="固定次数" value="times" />
            <el-option label="元素列表" value="selector" />
            <el-option label="无限循环" value="infinite" />
            <el-option label="条件循环" value="while" />
          </el-select>
        </el-form-item>
        <template v-if="node.config.type === 'times'">
          <el-form-item label="循环次数">
            <el-input-number v-model="node.config.times" :min="1" :max="10000" style="width: 100%" />
          </el-form-item>
        </template>
        <template v-if="node.config.type === 'selector'">
          <el-form-item label="元素选择器">
            <el-input v-model="node.config.selector" placeholder=".list-item" />
          </el-form-item>
          <el-form-item label="保存列表到变量">
            <el-input v-model="node.config.variableName" placeholder="items" />
          </el-form-item>
        </template>
        <template v-if="node.config.type === 'while'">
          <el-form-item label="循环条件">
            <el-input v-model="node.config.condition" placeholder="如: items.length > 0" />
          </el-form-item>
        </template>
        <el-form-item label="循环间隔(ms)">
          <el-input-number v-model="node.config.interval" :min="0" :max="10000" style="width: 100%" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'break'">
        <el-form-item label="中断类型">
          <el-select v-model="node.config.breakType" style="width: 100%">
            <el-option label="跳出循环" value="break" />
            <el-option label="跳出当前迭代" value="continue" />
          </el-select>
        </el-form-item>
        <el-form-item label="条件（可选）">
          <el-input v-model="node.config.condition" placeholder="满足条件时中断（可选）" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'new_tab'">
        <el-form-item label="URL">
          <el-input v-model="node.config.url" placeholder="https://example.com" />
        </el-form-item>
        <el-form-item label="打开后切换">
          <el-switch v-model="node.config.switchTo" />
        </el-form-item>
        <el-form-item label="等待加载完成">
          <el-switch v-model="node.config.waitLoad" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'switch_tab'">
        <el-form-item label="操作">
          <el-select v-model="node.config.action" style="width: 100%">
            <el-option label="切换到第一个" value="first" />
            <el-option label="切换到最后一个" value="last" />
            <el-option label="切换到下一个" value="next" />
            <el-option label="切换到上一个" value="prev" />
            <el-option label="切换到指定索引" value="index" />
            <el-option label="切换到指定URL" value="url" />
          </el-select>
        </el-form-item>
        <template v-if="node.config.action === 'index'">
          <el-form-item label="标签页索引">
            <el-input-number v-model="node.config.index" :min="0" style="width: 100%" />
          </el-form-item>
        </template>
        <template v-if="node.config.action === 'url'">
          <el-form-item label="URL包含">
            <el-input v-model="node.config.url" placeholder="example.com" />
          </el-form-item>
        </template>
      </template>
      
      <template v-else-if="node.type === 'close_tab'">
        <el-form-item label="操作">
          <el-select v-model="node.config.action" style="width: 100%">
            <el-option label="关闭当前标签页" value="current" />
            <el-option label="关闭第一个标签页" value="first" />
            <el-option label="关闭最后一个标签页" value="last" />
            <el-option label="关闭除当前外所有" value="others" />
          </el-select>
        </template>
      </template>
      
      <template v-else-if="node.type === 'switch_frame'">
        <el-form-item label="框架选择">
          <el-select v-model="node.config.action" style="width: 100%">
            <el-option label="主文档" value="main" />
            <el-option label="第一个iframe" value="first" />
            <el-option label="最后一个iframe" value="last" />
            <el-option label="指定选择器" value="selector" />
            <el-option label="退出到主文档" value="parent" />
          </el-select>
        </el-form-item>
        <template v-if="node.config.action === 'selector'">
          <el-form-item label="iframe选择器">
            <el-input v-model="node.config.selector" placeholder="iframe" />
          </el-form-item>
        </template>
      </template>
      
      <template v-else-if="node.type === 'download'">
        <el-form-item label="选择器">
          <el-input v-model="node.config.selector" placeholder="#download-btn" />
        </el-form-item>
        <el-form-item label="保存路径">
          <el-input v-model="node.config.savePath" placeholder="./downloads" />
        </el-form-item>
        <el-form-item label="文件名">
          <el-input v-model="node.config.fileName" placeholder="自动生成" />
        </el-form-item>
        <el-form-item label="等待下载完成">
          <el-switch v-model="node.config.waitComplete" />
        </el-form-item>
      </template>
      
      <template v-else-if="node.type === 'upload'">
        <el-form-item label="选择器">
          <el-input v-model="node!.config.selector" placeholder="input[type=file]" />
        </el-form-item>
        <el-form-item label="文件路径">
          <el-input v-model="node!.config.filePaths" type="textarea" :rows="3" placeholder="每行一个文件路径" />
        </el-form-item>
        <el-form-item label="多个文件">
          <el-switch v-model="node!.config.multiple" />
        </el-form-item>
      </template>
    </el-form>
    
    <div class="panel-actions">
      <el-button type="primary" size="small" @click="$emit('duplicate', node)">
        复制节点
      </el-button>
      <el-button type="danger" size="small" @click="$emit('delete', node.id)">
        删除节点
      </el-button>
    </div>
  </div>
  
  <el-empty v-else description="点击画布中的节点进行配置" />
</template>

<style scoped lang="scss">
.node-config-panel {
  .panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid #ebeef5;
    
    .title {
      font-size: 14px;
      font-weight: 600;
      color: #303133;
    }
  }
  
  .config-form {
    .el-form-item {
      margin-bottom: 12px;
    }
    
    .id-wrapper {
      display: flex;
      gap: 8px;
      
      .el-input {
        flex: 1;
      }
    }
  }
  
  .condition-list, .selector-list {
    width: 100%;
  }
  
  .condition-item, .selector-item {
    display: flex;
    gap: 8px;
    margin-bottom: 8px;
    align-items: center;
  }
  
  .panel-actions {
    margin-top: 16px;
    padding-top: 12px;
    border-top: 1px solid #ebeef5;
    display: flex;
    gap: 8px;
    justify-content: center;
  }
}
</style>
