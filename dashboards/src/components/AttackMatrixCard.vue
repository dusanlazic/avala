<script setup lang="ts">
import { useFilterStore } from '@/stores/filters';
import { useAttackStatsStore } from '@/stores/attackStats';
import { computed, inject, ref, watch, onMounted, type Ref } from 'vue';
import axios from 'axios';

const filterStore = useFilterStore();
const attackStatsStore = useAttackStatsStore();

const heatmapValues = ref<number[][] | null>(null);
const isLoadingHeatmap = ref(false);
const heatmapError = ref<string | null>(null);

const tickNumber = inject<Ref<number>>('tickNumber');
const refreshTrigger = inject<Ref<number>>('refreshTrigger');

const calculateCellColor = (value: number) => {
  const flatValues = heatmapValues.value?.flat() || [];
  if (flatValues.length === 0) {
    return 'rgb(33, 33, 33)';
  }

  const maxValue = Math.max(...flatValues);
  const minValue = Math.min(...flatValues);

  if (value === 0) {
    return 'rgb(33, 33, 33)';
  }

  const ratio = (maxValue === minValue) ? 0 : (value - minValue) / (maxValue - minValue);
  const red = Math.round(33 + ratio * (239 - 33));
  const green = Math.round(33 + ratio * (35 - 33));
  const blue = Math.round(33 + ratio * (60 - 33));

  return `rgb(${red}, ${green}, ${blue})`;
};

const fetchHeatmapValues = async () => {
  isLoadingHeatmap.value = true;
  heatmapError.value = null;

  try {
    const params = new URLSearchParams();

    if (filterStore.selectedStatus !== 'all') {
      params.append('status', filterStore.selectedStatus);
    }

    if (filterStore.selectedExploit !== 'all') {
      params.append('exploit', filterStore.selectedExploit);
    }

    if (filterStore.tickRange !== 'all') {
      params.append('last_n_ticks', filterStore.tickRange);
    }

    const apiUrl = `${import.meta.env.VITE_API_URL}/stats/attack-heatmap?${params.toString()}`;
    console.log(`Fetching attack heatmap from: ${apiUrl}`);

    const response = await axios.get<number[][]>(apiUrl, { withCredentials: true });
    heatmapValues.value = response.data;
    console.log('Attack heatmap fetched:', heatmapValues.value);

  } catch (error: any) {
    console.error('Error fetching attack heatmap:', error);
    heatmapError.value = error.message || 'Failed to fetch attack heatmap.';
  } finally {
    isLoadingHeatmap.value = false;
  }
};

watch(
  [
    tickNumber,
    refreshTrigger,
    () => filterStore.selectedStatus,
    () => filterStore.selectedExploit,
    () => filterStore.tickRange
  ],
  () => {
    fetchHeatmapValues();
  },
  {
    immediate: true
  }
);

onMounted(() => {
  if (!attackStatsStore.hosts || !attackStatsStore.services) {
    attackStatsStore.fetchAllAttackStats();
  }
});
</script>

<template>
  <div class="card">
    <div class="card-body">
      <div class="matrix">
        <div class="matrix-row">
          <div class="matrix-cell fixed-width-host"
            style="background-color: transparent; width: 60px; margin-right: 5px;"></div>
          <div v-for="service in attackStatsStore.services" :key="service" class="matrix-cell">
            {{ service }}
          </div>
        </div>

        <template v-if="attackStatsStore.hosts && heatmapValues">
          <div v-for="(host, hostIndex) in attackStatsStore.hosts" :key="host" class="matrix-row">
            <div class="matrix-cell fixed-width-host" style="width: 60px; text-align: left; margin-right: 5px;">
              {{ host }}
            </div>
            <div v-for="(service, serviceIndex) in attackStatsStore.services" :key="service" class="matrix-cell"
              :style="{ backgroundColor: calculateCellColor(heatmapValues[hostIndex]?.[serviceIndex] ?? 0) }">
              <span class="tooltip">
                Host: {{ host }}<br />
                Service: {{ service }}<br />
                <b>{{ heatmapValues[hostIndex]?.[serviceIndex] ?? 'N/A' }}</b> flags {{ filterStore.selectedStatus }}
              </span>
            </div>
          </div>
        </template>
        <div v-else-if="isLoadingHeatmap">
          Loading heatmap...
        </div>
        <div v-else-if="heatmapError">
          Error loading attack matrix: {{ heatmapError }}
        </div>
        <div v-else>
          <p>No data :(</p>
        </div>
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
        <select v-model="filterStore.tickRange">
          <option value="0">Current tick</option>
          <option value="4">Last 5 ticks</option>
          <option value="9">Last 10 ticks</option>
          <option value="29">Last 30 ticks</option>
          <option value="all">All ticks</option>
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
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.875rem;
  color: #aaa;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.matrix {
  display: flex;
  flex-direction: column;
  gap: 0px;
  width: 100%;
}

.matrix-row {
  display: flex;
  gap: 0px;
  width: 100%;
}

.matrix-cell {
  position: relative;
  height: 12px;
  background-color: transparent;
  margin: 0;
  color: #ffffff59;
  font-size: 10px;
  transition: background-color 100ms linear;
  flex: 1;
  min-width: 0;
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  word-break: break-all;
}

.matrix-cell.fixed-width-host {
  width: 60px;
  flex-shrink: 0;
  text-align: left;
  justify-content: flex-start;
}

.tooltip {
  visibility: hidden;
  position: absolute;
  top: 15px;
  left: 50%;
  transform: translateX(-50%);
  margin-bottom: 5px;
  background-color: #181818;
  border: 1px solid #313131;
  color: #ffffff;
  text-align: center;
  padding: 10px;
  font-size: 12px;
  white-space: nowrap;
  z-index: 10;
  opacity: 0;
}

.matrix-cell:hover {
  box-shadow: inset 0px 0px 0px 1px #aaaaaa75
}

.matrix-cell:hover .tooltip {
  visibility: visible;
  opacity: 1;
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
</style>
