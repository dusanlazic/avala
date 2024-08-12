<script setup>
import { ref, computed, onMounted, watch, inject, getCurrentInstance } from 'vue'
import axios from 'axios'
import { Icon } from '@iconify/vue'

const tickNumber = inject('tickNumber')
const totalTicks = inject('totalTicks')
const networkOpenTick = inject('networkOpenTick')

const pastTicks = ref([])

const nonZeroValues = computed(() => pastTicks.value.filter((value) => value !== 0))
const minVal = computed(() => Math.min(...nonZeroValues.value))
const maxVal = computed(() => Math.max(...nonZeroValues.value))

const calculateOpacity = (value, min, max) => (((value - min) / (max - min)) * 0.8 + 0.2).toFixed(2)

const cellBackgroundColor = (value) =>
  value === 0
    ? 'rgba(24, 24, 24, 1)'
    : `rgba(239, 35, 60, ${calculateOpacity(value, minVal.value, maxVal.value)})`

async function fetchTickStats() {
  try {
    const response = await axios.get(`${import.meta.env.VITE_API_URL}/flags/tick-stats`, {
      withCredentials: true
    })

    pastTicks.value = response.data.map((item) => item.accepted)
    getCurrentInstance().proxy.$forceUpdate()
  } catch (error) {
    console.error('Error fetching exploit stats:', error)
  }
}

const columnWidth = 17
const columnRows = 8
const finetune = 3

watch(tickNumber, () => {
  fetchTickStats()
  setTimeout(() => {
    fetchTickStats()
  }, 5000)
})

onMounted(() => {
  fetchTickStats()
})
</script>

<template>
  <div class="grid">
    <div
      v-for="index in totalTicks"
      :key="
        index === pastTicks.length
          ? 'current-' + index
          : index > pastTicks.length
            ? 'upcoming-' + index
            : 'old-' + index
      "
      class="cell tooltip"
      :class="{ live: index === pastTicks.length, empty: index > pastTicks.length }"
      :style="{
        backgroundColor: index <= pastTicks.length ? cellBackgroundColor(pastTicks[index - 1]) : ''
      }"
    >
      <span class="tooltiptext">
        Tick {{ index }}<br />
        {{
          index < pastTicks.length
            ? `${pastTicks[index - 1]} flags`
            : index === pastTicks.length
              ? '🔴 Current'
              : 'Upcoming'
        }}
      </span>
    </div>
  </div>
  <div class="markers">
    <span class="tooltip">
      <span class="tooltiptext">Game Start</span>
      <Icon icon="ri:rocket-2-fill" :style="{ left: '0%' }" />
    </span>
    <span class="tooltip">
      <span class="tooltiptext">Networks Open<br />(tick {{ networkOpenTick }})</span>
      <Icon
        icon="ri:boxing-fill"
        :style="{ left: Math.floor(networkOpenTick / columnRows) * columnWidth - finetune + 'px' }"
      />
    </span>
    <span class="tooltip">
      <span class="tooltiptext">Game End<br />(tick {{ totalTicks }})</span>
      <Icon
        icon="ri:flag-fill"
        :style="{ left: Math.floor(totalTicks / columnRows) * columnWidth - finetune + 'px' }"
      />
    </span>
  </div>
</template>

<style scoped>
.grid {
  display: grid;
  grid-template-rows: repeat(8, 13px);
  gap: 4px;
  grid-auto-flow: column;
  justify-content: start;
}

.cell {
  width: 13px;
  height: 13px;
  background-color: #ef233c;
  border-radius: 2px;
  position: relative;
}

.cell.empty {
  background-color: #181818;
}

.cell.live {
  -moz-animation: blink normal 1s infinite ease-in-out;
  -webkit-animation: blink normal 1s infinite ease-in-out;
  -ms-animation: blink normal 1s infinite ease-in-out;
  animation: blink normal 1s infinite ease-in-out;
}

@keyframes blink {
  0% {
    background-color: rgb(255, 255, 255, 0.1);
  }
  50% {
    background-color: rgba(255, 255, 255, 0.2);
  }
  100% {
    background-color: rgb(255, 255, 255, 0.1);
  }
}

.markers {
  color: #313131;
  height: 20px;
  position: relative;
}

.markers .iconify {
  font-size: 15px;
  width: 17px;
  position: absolute;
  bottom: 0px;
}

.markers .iconify:hover {
  color: white;
}
</style>
