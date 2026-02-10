import { ref, computed } from 'vue'
import type { Node, Edge } from '@vue-flow/core'

export interface ValidationError {
  nodeId?: string
  type?: 'error' | 'warning' | 'info'
  message: string
  suggestion?: string
}

export interface ValidationResult {
  isValid: boolean
  errors: ValidationError[]
  warnings: ValidationError[]
  infos: ValidationError[]
}

const requiredConfigs: Record<string, string[]> = {
  goto: ['url'],
  click: ['selector'],
  input: ['selector', 'value'],
  wait: ['timeout'],
  wait_element: ['selector'],
  scroll: ['direction'],
  screenshot: ['savePath'],
  extract: ['selectors'],
  ocr: ['imagePath'],
  image_match: ['templatePath'],
  captcha: ['captchaType'],
  hover: ['selector'],
  drag: ['sourceSelector'],
  keyboard: ['keys', 'text', 'combo'],
  js: ['code'],
  condition: ['conditions'],
  loop: ['type', 'times'],
  break: ['breakType'],
  new_tab: ['url'],
  switch_tab: ['action'],
  close_tab: ['action'],
  switch_frame: ['action'],
  download: ['selector', 'savePath'],
  upload: ['selector', 'filePaths']
}

export function useWorkflowValidation() {
  const validationResult = ref<ValidationResult>({
    isValid: true,
    errors: [],
    warnings: [],
    infos: []
  })

  function validateWorkflow(nodes: Node[], edges: Edge[]): ValidationResult {
    const errors: ValidationError[] = []
    const warnings: ValidationError[] = []
    const infos: ValidationError[] = []

    if (nodes.length === 0) {
      errors.push({
        message: '工作流为空，请添加至少一个节点',
        suggestion: '从左侧组件库拖拽节点到画布中'
      })
      return { isValid: false, errors, warnings, infos }
    }

    const startNodes = nodes.filter(n => n.type === 'workflow-node' && (n.data as any)?.type === 'start')
    const endNodes = nodes.filter(n => n.type === 'workflow-node' && (n.data as any)?.type === 'end')

    if (startNodes.length === 0) {
      warnings.push({
        message: '工作流没有开始节点',
        suggestion: '建议添加开始节点作为工作流入口'
      })
    }

    if (endNodes.length === 0) {
      warnings.push({
        message: '工作流没有结束节点',
        suggestion: '建议添加结束节点作为工作流终点'
      })
    }

    const nodeIds = new Set(nodes.map(n => n.id))
    const connectedNodes = new Set<string>()
    edges.forEach(edge => {
      if (edge.source && nodeIds.has(edge.source)) {
        connectedNodes.add(edge.source)
      }
      if (edge.target && nodeIds.has(edge.target)) {
        connectedNodes.add(edge.target)
      }
    })

    nodes.forEach(node => {
      if (node.type !== 'workflow-node') return

      const nodeData = node.data as any
      if (!nodeData) return

      const nodeType = nodeData.type
      if (nodeType === 'start' || nodeType === 'end') return

      const nodeErrors = validateNodeConfig(node)
      errors.push(...nodeErrors.errors)
      warnings.push(...nodeErrors.warnings)
      infos.push(...nodeErrors.infos)

      if (!connectedNodes.has(node.id) && nodes.length > 1) {
        warnings.push({
          nodeId: node.id,
          message: `节点 "${nodeData.label}" 未连接到任何其他节点`,
          suggestion: '检查节点连接线是否正确'
        })
      }

      if (nodeType === 'goto' && !nodeData.config?.url) {
        errors.push({
          nodeId: node.id,
          message: '访问页面节点缺少URL配置',
          suggestion: '请在节点配置中设置目标URL'
        })
      }

      if (nodeType === 'goto' && nodeData.config?.url) {
        const url = nodeData.config.url
        if (!url.startsWith('http://') && !url.startsWith('https://')) {
          warnings.push({
            nodeId: node.id,
            message: 'URL格式可能不正确',
            suggestion: '建议使用完整的URL（包含http://或https://）'
          })
        }
      }

      if ((nodeType === 'click' || nodeType === 'input' || nodeType === 'hover') && !nodeData.config?.selector && !nodeData.config?.byImage) {
        warnings.push({
          nodeId: node.id,
          message: `节点 "${nodeData.label}" 未设置选择器`,
          suggestion: '使用CSS选择器或图像识别来定位元素'
        })
      }

      if (nodeType === 'loop' && nodeData.config?.type === 'times') {
        const times = parseInt(nodeData.config.times) || 0
        if (times > 1000) {
          warnings.push({
            nodeId: node.id,
            message: '循环次数较高（超过1000次）',
            suggestion: '考虑使用其他循环方式或优化流程'
          })
        }
        if (times <= 0) {
          errors.push({
            nodeId: node.id,
            message: '循环次数必须大于0',
            suggestion: '请设置有效的循环次数'
          })
        }
      }

      if (nodeType === 'wait' && nodeData.config?.timeout > 60000) {
        warnings.push({
          nodeId: node.id,
          message: '等待时间较长（超过60秒）',
          suggestion: '考虑使用等待元素出现代替固定等待'
        })
      }
    })

    const isolatedNodes = nodes.filter(n => {
      if (n.type !== 'workflow-node') return false
      const nodeData = n.data as any
      if (nodeData.type === 'start' || nodeData.type === 'end') return false
      return !connectedNodes.has(n.id)
    })

    if (isolatedNodes.length > 0) {
      warnings.push({
        message: `有 ${isolatedNodes.length} 个节点未连接到工作流`,
        suggestion: '删除孤立节点或正确连接它们'
      })
    }

    const hasCycle = detectCycle(nodes, edges)
    if (hasCycle) {
      errors.push({
        message: '检测到循环依赖',
        suggestion: '移除多余的连接线以消除循环'
      })
    }

    const firstNode = nodes.find(n => n.type === 'workflow-node' && (n.data as any)?.type === 'start')
    if (firstNode) {
      const incomingEdges = edges.filter(e => e.target === firstNode.id)
      if (incomingEdges.length > 0) {
        warnings.push({
          nodeId: firstNode.id,
          message: '开始节点有输入连接',
          suggestion: '开始节点应该只有输出连接'
        })
      }
    }

    const result: ValidationResult = {
      isValid: errors.length === 0,
      errors,
      warnings,
      infos
    }

    validationResult.value = result
    return result
  }

  function validateNodeConfig(node: Node): { errors: ValidationError[]; warnings: ValidationError[]; infos: ValidationError[] } {
    const errors: ValidationError[] = []
    const warnings: ValidationError[] = []
    const infos: ValidationError[] = []

    const nodeData = node.data as any
    if (!nodeData) return { errors, warnings, infos }

    const nodeType = nodeData.type
    const config = nodeData.config || {}

    const required = requiredConfigs[nodeType]
    if (required) {
      required.forEach(field => {
        const value = config[field]
        if (value === undefined || value === null || value === '') {
          const fieldLabels: Record<string, string> = {
            url: 'URL',
            selector: '选择器',
            value: '内容',
            timeout: '等待时间',
            direction: '滚动方向',
            savePath: '保存路径',
            selectors: '提取规则',
            imagePath: '图像路径',
            templatePath: '模板图路径',
            captchaType: '验证码类型',
            keys: '按键',
            text: '文本',
            combo: '快捷键',
            code: 'JavaScript代码',
            conditions: '条件列表',
            type: '循环类型',
            times: '循环次数',
            breakType: '中断类型',
            action: '操作',
            filePaths: '文件路径'
          }
          errors.push({
            nodeId: node.id,
            message: `缺少必要的配置: ${fieldLabels[field] || field}`,
            suggestion: `请在节点配置中填写 ${fieldLabels[field] || field}`
          })
        }
      })
    }

    if (nodeType === 'input' && config.value && typeof config.value === 'string') {
      if (config.value.length > 10000) {
        warnings.push({
          nodeId: node.id,
          message: '输入内容较长，可能影响性能',
          suggestion: '考虑分批输入或使用文件导入'
        })
      }
    }

    if (nodeType === 'js' && config.code) {
      try {
        new Function(config.code)
      } catch (e: any) {
        errors.push({
          nodeId: node.id,
          message: 'JavaScript代码语法错误',
          suggestion: e.message
        })
      }
    }

    return { errors, warnings, infos }
  }

  function detectCycle(nodes: Node[], edges: Edge[]): boolean {
    const adj = new Map<string, string[]>()
    nodes.forEach(node => {
      adj.set(node.id, [])
    })
    edges.forEach(edge => {
      if (edge.source && edge.target) {
        adj.get(edge.source)?.push(edge.target)
      }
    })

    const visited = new Set<string>()
    const recursionStack = new Set<string>()

    function hasCycleDFS(nodeId: string): boolean {
      visited.add(nodeId)
      recursionStack.add(nodeId)

      const neighbors = adj.get(nodeId) || []
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          if (hasCycleDFS(neighbor)) return true
        } else if (recursionStack.has(neighbor)) {
          return true
        }
      }

      recursionStack.delete(nodeId)
      return false
    }

    for (const node of nodes) {
      if (!visited.has(node.id)) {
        if (hasCycleDFS(node.id)) return true
      }
    }

    return false
  }

  function validateNodeConnections(nodeId: string, nodes: Node[], edges: Edge[]): ValidationError[] {
    const errors: ValidationError[] = []
    const node = nodes.find(n => n.id === nodeId)

    if (!node) return errors

    const incomingEdges = edges.filter(e => e.target === nodeId)
    const outgoingEdges = edges.filter(e => e.source === nodeId)

    const nodeData = node.data as any
    const isStartNode = nodeData?.type === 'start'
    const isEndNode = nodeData?.type === 'end'

    if (isStartNode && incomingEdges.length > 0) {
      errors.push({
        nodeId,
        type: 'warning',
        message: '开始节点不应有输入连接',
        suggestion: '移除连接到开始节点的线'
      })
    }

    if (isEndNode && outgoingEdges.length > 0) {
      errors.push({
        nodeId,
        type: 'warning',
        message: '结束节点不应有输出连接',
        suggestion: '移除从结束节点延伸的线'
      })
    }

    return errors
  }

  const isValid = computed(() => validationResult.value.isValid)
  const errors = computed(() => validationResult.value.errors)
  const warnings = computed(() => validationResult.value.warnings)
  const infos = computed(() => validationResult.value.infos)

  return {
    validationResult,
    validateWorkflow,
    validateNodeConfig,
    validateNodeConnections,
    isValid,
    errors,
    warnings,
    infos
  }
}
