import { ref, computed, type Ref } from 'vue'
import type { Node } from '@vue-flow/core'
import type { ActionNode } from '@/stores/workflow'

export interface SearchFilters {
  keyword: string
  category: string[]
  nodeType: string[]
  hasErrors: boolean | null
}

export interface SearchResult {
  nodes: Node[]
  totalCount: number
  highlightedIds: string[]
}

const nodeTypeLabels: Record<string, string> = {
  start: '开始',
  end: '结束',
  goto: '访问页面',
  click: '点击',
  input: '输入',
  wait: '等待',
  scroll: '滚动',
  screenshot: '截图',
  extract: '提取',
  evaluate: '执行脚本',
  press: '按键',
  hover: '悬停',
  upload: '上传',
  drag: '拖拽',
  keyboard: '键盘',
  js: 'JavaScript',
  condition: '条件',
  loop: '循环',
  break: '中断',
  new_tab: '新标签页',
  switch_tab: '切换标签页',
  close_tab: '关闭标签页',
  switch_frame: '切换框架',
  download: '下载',
  captcha: '验证码',
  ocr: 'OCR识别',
  image_match: '图像匹配'
}

const categoryLabels: Record<string, string> = {
  browser: '浏览器',
  interaction: '交互',
  extraction: '提取',
  ai: 'AI智能',
  control: '控制',
  file: '文件'
}

export function useNodeSearch(nodes: Ref<Node[]>) {
  const filters = ref<SearchFilters>({
    keyword: '',
    category: [],
    nodeType: [],
    hasErrors: null
  })

  const searchHistory = ref<string[]>([])
  const maxHistorySize = 10

  const filteredNodes = computed(() => {
    let result = nodes.value

    if (filters.value.keyword.trim()) {
      const keyword = filters.value.keyword.toLowerCase()
      result = result.filter(node => {
        const data = node.data as ActionNode
        if (!data) return false
        
        return (
          data.label?.toLowerCase().includes(keyword) ||
          data.type?.toLowerCase().includes(keyword) ||
          data.description?.toLowerCase().includes(keyword) ||
          JSON.stringify(data.config || {}).toLowerCase().includes(keyword)
        )
      })
    }

    if (filters.value.category.length > 0) {
      result = result.filter((node: Node) => {
        const data = node.data as ActionNode
        return data?.category && filters.value.category.includes(data.category)
      })
    }

    if (filters.value.nodeType.length > 0) {
      result = result.filter((node: Node) => {
        const data = node.data as ActionNode
        return data?.type && filters.value.nodeType.includes(data.type)
      })
    }

    if (filters.value.hasErrors !== null) {
      result = result.filter((node: Node) => {
        const data = node.data as ActionNode
        const config = data?.config || {}
        const hasError = !config.selector && ['click', 'input', 'hover'].includes(data.type) ||
                         !config.url && data.type === 'goto' ||
                         !config.selectors?.length && data.type === 'extract'
        return filters.value.hasErrors ? hasError : !hasError
      })
    }

    return result
  })

  const searchResults = computed((): SearchResult => {
    const highlightedIds = filteredNodes.value.map((n: Node) => n.id)
    return {
      nodes: filteredNodes.value,
      totalCount: nodes.value.length,
      highlightedIds
    }
  })

  const statistics = computed(() => {
    const total = nodes.value.length
    const filtered = filteredNodes.value.length
    const byCategory: Record<string, number> = {}
    const byType: Record<string, number> = {}

    nodes.value.forEach((node: Node) => {
      const data = node.data as ActionNode
      if (data?.category) {
        byCategory[data.category] = (byCategory[data.category] || 0) + 1
      }
      if (data?.type) {
        byType[data.type] = (byType[data.type] || 0) + 1
      }
    })

    return { total, filtered, byCategory, byType }
  })

  function search(keyword: string) {
    filters.value.keyword = keyword
    
    if (keyword.trim() && !searchHistory.value.includes(keyword)) {
      searchHistory.value.unshift(keyword.trim())
      if (searchHistory.value.length > maxHistorySize) {
        searchHistory.value.pop()
      }
    }
  }

  function setCategoryFilter(category: string[]) {
    filters.value.category = category
  }

  function setTypeFilter(types: string[]) {
    filters.value.nodeType = types
  }

  function setErrorFilter(hasErrors: boolean | null) {
    filters.value.hasErrors = hasErrors
  }

  function clearFilters() {
    filters.value = {
      keyword: '',
      category: [],
      nodeType: [],
      hasErrors: null
    }
  }

  function clearHistory() {
    searchHistory.value = []
  }

  function removeFromHistory(index: number) {
    searchHistory.value.splice(index, 1)
  }

  const highlightedNodeIds = ref<string[]>([])

  function highlightNode(nodeId: string) {
    highlightedNodeIds.value = [nodeId]
  }

  function clearHighlights() {
    highlightedNodeIds.value = []
  }

  function jumpToNode(nodeId: string, onJump?: (node: Node) => void) {
    const node = nodes.value.find((n: Node) => n.id === nodeId)
    if (node) {
      clearHighlights()
      highlightNode(nodeId)
      onJump?.(node)
    }
  }

  function getNodeLabel(type: string): string {
    return nodeTypeLabels[type] || type
  }

  function getCategoryLabel(category: string): string {
    return categoryLabels[category] || category
  }

  function getAllNodeTypes(): { value: string; label: string }[] {
    return Object.entries(nodeTypeLabels).map(([value, label]) => ({ value, label }))
  }

  function getAllCategories(): { value: string; label: string }[] {
    return Object.entries(categoryLabels).map(([value, label]) => ({ value, label }))
  }

  return {
    filters,
    searchHistory,
    filteredNodes,
    searchResults,
    statistics,
    highlightedNodeIds,
    search,
    setCategoryFilter,
    setTypeFilter,
    setErrorFilter,
    clearFilters,
    clearHistory,
    removeFromHistory,
    highlightNode,
    clearHighlights,
    jumpToNode,
    getNodeLabel,
    getCategoryLabel,
    getAllNodeTypes,
    getAllCategories,
    nodeTypeLabels,
    categoryLabels
  }
}
