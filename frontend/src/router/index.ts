import { createRouter, createWebHistory } from 'vue-router'
import type { UserRole } from '../types'
import { useAuthStore } from '../stores/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'login', component: () => import('../views/LoginView.vue') },
    {
      path: '/',
      component: () => import('../components/AppShell.vue'),
      meta: { requiresAuth: true },
      children: [
        { path: '', redirect: '/dashboard' },
        { path: 'dashboard', name: 'dashboard', component: () => import('../views/DashboardView.vue') },
        { path: 'students', name: 'students', component: () => import('../views/StudentsView.vue') },
        { path: 'students/:id', name: 'student-detail', component: () => import('../views/StudentDetailView.vue') },
        { path: 'cases', name: 'cases', component: () => import('../views/CasesView.vue') },
        { path: 'followups', name: 'followups', component: () => import('../views/FollowUpsView.vue') },
        { path: 'referrals', name: 'referrals', component: () => import('../views/ReferralsView.vue') },
        { path: 'reports', name: 'reports', component: () => import('../views/ReportsView.vue') },
        {
          path: 'users',
          name: 'users',
          component: () => import('../views/UsersView.vue'),
          meta: { roles: ['ADMIN'] satisfies UserRole[] },
        },
        {
          path: 'organizations',
          name: 'organizations',
          component: () => import('../views/OrganizationsView.vue'),
          meta: { roles: ['ADMIN'] satisfies UserRole[] },
        },
        {
          path: 'audit-logs',
          name: 'audit-logs',
          component: () => import('../views/AuditLogsView.vue'),
          meta: { roles: ['ADMIN'] satisfies UserRole[] },
        },
      ],
    },
    { path: '/:pathMatch(.*)*', component: () => import('../views/NotFoundView.vue') },
  ],
})

router.beforeEach(async (to) => {
  const auth = useAuthStore()
  if (to.meta.requiresAuth) {
    if (!auth.token) return { name: 'login', query: { redirect: to.fullPath } }
    if (!auth.user) {
      try {
        await auth.fetchMe()
      } catch {
        auth.logout()
        return { name: 'login' }
      }
    }
    const roles = to.meta.roles as UserRole[] | undefined
    if (roles && auth.user && !roles.includes(auth.user.role)) {
      return { name: 'dashboard' }
    }
  }
  if (to.name === 'login' && auth.token) return { name: 'dashboard' }
  return true
})

export default router
