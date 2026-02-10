/**
 * 可复用的爬虫模板库
 */
import type { Action, Extractor } from '../services/api'

export interface WorkflowTemplate {
  id: string
  name: string
  description: string
  category: string
  actions: Action[]
  extractors: Extractor[]
  tags: string[]
}

export const workflowTemplates: WorkflowTemplate[] = [
  {
    id: 'basic-search',
    name: '通用搜索流程',
    description: '适用于大多数网站的搜索功能自动化',
    category: 'search',
    tags: ['搜索', '输入', '点击'],
    actions: [
      { type: 'goto', url: '' },
      { type: 'input', selector: '#search-input, .search-box input, input[name="keyword"]', value: '', clear: true },
      { type: 'press', selector: '#search-input, .search-box input', key: 'Enter' },
      { type: 'wait', timeout: 2000 }
    ],
    extractors: [
      { type: 'html', selectors: ['.search-result', '.result-item', '.product-item'] }
    ]
  },
  {
    id: 'login-flow',
    name: '用户登录流程',
    description: '模拟用户登录操作的标准化流程',
    category: 'auth',
    tags: ['登录', '表单', '认证'],
    actions: [
      { type: 'goto', url: '' },
      { type: 'input', selector: '#username, input[name="username"], input[type="text"]', value: '', clear: true },
      { type: 'input', selector: '#password, input[name="password"], input[type="password"]', value: '', clear: true },
      { type: 'click', selector: '#login-btn, button[type="submit"], .login-button' },
      { type: 'wait', timeout: 3000 }
    ],
    extractors: [
      { type: 'html', selectors: ['.user-info', '#user-profile', '.logged-in'] }
    ]
  },
  {
    id: 'form-submit',
    name: '表单提交流程',
    description: '通用表单填写和提交流程',
    category: 'form',
    tags: ['表单', '提交', '数据录入'],
    actions: [
      { type: 'goto', url: '' },
      { type: 'input', selector: '.form-field input, input.form-control', value: '', clear: true },
      { type: 'input', selector: '.form-field textarea, textarea.form-control', value: '', clear: true },
      { type: 'click', selector: '#submit, button[type="submit"], .submit-btn' },
      { type: 'wait', timeout: 5000 }
    ],
    extractors: [
      { type: 'html', selectors: ['.success-message', '#result', '.form-result'] }
    ]
  },
  {
    id: 'detail-page',
    name: '详情页数据提取',
    description: '从详情页提取结构化数据',
    category: 'extraction',
    tags: ['详情', '提取', '结构化'],
    actions: [
      { type: 'goto', url: '' },
      { type: 'wait', timeout: 2000 }
    ],
    extractors: [
      {
        type: 'html',
        selectors: ['h1.title', '.product-title', '.detail-title'],
        extract_type: 'text'
      },
      {
        type: 'html',
        selectors: ['.price, .product-price', '.amount, .product-amount'],
        extract_type: 'text'
      },
      {
        type: 'html',
        selectors: ['.description, .product-description', '.content'],
        extract_type: 'html'
      },
      {
        type: 'html',
        selectors: ['img.product-image, .detail-image img'],
        extract_type: 'attribute',
        attribute: 'src'
      }
    ]
  },
  {
    id: 'pagination-scroll',
    name: '分页滚动加载',
    description: '处理分页和无限滚动场景',
    category: 'scroll',
    tags: ['滚动', '分页', '无限加载'],
    actions: [
      { type: 'goto', url: '' },
      { type: 'wait', timeout: 2000 },
      { type: 'scroll', y: 800 },
      { type: 'wait', timeout: 1500 },
      { type: 'scroll', y: 1600 },
      { type: 'wait', timeout: 1500 }
    ],
    extractors: [
      { type: 'html', selectors: ['.list-item', '.card-item', '.feed-item'] }
    ]
  },
  {
    id: 'image-click',
    name: '图像识别点击',
    description: '使用模板匹配进行图像识别点击',
    category: 'advanced',
    tags: ['图像', '识别', '点击'],
    actions: [
      { type: 'goto', url: '' },
      { type: 'wait', timeout: 2000 },
      { type: 'click', selector: '', by_image: true, template_path: 'button.png' },
      { type: 'wait', timeout: 2000 }
    ],
    extractors: [
      { type: 'html', selectors: ['.content', '#result'] }
    ]
  },
  {
    id: 'api-extraction',
    name: 'API数据提取',
    description: '从页面加载的API响应中提取数据',
    category: 'advanced',
    tags: ['API', 'JSON', '异步'],
    actions: [
      { type: 'goto', url: '' },
      { type: 'wait', timeout: 3000 }
    ],
    extractors: [
      {
        type: 'api',
        url_pattern: '/api/',
        timeout: 5000
      },
      {
        type: 'json',
        script_tag: 'window.__INITIAL_STATE__'
      }
    ]
  },
  {
    id: 'table-extraction',
    name: '表格数据提取',
    description: '从HTML表格中提取结构化数据',
    category: 'extraction',
    tags: ['表格', '结构化', '数据'],
    actions: [
      { type: 'goto', url: '' },
      { type: 'wait', timeout: 2000 }
    ],
    extractors: [
      {
        type: 'table',
        selector: 'table.data-table, table, .table',
        has_header: true
      }
    ]
  },
  {
    id: 'fullpage-capture',
    name: '完整页面截图',
    description: '截取完整的页面截图',
    category: 'screenshot',
    tags: ['截图', '全屏', '可视化'],
    actions: [
      { type: 'goto', url: '' },
      { type: 'wait', timeout: 3000 }
    ],
    extractors: [
      {
        type: 'screenshot',
        save_path: '',
        selector: ''
      },
      {
        type: 'fullpage'
      }
    ]
  },
  {
    id: 'multi-step',
    name: '多步骤向导',
    description: '处理多步骤表单或向导流程',
    category: 'wizard',
    tags: ['向导', '步骤', '多页'],
    actions: [
      { type: 'goto', url: '' },
      { type: 'input', selector: '.step-1 input', value: '', clear: true },
      { type: 'click', selector: '.step-1 .next-btn' },
      { type: 'wait', timeout: 1000 },
      { type: 'input', selector: '.step-2 input', value: '', clear: true },
      { type: 'click', selector: '.step-2 .next-btn' },
      { type: 'wait', timeout: 1000 },
      { type: 'click', selector: '.step-3 .submit-btn' },
      { type: 'wait', timeout: 3000 }
    ],
    extractors: [
      { type: 'html', selectors: ['.confirmation', '.success-page', '#result'] }
    ]
  }
]

