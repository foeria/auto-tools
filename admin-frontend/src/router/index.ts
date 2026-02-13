import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/',
    redirect: '/workflow'
  },
  {
    path: '/workflow',
    name: 'Workflow',
    component: () => import('@/views/WorkflowDesigner.vue'),
    meta: { title: '工作流设计' }
  },
  {
    path: '/tasks',
    name: 'Tasks',
    component: () => import('@/views/TaskManager.vue'),
    meta: { title: '任务管理' }
  },
  {
    path: '/history',
    name: 'History',
    component: () => import('@/views/TaskHistory.vue'),
    meta: { title: '任务历史' }
  },
  {
    path: '/templates',
    name: 'Templates',
    component: () => import('@/views/SpiderTemplates.vue'),
    meta: { title: '爬虫模板' }
  },
  {
    path: '/data',
    name: 'Data',
    component: () => import('@/views/DataPreview.vue'),
    meta: { title: '数据预览' }
  },
  {
    path: '/settings',
    name: 'Settings',
    component: () => import('@/views/SystemSettings.vue'),
    meta: { title: '系统配置' }
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router
