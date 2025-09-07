<script setup lang="ts">
import { useConfigStore } from '@/stores/config';
import { inject, onMounted, ref, type Ref } from 'vue';

const configStore = useConfigStore();

const elapsed = ref(0);
const tickNumber = inject<Ref<number>>('tickNumber');

function startTicking() {
  const update = () => {
    if (configStore.config?.schedule) {
      const gameStart = Date.parse(configStore.config?.schedule.first_tick_start.replace(' ', 'T'))
      elapsed.value = Math.floor(((Date.now() - gameStart) / 1000) % configStore.config?.schedule.tick_duration)

      if (tickNumber) {
        tickNumber.value = Math.floor((Date.now() - gameStart) / (configStore.config?.schedule.tick_duration * 1000)) + 1;
      }
    }
  }

  update();
  setInterval(update, 50);
}

onMounted(() => {
  startTicking();
});
</script>

<template>
  <div class="progress-wrapper">
    <div class="tick-progress"
      :style="{ width: configStore.config?.schedule?.tick_duration ? ((elapsed + 1) / configStore.config.schedule.tick_duration) * 100 + '%' : '0%' }">
    </div>
  </div>
</template>

<style scoped>
.progress-wrapper {
  width: 100%;
  height: 6px;
  background-color: #313131;
}

.tick-progress {
  height: 100%;
  background-color: #ef233c;
  transition: width 0.2s ease;
}
</style>
