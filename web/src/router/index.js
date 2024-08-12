import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import FlagBrowserView from '@/views/FlagBrowserView.vue'
import ManualSubmissionView from '@/views/ManualSubmissionView.vue'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView
    },
    {
      path: '/flags',
      name: 'flags',
      component: FlagBrowserView
    },
    {
      path: '/submit',
      name: 'submit',
      component: ManualSubmissionView
    }
  ]
})

export default router
