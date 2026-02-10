import { ref, computed } from 'vue'
import type { Node, Edge } from '@vue-flow/core'

export interface WorkflowTemplate {
  id: string
  name: string
  description: string
  category: TemplateCategory
  tags: string[]
  nodes: TemplateNode[]
  edges: TemplateEdge[]
  estimatedTime: string
  difficulty: 'easy' | 'medium' | 'hard'
}

export interface TemplateNode {
  id: string
  type: string
  label: string
  position: { x: number; y: number }
  config: Record<string, any>
}

export interface TemplateEdge {
  id: string
  source: string
  target: string
  sourceHandle?: string
  targetHandle?: string
}

export type TemplateCategory = 
  | 'basic'
  | 'ecommerce'
  | 'social'
  | 'data'
  | 'automation'
  | 'auth'

const defaultTemplates: WorkflowTemplate[] = [
  {
    id: 'basic-scrape',
    name: '基础网页抓取',
    description: '最简单的网页抓取流程：访问页面 → 等待加载 → 提取数据',
    category: 'basic',
    tags: ['入门', '基础', '网页'],
    estimatedTime: '2分钟',
    difficulty: 'easy',
    nodes: [
      {
        id: 'start',
        type: 'start',
        label: '开始',
        position: { x: 100, y: 100 },
        config: { url: '' }
      },
      {
        id: 'goto',
        type: 'goto',
        label: '访问页面',
        position: { x: 100, y: 200 },
        config: { url: '', timeout: 5000 }
      },
      {
        id: 'wait',
        type: 'wait',
        label: '等待加载',
        position: { x: 100, y: 300 },
        config: { timeout: 2000, state: 'domcontentloaded' }
      },
      {
        id: 'extract',
        type: 'extract',
        label: '提取数据',
        position: { x: 100, y: 400 },
        config: { 
          selectors: [
            { name: 'title', selector: 'h1', extractType: 'text', attribute: '' },
            { name: 'content', selector: '.content', extractType: 'text', attribute: '' }
          ]
        }
      },
      {
        id: 'end',
        type: 'end',
        label: '结束',
        position: { x: 100, y: 500 },
        config: {}
      }
    ],
    edges: [
      { id: 'e1', source: 'start', target: 'goto' },
      { id: 'e2', source: 'goto', target: 'wait' },
      { id: 'e3', source: 'wait', target: 'extract' },
      { id: 'e4', source: 'extract', target: 'end' }
    ]
  },
  {
    id: 'login-required',
    name: '登录后抓取',
    description: '需要登录才能访问的内容抓取流程',
    category: 'auth',
    tags: ['登录', '认证', 'cookies'],
    estimatedTime: '5分钟',
    difficulty: 'medium',
    nodes: [
      {
        id: 'start',
        type: 'start',
        label: '开始',
        position: { x: 100, y: 100 },
        config: { url: '' }
      },
      {
        id: 'goto-login',
        type: 'goto',
        label: '访问登录页',
        position: { x: 100, y: 200 },
        config: { url: '', timeout: 5000 }
      },
      {
        id: 'wait-login',
        type: 'wait',
        label: '等待页面',
        position: { x: 100, y: 300 },
        config: { timeout: 2000, state: 'domcontentloaded' }
      },
      {
        id: 'input-user',
        type: 'input',
        label: '输入账号',
        position: { x: 100, y: 400 },
        config: { selector: '#username, input[name="username"]', value: '', clear: true }
      },
      {
        id: 'input-pwd',
        type: 'input',
        label: '输入密码',
        position: { x: 100, y: 500 },
        config: { selector: '#password, input[name="password"]', value: '', clear: true }
      },
      {
        id: 'click-login',
        type: 'click',
        label: '点击登录',
        position: { x: 100, y: 600 },
        config: { selector: '#login-btn, button[type="submit"]' }
      },
      {
        id: 'wait-login-wait',
        type: 'wait',
        label: '等待登录',
        position: { x: 100, y: 700 },
        config: { timeout: 3000, state: 'networkidle' }
      },
      {
        id: 'goto-content',
        type: 'goto',
        label: '访问目标页',
        position: { x: 100, y: 800 },
        config: { url: '', timeout: 5000 }
      },
      {
        id: 'extract-content',
        type: 'extract',
        label: '提取数据',
        position: { x: 100, y: 900 },
        config: { selectors: [{ name: 'data', selector: '.content', extractType: 'text', attribute: '' }] }
      },
      {
        id: 'end',
        type: 'end',
        label: '结束',
        position: { x: 100, y: 1000 },
        config: {}
      }
    ],
    edges: [
      { id: 'e1', source: 'start', target: 'goto-login' },
      { id: 'e2', source: 'goto-login', target: 'wait-login' },
      { id: 'e3', source: 'wait-login', target: 'input-user' },
      { id: 'e4', source: 'input-user', target: 'input-pwd' },
      { id: 'e5', source: 'input-pwd', target: 'click-login' },
      { id: 'e6', source: 'click-login', target: 'wait-login-wait' },
      { id: 'e7', source: 'wait-login-wait', target: 'goto-content' },
      { id: 'e8', source: 'goto-content', target: 'extract-content' },
      { id: 'e9', source: 'extract-content', target: 'end' }
    ]
  },
  {
    id: 'pagination-list',
    name: '列表分页抓取',
    description: '抓取列表页并翻页提取所有数据',
    category: 'data',
    tags: ['分页', '列表', '批量'],
    estimatedTime: '10分钟',
    difficulty: 'medium',
    nodes: [
      {
        id: 'start',
        type: 'start',
        label: '开始',
        position: { x: 100, y: 100 },
        config: { url: '' }
      },
      {
        id: 'goto-page',
        type: 'goto',
        label: '访问列表页',
        position: { x: 100, y: 200 },
        config: { url: '', timeout: 5000 }
      },
      {
        id: 'wait-page',
        type: 'wait',
        label: '等待加载',
        position: { x: 100, y: 300 },
        config: { timeout: 2000, state: 'domcontentloaded' }
      },
      {
        id: 'extract-list',
        type: 'extract',
        label: '提取列表',
        position: { x: 100, y: 400 },
        config: { 
          selectors: [
            { name: 'items', selector: '.list-item, .item, .product', extractType: 'text', attribute: '' }
          ]
        }
      },
      {
        id: 'click-next',
        type: 'click',
        label: '下一页',
        position: { x: 100, y: 500 },
        config: { selector: '.next, .pagination .next, a[rel="next"]' }
      },
      {
        id: 'loop-check',
        type: 'condition',
        label: '是否有更多',
        position: { x: 100, y: 600 },
        config: {
          logic: 'and',
          conditions: [
            { selector: '.next, .pagination .next, a[rel="next"]', operator: 'exists', value: '' }
          ]
        }
      },
      {
        id: 'end',
        type: 'end',
        label: '结束',
        position: { x: 400, y: 600 },
        config: {}
      }
    ],
    edges: [
      { id: 'e1', source: 'start', target: 'goto-page' },
      { id: 'e2', source: 'goto-page', target: 'wait-page' },
      { id: 'e3', source: 'wait-page', target: 'extract-list' },
      { id: 'e4', source: 'extract-list', target: 'click-next' },
      { id: 'e5', source: 'click-next', target: 'loop-check' },
      { id: 'e6', source: 'loop-check', target: 'end', sourceHandle: 'false' },
      { id: 'e7', source: 'loop-check', target: 'wait-page', sourceHandle: 'true' }
    ]
  },
  {
    id: 'scroll-infinite',
    name: '无限滚动抓取',
    description: '处理无限滚动页面，自动加载更多内容',
    category: 'automation',
    tags: ['滚动', '无限加载', 'AJAX'],
    estimatedTime: '8分钟',
    difficulty: 'medium',
    nodes: [
      {
        id: 'start',
        type: 'start',
        label: '开始',
        position: { x: 100, y: 100 },
        config: { url: '' }
      },
      {
        id: 'goto',
        type: 'goto',
        label: '访问页面',
        position: { x: 100, y: 200 },
        config: { url: '', timeout: 5000 }
      },
      {
        id: 'scroll-1',
        type: 'scroll',
        label: '滚动加载',
        position: { x: 100, y: 300 },
        config: { direction: 'down', amount: 500 }
      },
      {
        id: 'wait-scroll',
        type: 'wait',
        label: '等待加载',
        position: { x: 100, y: 400 },
        config: { timeout: 2000, state: 'networkidle' }
      },
      {
        id: 'extract',
        type: 'extract',
        label: '提取数据',
        position: { x: 100, y: 500 },
        config: { selectors: [{ name: 'items', selector: '.feed-item, .infinite-item', extractType: 'text', attribute: '' }] }
      },
      {
        id: 'scroll-more',
        type: 'scroll',
        label: '继续滚动',
        position: { x: 100, y: 600 },
        config: { direction: 'down', amount: 1000 }
      },
      {
        id: 'condition',
        type: 'condition',
        label: '是否继续',
        position: { x: 100, y: 700 },
        config: {
          logic: 'and',
          conditions: [
            { selector: '.loading, .spinner', operator: 'not_exists', value: '' },
            { selector: '.no-more, .end-of-list', operator: 'not_exists', value: '' }
          ]
        }
      },
      {
        id: 'end',
        type: 'end',
        label: '结束',
        position: { x: 400, y: 700 },
        config: {}
      }
    ],
    edges: [
      { id: 'e1', source: 'start', target: 'goto' },
      { id: 'e2', source: 'goto', target: 'scroll-1' },
      { id: 'e3', source: 'scroll-1', target: 'wait-scroll' },
      { id: 'e4', source: 'wait-scroll', target: 'extract' },
      { id: 'e5', source: 'extract', target: 'scroll-more' },
      { id: 'e6', source: 'scroll-more', target: 'condition' },
      { id: 'e7', source: 'condition', target: 'end', sourceHandle: 'false' },
      { id: 'e8', source: 'condition', target: 'scroll-1', sourceHandle: 'true' }
    ]
  },
  {
    id: 'form-submit-flow',
    name: '表单提交流程',
    description: '填写并提交复杂表单',
    category: 'automation',
    tags: ['表单', '提交', '输入'],
    estimatedTime: '5分钟',
    difficulty: 'medium',
    nodes: [
      {
        id: 'start',
        type: 'start',
        label: '开始',
        position: { x: 100, y: 100 },
        config: { url: '' }
      },
      {
        id: 'goto',
        type: 'goto',
        label: '访问表单页',
        position: { x: 100, y: 200 },
        config: { url: '', timeout: 5000 }
      },
      {
        id: 'input-1',
        type: 'input',
        label: '填写字段1',
        position: { x: 100, y: 300 },
        config: { selector: 'input[name="field1"], #field1', value: '', clear: true }
      },
      {
        id: 'input-2',
        type: 'input',
        label: '填写字段2',
        position: { x: 100, y: 400 },
        config: { selector: 'textarea[name="field2"], #field2', value: '', clear: true }
      },
      {
        id: 'select',
        type: 'input',
        label: '选择选项',
        position: { x: 100, y: 500 },
        config: { selector: 'select[name="category"], #category', value: '', clear: true }
      },
      {
        id: 'check',
        type: 'input',
        label: '勾选同意',
        position: { x: 100, y: 600 },
        config: { selector: '#agree, input[type="checkbox"]', value: '', clear: true }
      },
      {
        id: 'submit',
        type: 'click',
        label: '提交表单',
        position: { x: 100, y: 700 },
        config: { selector: '#submit, button[type="submit"], .submit-btn' }
      },
      {
        id: 'wait-result',
        type: 'wait',
        label: '等待结果',
        position: { x: 100, y: 800 },
        config: { timeout: 3000, state: 'networkidle' }
      },
      {
        id: 'extract-result',
        type: 'extract',
        label: '提取结果',
        position: { x: 100, y: 900 },
        config: { selectors: [{ name: 'result', selector: '.result, #message', extractType: 'text', attribute: '' }] }
      },
      {
        id: 'end',
        type: 'end',
        label: '结束',
        position: { x: 100, y: 1000 },
        config: {}
      }
    ],
    edges: [
      { id: 'e1', source: 'start', target: 'goto' },
      { id: 'e2', source: 'goto', target: 'input-1' },
      { id: 'e3', source: 'input-1', target: 'input-2' },
      { id: 'e4', source: 'input-2', target: 'select' },
      { id: 'e5', source: 'select', target: 'check' },
      { id: 'e6', source: 'check', target: 'submit' },
      { id: 'e7', source: 'submit', target: 'wait-result' },
      { id: 'e8', source: 'wait-result', target: 'extract-result' },
      { id: 'e9', source: 'extract-result', target: 'end' }
    ]
  },
  {
    id: 'detail-multi',
    name: '多详情页抓取',
    description: '从列表页进入多个详情页分别提取数据',
    category: 'data',
    tags: ['详情页', '列表', '批量'],
    estimatedTime: '15分钟',
    difficulty: 'hard',
    nodes: [
      {
        id: 'start',
        type: 'start',
        label: '开始',
        position: { x: 100, y: 100 },
        config: { url: '' }
      },
      {
        id: 'goto-list',
        type: 'goto',
        label: '访问列表页',
        position: { x: 100, y: 200 },
        config: { url: '', timeout: 5000 }
      },
      {
        id: 'wait-list',
        type: 'wait',
        label: '等待加载',
        position: { x: 100, y: 300 },
        config: { timeout: 2000, state: 'domcontentloaded' }
      },
      {
        id: 'extract-links',
        type: 'extract',
        label: '提取链接',
        position: { x: 100, y: 400 },
        config: {
          selectors: [
            { name: 'links', selector: '.item a, .list-item a[href]', extractType: 'attribute', attribute: 'href' }
          ]
        }
      },
      {
        id: 'loop',
        type: 'loop',
        label: '遍历链接',
        position: { x: 100, y: 500 },
        config: { type: 'times', times: 10 }
      },
      {
        id: 'get-link',
        type: 'evaluate',
        label: '获取链接',
        position: { x: 100, y: 600 },
        config: { code: 'return links[loopIndex]' }
      },
      {
        id: 'goto-detail',
        type: 'goto',
        label: '访问详情页',
        position: { x: 100, y: 700 },
        config: { url: '', timeout: 5000 }
      },
      {
        id: 'wait-detail',
        type: 'wait',
        label: '等待详情',
        position: { x: 100, y: 800 },
        config: { timeout: 2000, state: 'domcontentloaded' }
      },
      {
        id: 'extract-detail',
        type: 'extract',
        label: '提取详情',
        position: { x: 100, y: 900 },
        config: {
          selectors: [
            { name: 'title', selector: 'h1, .title', extractType: 'text', attribute: '' },
            { name: 'content', selector: '.content, .description', extractType: 'text', attribute: '' }
          ]
        }
      },
      {
        id: 'save-data',
        type: 'evaluate',
        label: '保存数据',
        position: { x: 100, y: 1000 },
        config: { code: 'results.push(detailData)' }
      },
      {
        id: 'end',
        type: 'end',
        label: '结束',
        position: { x: 100, y: 1100 },
        config: {}
      }
    ],
    edges: [
      { id: 'e1', source: 'start', target: 'goto-list' },
      { id: 'e2', source: 'goto-list', target: 'wait-list' },
      { id: 'e3', source: 'wait-list', target: 'extract-links' },
      { id: 'e4', source: 'extract-links', target: 'loop' },
      { id: 'e5', source: 'loop', target: 'get-link' },
      { id: 'e6', source: 'get-link', target: 'goto-detail' },
      { id: 'e7', source: 'goto-detail', target: 'wait-detail' },
      { id: 'e8', source: 'wait-detail', target: 'extract-detail' },
      { id: 'e9', source: 'extract-detail', target: 'save-data' },
      { id: 'e10', source: 'save-data', target: 'loop', sourceHandle: 'true' },
      { id: 'e11', source: 'loop', target: 'end', sourceHandle: 'false' }
    ]
  },
  {
    id: 'screenshot-flow',
    name: '页面截图流程',
    description: '截取页面或特定元素的截图',
    category: 'automation',
    tags: ['截图', '图片', '可视化'],
    estimatedTime: '3分钟',
    difficulty: 'easy',
    nodes: [
      {
        id: 'start',
        type: 'start',
        label: '开始',
        position: { x: 100, y: 100 },
        config: { url: '' }
      },
      {
        id: 'goto',
        type: 'goto',
        label: '访问页面',
        position: { x: 100, y: 200 },
        config: { url: '', timeout: 5000 }
      },
      {
        id: 'wait',
        type: 'wait',
        label: '等待加载',
        position: { x: 100, y: 300 },
        config: { timeout: 2000, state: 'domcontentloaded' }
      },
      {
        id: 'screenshot-full',
        type: 'screenshot',
        label: '全屏截图',
        position: { x: 100, y: 400 },
        config: { savePath: '', fullPage: true }
      },
      {
        id: 'screenshot-element',
        type: 'screenshot',
        label: '元素截图',
        position: { x: 100, y: 500 },
        config: { selector: '.main-content, #content', savePath: '' }
      },
      {
        id: 'end',
        type: 'end',
        label: '结束',
        position: { x: 100, y: 600 },
        config: {}
      }
    ],
    edges: [
      { id: 'e1', source: 'start', target: 'goto' },
      { id: 'e2', source: 'goto', target: 'wait' },
      { id: 'e3', source: 'wait', target: 'screenshot-full' },
      { id: 'e4', source: 'screenshot-full', target: 'screenshot-element' },
      { id: 'e5', source: 'screenshot-element', target: 'end' }
    ]
  }
]

