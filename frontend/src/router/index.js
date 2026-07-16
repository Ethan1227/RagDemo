import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  {
    path: '/login',
    name: 'login',
    component: () => import('@/views/LoginView.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/register',
    name: 'register',
    component: () => import('@/views/RegisterView.vue'),
    meta: { public: true, title: '注册' },
  },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    children: [
      {
        path: '',
        name: 'home',
        component: () => import('@/views/HomeView.vue'),
        meta: { title: '首页' },
      },
      {
        path: 'consult',
        name: 'consult',
        component: () => import('@/views/ConsultView.vue'),
        meta: { title: '法律咨询' },
      },
      {
        path: 'knowledge',
        name: 'knowledge',
        component: () => import('@/views/KnowledgeView.vue'),
        meta: { title: '知识库管理' },
      },
      {
        path: 'knowledge/doc/:docId',
        name: 'knowledge-preview',
        component: () => import('@/views/KnowledgePreviewView.vue'),
        meta: { title: '知识库预览' },
      },
      {
        path: 'case',
        name: 'case',
        component: () => import('@/views/CaseView.vue'),
        meta: { title: '案件信息' },
      },
      {
        path: 'evidence',
        name: 'evidence',
        component: () => import('@/views/EvidenceView.vue'),
        meta: { title: '证据材料' },
      },
      {
        path: 'complaint',
        name: 'complaint',
        component: () => import('@/views/ComplaintView.vue'),
        meta: { title: '起诉状生成' },
      },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫：未登录访问受保护页面时跳转登录页
router.beforeEach((to) => {
  const token = localStorage.getItem('access_token')
  if (!to.meta.public && !token) {
    return { name: 'login', query: { redirect: to.fullPath } }
  }
  if (to.meta.public && token && (to.name === 'login' || to.name === 'register')) {
    return { name: 'home' }
  }
  return true
})

export default router
