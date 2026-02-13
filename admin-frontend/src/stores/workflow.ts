import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export interface ActionNode {
  id: string
  type: string
  label: string
  icon: string
  description: string
  category: 'browser' | 'interaction' | 'extraction' | 'control' | 'ai' | 'file'
  config: Record<string, any>
  position?: { x: number; y: number }
  children?: ActionNode[]
}

export const useWorkflowStore = defineStore('workflow', () => {
  const nodes = ref<ActionNode[]>([
    {
      id: 'start-1',
      type: 'start',
      label: '开始',
      icon: 'VideoPlay',
      description: '开始执行工作流',
      category: 'control',
      config: {}
    },
    {
      id: 'goto-1',
      type: 'goto',
      label: '访问页面',
      icon: 'Location',
      description: '跳转到指定URL',
      category: 'browser',
      config: { url: '', waitUntil: 'domcontentloaded' }
    },
    {
      id: 'click-1',
      type: 'click',
      label: '点击元素',
      icon: 'Pointer',
      description: '点击页面元素',
      category: 'interaction',
      config: { selector: '', selectorType: 'css', byImage: false, templatePath: '', offsetX: 0, offsetY: 0 }
    },
    {
      id: 'input-1',
      type: 'input',
      label: '输入内容',
      icon: 'Edit',
      description: '输入文本内容',
      category: 'interaction',
      config: { selector: '', selectorType: 'css', value: '', clear: true }
    },
    {
      id: 'wait-1',
      type: 'wait',
      label: '等待时间',
      icon: 'Clock',
      description: '等待指定时间（毫秒）',
      category: 'control',
      config: { timeout: 1000 }
    },
    {
      id: 'wait-element-1',
      type: 'wait_element',
      label: '等待元素',
      icon: 'View',
      description: '等待元素出现或消失',
      category: 'interaction',
      config: { selector: '', selectorType: 'css', state: 'present', timeout: 10000 }
    },
    {
      id: 'scroll-1',
      type: 'scroll',
      label: '页面滚动',
      icon: 'Bottom',
      description: '滚动页面到指定位置',
      category: 'interaction',
      config: { direction: 'down', amount: 500, selector: '', selectorType: 'css' }
    },
    {
      id: 'screenshot-1',
      type: 'screenshot',
      label: '页面截图',
      icon: 'Picture',
      description: '截取页面或元素截图',
      category: 'extraction',
      config: { fullPage: false, selector: '', selectorType: 'css', path: '' }
    },
    {
      id: 'extract-1',
      type: 'extract',
      label: '提取数据',
      icon: 'Document',
      description: '提取页面数据',
      category: 'extraction',
      config: { selectors: [], format: 'json' }
    },
    {
      id: 'ocr-1',
      type: 'ocr',
      label: '图像识别(OCR)',
      icon: 'Reading',
      description: '从截图或区域识别文字',
      category: 'ai',
      config: { imagePath: '', region: null, languages: ['chi_sim'] }
    },
    {
      id: 'image-match-1',
      type: 'image_match',
      label: '图像匹配',
      icon: 'PictureFilled',
      description: '在页面中查找指定图像',
      category: 'ai',
      config: { templatePath: '', threshold: 0.8, action: 'click', offsetX: 0, offsetY: 0 }
    },
    {
      id: 'captcha-1',
      type: 'captcha',
      label: '验证码识别',
      icon: 'Lock',
      description: '自动识别并填写验证码',
      category: 'ai',
      config: { type: 'image', templatePath: '', api: '' }
    },
    {
      id: 'hover-1',
      type: 'hover',
      label: '悬停元素',
      icon: 'Pointer',
      description: '鼠标悬停在元素上',
      category: 'interaction',
      config: { selector: '', selectorType: 'css' }
    },
    {
      id: 'drag-1',
      type: 'drag',
      label: '拖拽元素',
      icon: 'Rank',
      description: '拖拽元素到目标位置',
      category: 'interaction',
      config: { sourceSelector: '', sourceSelectorType: 'css', targetSelector: '', targetSelectorType: 'css', targetX: 0, targetY: 0 }
    },
    {
      id: 'keyboard-1',
      type: 'keyboard',
      label: '键盘操作',
      icon: 'Edit',
      description: '模拟键盘按键或快捷键',
      category: 'interaction',
      config: { keys: [], text: '', pressEnter: false }
    },
    {
      id: 'switch-tab-1',
      type: 'switch_tab',
      label: '切换标签页',
      icon: 'CopyDocument',
      description: '切换到指定标签页',
      category: 'browser',
      config: { action: 'next', index: 0, url: '' }
    },
    {
      id: 'new-tab-1',
      type: 'new_tab',
      label: '打开新标签页',
      icon: 'DocumentAdd',
      description: '在新标签页打开URL',
      category: 'browser',
      config: { url: '', switchTo: true }
    },
    {
      id: 'close-tab-1',
      type: 'close_tab',
      label: '关闭标签页',
      icon: 'Remove',
      description: '关闭当前或指定标签页',
      category: 'browser',
      config: { action: 'current', index: 0 }
    },
    {
      id: 'switch-frame-1',
      type: 'switch_frame',
      label: '切换框架',
      icon: 'Menu',
      description: '切换到指定iframe框架',
      category: 'browser',
      config: { selector: '', selectorType: 'css', index: -1 }
    },
    {
      id: 'download-1',
      type: 'download',
      label: '下载文件',
      icon: 'Download',
      description: '点击下载文件',
      category: 'file',
      config: { selector: '', selectorType: 'css', savePath: '', url: '' }
    },
    {
      id: 'upload-1',
      type: 'upload',
      label: '上传文件',
      icon: 'Upload',
      description: '上传文件到input元素',
      category: 'file',
      config: { selector: '', selectorType: 'css', filePaths: [] }
    },
    {
      id: 'js-1',
      type: 'js',
      label: '执行JavaScript',
      icon: 'Edit',
      description: '执行自定义JavaScript代码',
      category: 'control',
      config: { code: '', returnValue: false }
    },
    {
      id: 'condition-1',
      type: 'condition',
      label: '条件判断',
      icon: 'Odometer',
      description: '根据条件分支执行',
      category: 'control',
      config: { conditions: [], logic: 'and' }
    },
    {
      id: 'loop-1',
      type: 'loop',
      label: '循环',
      icon: 'Refresh',
      description: '循环执行一段操作',
      category: 'control',
      config: { type: 'times', selector: '', selectorType: 'css', times: 10, selectorList: [] }
    },
    {
      id: 'break-1',
      type: 'break',
      label: '中断循环',
      icon: 'CircleClose',
      description: '中断当前循环',
      category: 'control',
      config: { type: 'break' }
    },
    {
      id: 'end-1',
      type: 'end',
      label: '结束',
      icon: 'CircleCheck',
      description: '结束执行工作流',
      category: 'control',
      config: {}
    }
  ])
  
  const currentWorkflow = ref<ActionNode[]>([])
  const selectedNodeId = ref<string | null>(null)
  
  const availableNodes = computed(() => nodes.value)
  
  const nodesByCategory = computed(() => {
    const categories: Record<string, ActionNode[]> = {}
    nodes.value.forEach(node => {
      if (!categories[node.category]) {
        categories[node.category] = []
      }
      categories[node.category].push(node)
    })
    return categories
  })
  
  function addNodeToWorkflow(node: ActionNode) {
    const newNode = { ...node, id: `${node.type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}` }
    currentWorkflow.value.push(newNode)
    return newNode
  }
  
  function removeNodeFromWorkflow(nodeId: string) {
    const index = currentWorkflow.value.findIndex(n => n.id === nodeId)
    if (index > -1) {
      currentWorkflow.value.splice(index, 1)
    }
  }
  
  function updateNodeConfig(nodeId: string, config: Record<string, any>) {
    const node = currentWorkflow.value.find(n => n.id === nodeId)
    if (node) {
      node.config = { ...node.config, ...config }
    }
  }
  
  function updateNodePosition(nodeId: string, position: { x: number; y: number }) {
    const node = currentWorkflow.value.find(n => n.id === nodeId)
    if (node) {
      node.position = position
    }
  }
  
  function reorderNodes(fromIndex: number, toIndex: number) {
    const [removed] = currentWorkflow.value.splice(fromIndex, 1)
    currentWorkflow.value.splice(toIndex, 0, removed)
  }
  
  function clearWorkflow() {
    currentWorkflow.value = []
  }
  
  function loadWorkflow(workflow: ActionNode[]) {
    currentWorkflow.value = [...workflow]
  }
  
  function getNodeById(nodeId: string) {
    return currentWorkflow.value.find(n => n.id === nodeId)
  }
  
  return {
    nodes,
    currentWorkflow,
    selectedNodeId,
    availableNodes,
    nodesByCategory,
    addNodeToWorkflow,
    removeNodeFromWorkflow,
    updateNodeConfig,
    updateNodePosition,
    reorderNodes,
    clearWorkflow,
    loadWorkflow,
    getNodeById
  }
})
