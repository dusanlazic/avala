<script setup>
import { ref, provide } from 'vue'
import { Icon } from '@iconify/vue'
import TickProgress from '@/components/TickProgress.vue'
import DashboardView from '@/views/DashboardView.vue'
import FlagBrowserView from '@/views/FlagBrowserView.vue'
import ManualSubmissionView from '@/views/ManualSubmissionView.vue'

const tickNumber = ref(0)
const totalTicks = ref(0)
const networkOpenTick = ref(0)

provide('tickNumber', tickNumber)
provide('totalTicks', totalTicks)
provide('networkOpenTick', networkOpenTick)

const currentView = ref('dashboard')

const showView = (view) => {
  currentView.value = view
}
</script>

<template>
  <TickProgress />
  <div class="container">
    <header>
      <nav>
        <a
          href="#"
          :class="{ 'router-link-active': currentView === 'dashboard' }"
          @click.prevent="showView('dashboard')"
        >
          <Icon icon="ri:dashboard-3-line" /> Dashboard
        </a>
        <a
          href="#"
          :class="{ 'router-link-active': currentView === 'flags' }"
          @click.prevent="showView('flags')"
        >
          <Icon icon="ri:flag-line" /> Browse Flags
        </a>
        <a
          href="#"
          :class="{ 'router-link-active': currentView === 'submit' }"
          @click.prevent="showView('submit')"
        >
          <Icon icon="ri:cursor-line" /> Manual Submit
        </a>
        <div class="divider"></div>
      </nav>
    </header>
    <div class="spacing"></div>
    <div v-show="currentView === 'dashboard'">
      <DashboardView />
    </div>
    <div v-show="currentView === 'flags'">
      <FlagBrowserView />
    </div>
    <div v-show="currentView === 'submit'">
      <ManualSubmissionView />
    </div>
  </div>
</template>

<style scoped>
.container {
  width: 100%;
  max-width: 1344px;
  margin: 0 auto;
}

header {
  position: fixed;
  z-index: 4;
  background-image: linear-gradient(to bottom, #131313 0%, transparent 100%);
  width: 100%;
}

nav {
  display: flex;
  gap: 2.5rem;
  padding: 36px 0;
}

nav a {
  color: #6b6b6b;
  text-decoration: none;
  font-size: 18px;
  font-weight: 500;
  display: flex;
  align-items: center;
  gap: 9px;
}

nav a:hover {
  color: #c4c4c4;
}

nav a.router-link-active {
  color: #ef233c;
}

nav a .iconify {
  font-size: 24px;
  padding-bottom: 3px;
}

nav .divider {
  margin-left: auto;
}

.spacing {
  height: 100px;
}
</style>
