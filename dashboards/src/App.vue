<script setup lang="ts">
import { RouterLink, RouterView } from 'vue-router'
import { Icon } from '@iconify/vue'
import TickProgress from './components/TickProgress.vue'
import { onMounted, onUnmounted, provide } from 'vue';
import { useConfigStore } from '@/stores/config';
import { ref } from 'vue';

const configStore = useConfigStore();
const tickNumber = ref(1);
const refreshTrigger = ref(1);

let refreshInterval: number | undefined;
const REFRESH_INTERVAL_MS = 3000; // 3 seconds

provide('tickNumber', tickNumber);
provide('refreshTrigger', refreshTrigger)

onMounted(() => {
  if (!configStore.config) {
    configStore.fetchConfig();
  }

  refreshInterval = setInterval(() => {
    refreshTrigger.value = refreshTrigger.value * -1;
    console.log('refreshTrigger flipped to:', refreshTrigger.value);
  }, REFRESH_INTERVAL_MS);
})

onUnmounted(() => {
  if (refreshInterval) {
    clearInterval(refreshInterval);
    console.log('Refresh trigger interval cleared.');
  }
});
</script>

<template>
  <TickProgress />
  <div class="app-container">
    <!-- <aside class="sidebar">
      <RouterLink to="/dashboard" class="nav-icon" title="Dashboard">
        <Icon icon="ri:dashboard-3-line" />
      </RouterLink>
      <RouterLink to="/exploits" class="nav-icon" title="Exploits">
        <Icon icon="ri:sword-line" />
      </RouterLink>
      <RouterLink to="/flags" class="nav-icon" title="Flags">
        <Icon icon="ri:flag-line" />
      </RouterLink>
    </aside> -->
    <main class="main-view">
      <RouterView />
    </main>
  </div>
</template>

<style scoped>
.app-container {
  display: flex;
  height: calc(100vh - 6px);
  width: 100vw;
}

.sidebar {
  width: 48px;
  background-color: #181818;
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 0.5rem 0;
  border-right: 1px solid #313131;
}

.nav-icon {
  margin: 1rem 0;
  color: #2b2b2b;
  display: flex;
  justify-content: center;
  align-items: center;
  margin: 2px;
  padding: 6px;
  border-radius: 100%;
}

.nav-icon:hover {
  color: #dddddd;
}

.nav-icon.router-link-exact-active {
  color: #dddddd;
  background-color: #404040;
}

.nav-icon :deep(svg) {
  width: 22px;
  height: 22px;
}

.main-view {
  flex: 1;
  padding: 1.5rem;
  overflow-y: auto;
}
</style>