export const actionTypes = [
  { value: 'goto', label: '访问页面', icon: 'Location', description: '跳转到指定URL' },
  { value: 'click', label: '点击元素', icon: 'Pointer', description: '点击页面上的元素' },
  { value: 'input', label: '输入内容', icon: 'Edit', description: '在输入框中填写内容' },
  { value: 'wait', label: '等待', icon: 'Clock', description: '等待指定时间或元素' },
  { value: 'screenshot', label: '截图', icon: 'Picture', description: '截取页面或元素截图' },
  { value: 'extract', label: '提取数据', icon: 'Document', description: '从页面提取数据' },
  { value: 'evaluate', label: '执行脚本', icon: 'Code', description: '执行JavaScript代码' },
  { value: 'scroll', label: '滚动', icon: 'Bottom', description: '滚动页面' },
  { value: 'press', label: '按键', icon: 'Keyboard', description: '模拟键盘按键' },
  { value: 'hover', label: '悬停', icon: 'Mouse', description: '鼠标悬停' },
  { value: 'upload', label: '上传文件', icon: 'Upload', description: '上传文件到输入框' }
]

export const extractorTypes = [
  { value: 'html', label: 'HTML提取', description: '提取HTML元素内容' },
  { value: 'json', label: 'JSON提取', description: '从script标签提取JSON' },
  { value: 'table', label: '表格提取', description: '提取HTML表格数据' },
  { value: 'xpath', label: 'XPath提取', description: '使用XPath提取数据' },
  { value: 'api', label: 'API响应', description: '捕获API响应数据' },
  { value: 'screenshot', label: '页面截图', description: '截取页面快照' },
  { value: 'fullpage', label: '完整页面', description: '提取完整页面文本' }
]

export function getTemplateById(id: string): WorkflowTemplate | undefined {
  return workflowTemplates.find(t => t.id === id)
}

export function getTemplatesByCategory(category: string): WorkflowTemplate[] {
  return workflowTemplates.filter(t => t.category === category)
}

export function searchTemplates(keyword: string): WorkflowTemplate[] {
  const lower = keyword.toLowerCase()
  return workflowTemplates.filter(t =>
    t.name.toLowerCase().includes(lower) ||
    t.description.toLowerCase().includes(lower) ||
    t.tags.some(tag => tag.toLowerCase().includes(lower))
  )
}
