import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from '../views/DashboardView.vue'
import ExploitsView from '@/views/ExploitsView.vue'
import FlagsView from '@/views/FlagsView.vue'


const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      name: 'dashboard',
      component: DashboardView,
    },
    {
      path: '/exploits',
      name: 'exploits',
      component: ExploitsView,
    },
    {
      path: '/flags',
      name: 'flags',
      component: FlagsView,
    },
  ],
})

export default router
