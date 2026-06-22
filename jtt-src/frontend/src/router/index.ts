import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/login',
    },
    {
      path: '/login',
      name: 'Login',
      component: () => import('@/views/Login.vue'),
      meta: { title: '登录' },
    },
    {
      path: '/register',
      name: 'Register',
      component: () => import('@/views/Register.vue'),
      meta: { title: '注册' },
    },
    {
      path: '/home',
      name: 'Home',
      component: () => import('@/views/Home.vue'),
      meta: { title: '首页' },
    },
    {
      path: '/positions',
      name: 'Positions',
      component: () => import('@/views/positions/Index.vue'),
      meta: { title: '岗位探索' },
    },
    {
      path: '/positions/:id',
      name: 'PositionDetail',
      component: () => import('@/views/positions/Detail.vue'),
      meta: { title: '岗位详情' },
    },
    {
      path: '/graph',
      name: 'Graph',
      component: () => import('@/views/graph/Index.vue'),
      meta: { title: '知识图谱' },
    },
    {
      path: '/resumes',
      name: 'ResumeList',
      component: () => import('@/views/resume/Index.vue'),
      meta: { title: '我的简历' },
    },
    {
      path: '/resume/upload',
      name: 'ResumeUpload',
      component: () => import('@/views/resume/Upload.vue'),
      meta: { title: '上传简历' },
    },
    {
      path: '/resume/:id',
      name: 'ResumeDetail',
      component: () => import('@/views/resume/Detail.vue'),
      meta: { title: '简历详情' },
    },
    {
      path: '/resume/editor/:id?',
      name: 'ResumeEditor',
      component: () => import('@/views/resume/Editor.vue'),
      meta: { title: '简历编辑器' },
    },
    {
      path: '/resume/tailor/:resumeId/:positionId',
      name: 'ResumeTailor',
      component: () => import('@/views/resume/Tailor.vue'),
      meta: { title: 'AI 简历优化' },
    },
    {
      path: '/match',
      name: 'Match',
      component: () => import('@/views/match/Index.vue'),
      meta: { title: '匹配诊断' },
    },
    {
      path: '/match/result/:resumeId/:positionId',
      name: 'MatchResult',
      component: () => import('@/views/match/Result.vue'),
      meta: { title: '匹配结果' },
    },
    {
      path: '/learning',
      name: 'Learning',
      component: () => import('@/views/learning/Index.vue'),
      meta: { title: '学习路径' },
    },
    {
      path: '/profile',
      name: 'Profile',
      component: () => import('@/views/profile/Index.vue'),
      meta: { title: '个人中心' },
    },
    {
      path: '/favorites',
      name: 'Favorites',
      component: () => import('@/views/favorites/Index.vue'),
      meta: { title: '我的收藏' },
    },
  ],
})

router.beforeEach((to, _from, next) => {
  document.title = `${to.meta.title || '求职者端'} - 人才分析与决策系统`
  next()
})

export default router
