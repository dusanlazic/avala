<script setup lang="ts">
import { useConfigStore } from '@/stores/config';
import { useFilterStore } from '@/stores/filters'
import { useAttackStatsStore } from '@/stores/attackStats';
import { computed, inject, ref, watch, type Ref } from 'vue'
import axios from 'axios';

const filterStore = useFilterStore();
const configStore = useConfigStore();
const attackStatsStore = useAttackStatsStore();

const tickNumber = inject<Ref<number>>('tickNumber');
const refreshTrigger = inject<Ref<number>>('refreshTrigger');

const timelineValues = ref<number[]>([]);

const calculateCellColor = (value: number) => {
  if (timelineValues.value.length === 0) {
    return 'rgb(33, 33, 33)'; // Default color if no data
  }

  const maxValue = Math.max(...timelineValues.value)
  const minValue = Math.min(...timelineValues.value)

  if (value === 0) {
    return 'rgb(33, 33, 33)'
  }

  const ratio = (maxValue === minValue) ? 0 : (value - minValue) / (maxValue - minValue);
  const red = Math.round(33 + ratio * (239 - 33))
  const green = Math.round(33 + ratio * (35 - 33))
  const blue = Math.round(33 + ratio * (60 - 33))

  return `rgb(${red}, ${green}, ${blue})`
}

const fetchTimelineValues = async () => {
  try {
    const params = new URLSearchParams();

    if (filterStore.selectedStatus !== 'all') {
      params.append('status', filterStore.selectedStatus);
    }

    if (filterStore.selectedExploit !== 'all') {
      params.append('exploit', filterStore.selectedExploit);
    }

    const apiUrl = `${import.meta.env.VITE_API_URL}/stats/tick-graph?${params.toString()}`;
    console.log(`Fetching tick graph from: ${apiUrl}`);

    const response = await axios.get<number[]>(apiUrl, { withCredentials: true });
    timelineValues.value = response.data;
    console.log('Timeline values fetched:', timelineValues.value);

  } catch (error: any) {
    console.error('Error fetching timeline values:', error);
  }
}

watch([tickNumber, refreshTrigger, () => filterStore.selectedStatus, () => filterStore.selectedExploit], () => {
  fetchTimelineValues();
}, { immediate: true });
</script>

<template>
  <div class="card">
    <div class="card-body">
      <div class="timeline">
        <span v-for="n in configStore.config?.schedule.total_ticks" :key="n" class="timeline-square" :class="{
          'timeline-square-current': n === tickNumber,
          'timeline-square-networks-open': n === configStore.config?.schedule.network_open_tick
        }" :style="{ backgroundColor: calculateCellColor(timelineValues[n]) }">
          <span class="tooltip">
            Tick {{ n }}<br /><b>{{ timelineValues[n] }}</b>
          </span>
        </span>
      </div>
      <div class="dropdown-container">
        <select v-model="filterStore.selectedStatus">
          <option value="accepted">Accepted</option>
          <option value="rejected">Rejected</option>
          <option value="queued">Queued</option>
          <option value="all">All statuses</option>
        </select>
        <select v-model="filterStore.selectedExploit">
          <option value="all">All exploits</option>
          <option v-for="exploit in attackStatsStore.exploits" :key="exploit" :value="exploit">
            {{ exploit }}
          </option>
        </select>
      </div>
    </div>
  </div>
</template>

<style scoped>
.card {
  position: relative;
  background-color: #181818;
  color: #fff;
  padding: 1.25rem;
  border-radius: 0px;
  border: 1px solid #313131;
  overflow: hidden;
  z-index: 0;
}

.card-header {
  font-size: 0.875rem;
  color: #aaa;
  margin-bottom: 0.5rem;
}

.card-header b {
  color: #ef233c;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.timeline {
  display: flex;
  flex-wrap: wrap;
  gap: 2px;
  justify-content: start;
  height: auto;
  width: 100%;
}

.timeline-square {
  position: relative;
  width: 12px;
  height: 12px;
  background-color: #ef233c;
  margin: 0;
  color: #ffffff59;
  transition: background-color 100ms linear;
}

.tooltip {
  visibility: hidden;
  position: absolute;
  top: 15px;
  left: 15px;
  background-color: #181818;
  border: 1px solid #313131;
  color: #ffffff;
  text-align: center;
  padding: 10px;
  font-size: 12px;
  white-space: nowrap;
  z-index: 1;
}

.timeline-square:hover .tooltip {
  visibility: visible;
}

.timeline-square:hover {
  box-shadow: inset 0px 0px 0px 1px #aaaaaa75
}

.timeline-square-current {
  -moz-animation: blink normal 0.5s infinite ease-in-out;
  -webkit-animation: blink normal 0.5s infinite ease-in-out;
  -ms-animation: blink normal 0.5s infinite ease-in-out;
  animation: blink normal 0.5s infinite ease-in-out;
}

.timeline-square-networks-open {
  box-shadow: inset 0px 0px 0px 1px rgb(255, 255, 255, 0.5);
}

.dropdown-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 15px;
  gap: 12px;
}

.dropdown-container select {
  padding: 5px;
  background-color: #181818;
  color: #aaaaaa;
  border: none;
  font-size: 12px;
  cursor: pointer;
}

.dropdown-container select:hover {
  background-color: #212121;
}

@keyframes blink {
  0% {
    box-shadow: inset 0px 0px 0px 1px #aaaaaa80
  }

  50% {
    box-shadow: inset 0px 0px 0px 1px #aaaaaa
  }

  100% {
    box-shadow: inset 0px 0px 0px 1px #aaaaaa80
  }
}
</style>
