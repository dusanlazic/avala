<script setup>
import { ref, provide, reactive, onMounted, inject } from 'vue'
import axios from 'axios'

const tickNumber = inject('tickNumber')
const totalTicks = inject('totalTicks')
const networkOpenTick = inject('networkOpenTick')

const elapsed = ref(0)
const duration = ref(0)
const gameStart = ref(0)

async function fetchData() {
  try {
    const response = await axios.get(`${import.meta.env.VITE_API_URL}/connect/schedule`, {
      withCredentials: true
    })
    const data = response.data
    gameStart.value = Date.parse(response.data.first_tick_start.replace(' ', 'T'))
    duration.value = data.tick_duration
    networkOpenTick.value = data.network_open_tick
    totalTicks.value = data.total_ticks
  } catch (error) {
    console.error('Error fetching data:', error)
  }
}

function startTicking() {
  const update = () => {
    if (gameStart.value === 0) return

    const now = Date.now()
    elapsed.value = Math.floor(((now - gameStart.value) / 1000) % duration.value)
    tickNumber.value = Math.ceil((now - gameStart.value) / 1000 / duration.value)
  }

  update()
  setInterval(update, 50)
}

onMounted(() => {
  fetchData()
  startTicking()
})
</script>

<template>
  <div class="progress-wrapper">
    <div class="tick-progress" :style="{ width: ((elapsed + 1) / duration) * 100 + '%' }"></div>
  </div>
</template>

<style scoped>
.progress-wrapper {
  width: 100%;
  height: 6px;
  background-color: #313131;
  position: fixed;
  top: 0;
  z-index: 5;
}

.tick-progress {
  height: 100%;
  background-color: #ef233c;
  transition: width 0.2s ease;
}
</style>
