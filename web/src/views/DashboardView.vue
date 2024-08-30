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

const exploitsStats = ref([])

const aborter = new AbortController()

function resetDashboardStats() {
  queuedCount.value = 0
  duplicatesCount.value = 0
  acceptedCount.value = 0
  rejectedCount.value = 0
}

async function fetchLatestDashboardStats() {
  try {
    const response = await axios.get(`${import.meta.env.VITE_API_URL}/stats/dashboard`, {
      withCredentials: true
    })
    const data = response.data
    acceptedCount.value += data.accepted
    rejectedCount.value += data.rejected
    queuedCount.value += data.queued
  } catch (error) {
    console.error('Error fetching dashboard stats:', error)
  }
}

function updateDashboardStats(chunk) {
  const data = JSON.parse(chunk)
  
  queuedCount.value += data.queued
  duplicatesCount.value += data.discarded
  acceptedCount.value += data.accepted
  rejectedCount.value += data.rejected

  if (data.exploit) {
    const targetExploit = exploitsStats.value.find((exploit) => exploit.name === data.exploit)
    if (targetExploit) {
      if (!targetExploit.currentTick.targets) {
        targetExploit.currentTick.targets = new Set()
      }

      targetExploit.currentTick.retrieved += data.queued
      targetExploit.currentTick.duplicates += data.discarded
      targetExploit.currentTick.targets.add(data.target)
    }
  }

}

function updateRabbitStats(chunk) {
  const data = JSON.parse(chunk)
  
  retrievalRate.value = data.retrieved_per_second;
  
  retrievalHistory.value.push({
    sample: data.retrieved_per_second,
    timestamp: data.timestamp
  });
  
  if (retrievalHistory.value.length > 60) {
    retrievalHistory.value.shift();
  }
  
  submissionRate.value = data.submitted_per_second;
  
  submissionHistory.value.push({
    sample: data.submitted_per_second,
    timestamp: data.timestamp
  });
  
  if (submissionHistory.value.length > 60) {
    submissionHistory.value.shift();
  }
}

function consumeFlagEventStream() {
  const streamUrl = `${import.meta.env.VITE_API_URL}/stats/stream/flags`

  const eventSource = new EventSource(streamUrl, { withCredentials: true })

  eventSource.onmessage = (event) => {
    updateDashboardStats(event.data)
  }

  eventSource.onerror = (error) => {
    console.error('Error processing the event stream:', error)
    eventSource.close()
  }
}

function consumeRabbitEventStream() {
  const streamUrl = `${import.meta.env.VITE_API_URL}/stats/stream/rabbit`

  const eventSource = new EventSource(streamUrl, { withCredentials: true })

  eventSource.onmessage = (event) => {
    updateRabbitStats(event.data)
  }

  eventSource.onerror = (error) => {
    console.error('Error processing the event stream:', error)
    eventSource.close()
  }
}

async function fetchExploitStats() {
  try {
    const response = await axios.get(
      `${import.meta.env.VITE_API_URL}/stats/exploits`,
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

watch(tickNumber, () => {
  resetDashboardStats()
  fetchLatestDashboardStats()
  fetchExploitStats()
})

onMounted(() => {
  consumeFlagEventStream()
  consumeRabbitEventStream()
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
      />
      <ValueCard
        icon="ri:close-fill"
        title="Rejected"
        :number="rejectedCount"
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
        :data="submissionHistory.map((obj) => obj.sample) || [0, 0]"
        :labels="submissionHistory.map((obj) => obj.timestamp) || [0, 0]"
      />
    </div>

    <div class="columns-2" style="margin-top: 40px; margin-bottom: 40px">
      <div class="column">
        <h2>
          Exploits
          <Icon icon="ri:sword-line" />
        </h2>
        <div v-if="!exploitsStats.length" class="empty-exploits">
          <Icon icon="mdi:dinosaur-pixel" />
          <p>No exploits yet</p>
        </div>
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

.empty-exploits {
  text-align: center;
  color: #6b6b6b;
}

.empty-exploits .iconify {
  font-size: 72px;
}

.empty-exploits p {
  margin: 0;
}

@media (max-width: 500px) {
  .column {
    flex: 1 1 100%;
  }
}
</style>
