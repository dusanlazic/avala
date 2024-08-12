<script setup>
import { ref, onMounted, onUnmounted, watch, inject } from 'vue'
import { Icon } from '@iconify/vue'
import ValueCard from '@/components/ValueCard.vue'
import ValueChartCard from '@/components/ValueChartCard.vue'
import ExploitCard from '@/components/ExploitCard.vue'
import Timeline from '@/components/Timeline.vue'
import axios from 'axios'

const tickNumber = inject('tickNumber')

const retrievalRate = ref(0)
const retrievalHistory = ref([])
const submissionRate = ref(0)
const submissionHistory = ref([])
const queuedCount = ref(0)
const duplicatesCount = ref(0)
const acceptedCount = ref(0)
const rejectedCount = ref(0)
const acceptedChange = ref(0)
const rejectedChange = ref(0)

const exploitsStats = ref([])

const aborter = new AbortController()

function refreshDashboardValues(chunk) {
  const data = JSON.parse(chunk)
  submissionRate.value = data.submission.rate
  submissionHistory.value = data.submission.history
  retrievalRate.value = data.retrieval.rate
  retrievalHistory.value = data.retrieval.history

  acceptedChange.value += data.accepted - acceptedCount.value
  rejectedChange.value += data.rejected - rejectedCount.value

  queuedCount.value = data.queued
  acceptedCount.value = data.accepted
  rejectedCount.value = data.rejected
}

function handleArrivingFlags(chunk) {
  const data = JSON.parse(chunk)
  duplicatesCount.value += data.duplicates

  let targetExploit = exploitsStats.value.find((exploit) => exploit.name === data.exploit)

  if (targetExploit) {
    if (!targetExploit.currentTick.targets) {
      targetExploit.currentTick.targets = new Set()
    }

    targetExploit.currentTick.retrieved += data.enqueued
    targetExploit.currentTick.duplicates += data.duplicates
    targetExploit.currentTick.targets.add(data.target)
  }
}

async function consumeLiveStats() {
  const streamUrl = `${import.meta.env.VITE_API_URL}/stats/subscribe`
  try {
    const response = await fetch(streamUrl, { signal: aborter.signal })

    if (!response.body) {
      console.error('Failed to get readable stream')
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let result = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      result += decoder.decode(value, { stream: true })
      const lines = result.split('\n')
      result = lines.pop()

      lines.forEach((line) => {
        if (line) refreshDashboardValues(line)
      })
    }
  } catch (error) {
    if (error.name === 'AbortError') {
    } else {
      console.error('Error processing the stream:', error)
    }
  }
}

async function fetchExploitStats() {
  try {
    const response = await axios.get(
      `${import.meta.env.VITE_API_URL}/stats/exploits/tick-summary`,
      {
        withCredentials: true
      }
    )
    exploitsStats.value = response.data.map((exploit) => ({
      ...exploit,
      currentTick: {
        retrieved: 0,
        duplicates: 0,
        targets: new Set()
      }
    }))
  } catch (error) {
    console.error('Error fetching exploit stats:', error)
  }
}

async function consumeArrivingFlags() {
  const streamUrl = `${import.meta.env.VITE_API_URL}/stats/flags/subscribe`
  try {
    const response = await fetch(streamUrl, { signal: aborter.signal })

    if (!response.body) {
      console.error('Failed to get readable stream')
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let result = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      result += decoder.decode(value, { stream: true })
      const lines = result.split('\n')
      result = lines.pop()

      lines.forEach((line) => {
        if (line) handleArrivingFlags(line)
      })
    }
  } catch (error) {
    if (error.name === 'AbortError') {
    } else {
      console.error('Error processing the stream:', error)
    }
  }
}

watch(tickNumber, () => {
  acceptedChange.value = 0
  rejectedChange.value = 0
  duplicatesCount.value = 0
  fetchExploitStats()
})

onMounted(() => {
  consumeLiveStats()
  consumeArrivingFlags()
  acceptedChange.value = 0
  rejectedChange.value = 0
  fetchExploitStats()
})

onUnmounted(() => {
  aborter.abort()
})
</script>

<template>
  <main>
    <h2>
      Statistics
      <Icon icon="ri:donut-chart-fill" />
    </h2>
    <div class="grid-container column-300">
      <ValueCard icon="ri:hourglass-2-fill" title="Queued" :number="queuedCount" />
      <ValueCard icon="ri:reset-left-fill" title="Duplicates" :number="duplicatesCount" />
      <ValueCard
        icon="ri:check-double-fill"
        title="Accepted"
        :number="acceptedCount"
        :change="acceptedChange"
      />
      <ValueCard
        icon="ri:close-fill"
        title="Rejected"
        :number="rejectedCount"
        :change="rejectedChange"
      />
    </div>

    <div class="grid-container column-500">
      <ValueChartCard
        icon="ri:speed-up-fill"
        title="Retrieval speed"
        :number="retrievalRate"
        :unit="'flags/s'"
        :data="retrievalHistory.map((obj) => obj.sample) || [0, 0]"
        :labels="retrievalHistory.map((obj) => obj.timestamp) || [0, 0]"
      />
      <ValueChartCard
        icon="ri:speed-up-fill"
        title="Submission speed"
        :number="submissionRate"
        :unit="'flags/s'"
        :data="retrievalHistory.map((obj) => obj.sample) || [0, 0]"
        :labels="retrievalHistory.map((obj) => obj.timestamp) || [0, 0]"
      />
    </div>

    <div class="columns-2" style="margin-top: 40px">
      <div class="column">
        <h2>
          Exploits
          <Icon icon="ri:sword-line" />
        </h2>
        <div class="grid-container column-200">
          <ExploitCard
            v-for="exploit in exploitsStats"
            :key="exploit.name"
            :title="exploit.name"
            :history="exploit.history"
            :retrieved="exploit.currentTick.retrieved"
            :duplicates="exploit.currentTick.duplicates"
            :targets="exploit.currentTick.targets"
          />
        </div>
      </div>
      <div class="column">
        <h2>
          Timeline
          <Icon icon="ri:time-line" />
        </h2>
        <Timeline />
      </div>
    </div>
  </main>
</template>

<style scoped>
h2 {
  margin: 0;
  font-weight: 600;
  margin-bottom: 20px;
  display: flex;
  gap: 10px;
}

h2 .iconify {
  font-size: 28px;
}

.grid-container {
  display: grid;
  gap: 20px;
  margin-bottom: 20px;
}

.grid-container.column-200 {
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
}

.grid-container.column-300 {
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
}

.grid-container.column-500 {
  grid-template-columns: repeat(auto-fill, minmax(500px, 1fr));
}

.columns-2 {
  display: flex;
  flex-wrap: wrap;
  gap: 20px;
}

.column {
  flex: 1 1 calc(50% - 10px);
  box-sizing: border-box;
}

@media (max-width: 500px) {
  .column {
    flex: 1 1 100%;
  }
}
</style>