const categoryNames: Record<TemplateCategory, string> = {
  basic: '基础模板',
  ecommerce: '电商模板',
  social: '社交媒体',
  data: '数据采集',
  automation: '自动化流程',
  auth: '认证登录'
}

const categoryIcons: Record<TemplateCategory, string> = {
  basic: 'Document',
  ecommerce: 'ShoppingCart',
  social: 'ChatDotRound',
  data: 'DataAnalysis',
  automation: 'SetUp',
  auth: 'Lock'
}

export function useWorkflowTemplates() {
  const templates = ref<WorkflowTemplate[]>(defaultTemplates)
  const selectedTemplate = ref<WorkflowTemplate | null>(null)
  const showTemplateDialog = ref(false)

  const templatesByCategory = computed(() => {
    const grouped: Record<TemplateCategory, WorkflowTemplate[]> = {
      basic: [],
      ecommerce: [],
      social: [],
      data: [],
      automation: [],
      auth: []
    }
    
    templates.value.forEach(template => {
      grouped[template.category].push(template)
    })
    
    return grouped
  })

  const categories = computed(() => {
    return Object.entries(categoryNames).map(([key, name]) => ({
      key,
      name,
      icon: categoryIcons[key as TemplateCategory],
      count: templatesByCategory.value[key as TemplateCategory]?.length || 0
    }))
  })

  function getTemplateById(id: string): WorkflowTemplate | undefined {
    return templates.value.find(t => t.id === id)
  }

  function getTemplatesByTag(tag: string): WorkflowTemplate[] {
    return templates.value.filter(t => 
      t.tags.some(t => t.toLowerCase().includes(tag.toLowerCase()))
    )
  }

  function searchTemplates(keyword: string): WorkflowTemplate[] {
    const lower = keyword.toLowerCase()
    return templates.value.filter(t =>
      t.name.toLowerCase().includes(lower) ||
      t.description.toLowerCase().includes(lower) ||
      t.tags.some(tag => tag.toLowerCase().includes(lower))
    )
  }

  function convertToNodes(template: WorkflowTemplate): Node[] {
    return template.nodes.map(node => ({
      id: node.id,
      type: 'workflow-node',
      position: node.position,
      data: {
        id: node.id,
        type: node.type,
        label: node.label,
        config: node.config,
        icon: '',
        description: '',
        category: 'automation' as const
      }
    }))
  }

  function convertToEdges(template: WorkflowTemplate): Edge[] {
    return template.edges.map((edge, index) => ({
      id: edge.id || `e${index}`,
      source: edge.source,
      target: edge.target,
      sourceHandle: edge.sourceHandle,
      targetHandle: edge.targetHandle,
      type: 'workflow-edge'
    }))
  }

  function applyTemplate(
    template: WorkflowTemplate,
    onConvert: (nodes: Node[], edges: Edge[]) => void
  ): void {
    const nodes = convertToNodes(template)
    const edges = convertToEdges(template)
    onConvert(nodes, edges)
    selectedTemplate.value = template
  }

  function openTemplateDialog() {
    showTemplateDialog.value = true
  }

  function closeTemplateDialog() {
    showTemplateDialog.value = false
    selectedTemplate.value = null
  }

  return {
    templates,
    selectedTemplate,
    showTemplateDialog,
    templatesByCategory,
    categories,
    getTemplateById,
    getTemplatesByTag,
    searchTemplates,
    applyTemplate,
    openTemplateDialog,
    closeTemplateDialog,
    categoryNames,
    categoryIcons
  }
}
