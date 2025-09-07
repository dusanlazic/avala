<script setup lang="ts">
import Card from '@/components/Card.vue';
import TimelineCard from '@/components/TimelineCard.vue';
import ExploitsTable from '@/components/ExploitsTable.vue';
import AttackMatrixCard from '@/components/AttackMatrixCard.vue';
import { Icon } from '@iconify/vue'
import { useConfigStore } from '@/stores/config';
import { useGameStatsStore } from '@/stores/gameStats';
import { useCurrentTickStatsStore } from '@/stores/currentTickStats';
import { inject, onMounted, watch, type Ref } from 'vue';

interface FlagUpdateMessage {
  host: string;
  service: string;
  exploit: string;
  status: 'queued' | 'accepted' | 'rejected' | 'discarded';
  delta: number;
}

const configStore = useConfigStore();
const gameStatsStore = useGameStatsStore();
const currentTickStatsStore = useCurrentTickStatsStore();

const tickNumber = inject<Ref<number>>('tickNumber');
const refreshTrigger = inject<Ref<number>>('refreshTrigger');

watch([tickNumber, refreshTrigger], () => {
  gameStatsStore.fetchStats();
  currentTickStatsStore.fetchStats();
})

watch(tickNumber, () => {
  currentTickStatsStore.resetDiscarded();
})
</script>

<template>
  <h2>
    <Icon icon="ri:bar-chart-fill" />
    Game stats
  </h2>
  <div class="card-grid">
    <Card title="Flags in queue" :value="gameStatsStore.stats?.queued ?? 0" icon="ri:flag-line" backgroundIcon />
    <Card title="Total accepted flags" :value="gameStatsStore.stats?.accepted ?? 0" icon="ri:check-double-fill"
      backgroundIcon :subtext="`${gameStatsStore.stats?.accepted_previous_tick ?? 0} in the previous tick`" />
    <Card title="Total rejected flags" :value="gameStatsStore.stats?.rejected ?? 0" icon="ri:close-line" backgroundIcon
      :subtext="`${gameStatsStore.stats?.rejected_previous_tick ?? 0} in the previous tick`" />
  </div>
  <h2>
    <Icon icon="ri:timer-flash-line" />
    Current tick — <b>{{ tickNumber }}</b> / {{ configStore.config?.schedule.total_ticks }}
  </h2>
  <div class="card-grid">
    <Card title="Queued flags" :value="currentTickStatsStore.stats?.queued ?? 0" icon="ri:flag-line" backgroundIcon />
    <Card title="Discarded (duplicate) flags" :value="currentTickStatsStore.stats?.discarded ?? 0"
      icon="ri:flag-off-line" backgroundIcon />
    <Card title="Accepted flags" :value="currentTickStatsStore.stats?.accepted ?? 0" icon="ri:check-double-fill"
      backgroundIcon
      :subtext="currentTickStatsStore.stats?.accepted_delta >= 0 ? `+${currentTickStatsStore.stats.accepted_delta} compared to the previous tick` : `${currentTickStatsStore.stats.accepted_delta} compared to the previous tick`" />
    <Card title="Rejected flags" :value="currentTickStatsStore.stats?.rejected ?? 0" icon="ri:close-line" backgroundIcon
      :subtext="currentTickStatsStore.stats?.rejected_delta >= 0 ? `+${currentTickStatsStore.stats.rejected_delta} compared to the previous tick` : `${currentTickStatsStore.stats.rejected_delta} compared to the previous tick`" />
  </div>
  <h2 style="display: grid; grid-template-columns: repeat(3, 1fr); align-items: center; text-align: left;">
    <span>
      <Icon icon="ri:sword-line" />
      Exploits
    </span>
    <span style="margin-left: 0.5rem;">
      <Icon icon="ri:fire-line" />
      Attack Heatmap
    </span>
    <span style="margin-left: 0.5rem;">
      <Icon icon="ri:time-line" />
      Timeline
    </span>
  </h2>
  <div class="card-grid">
    <ExploitsTable :tableData="[
      { type: 'manual', alias: 'Alpha', worker: 'Worker X', accepted: 15, rejected: 3, queued: 7, discarded: 2, targetHits: 5, acceptedLastTenTicks: [12, 25, 18, 30, 22, 5, 10, 20, 28, 35] },
      { type: 'worker', alias: 'Beta', worker: 'Worker Y', accepted: 9, rejected: 2, queued: 3, discarded: 1, targetHits: 4, acceptedLastTenTicks: [5, 10, 5, 20, 25, 30, 5, 40, 45, 50] },
      { type: 'manual', alias: 'Gamma', worker: 'Worker Z', accepted: 11, rejected: 4, queued: 5, discarded: 0, targetHits: 6, acceptedLastTenTicks: [8, 16, 24, 32, 40, 2, 20, 28, 36, 44] },
      { type: 'worker', alias: 'Delta', worker: 'Worker A', accepted: 13, rejected: 1, queued: 4, discarded: 3, targetHits: 2, acceptedLastTenTicks: [10, 20, 30, 40, 15, 5, 35, 5, 12, 22] },
      { type: 'manual', alias: 'Epsilon', worker: 'Worker B', accepted: 8, rejected: 5, queued: 6, discarded: 1, targetHits: 3, acceptedLastTenTicks: [7, 14, 21, 28, 35, 42, 10, 18, 26, 34] },
      { type: 'worker', alias: 'Zeta', worker: 'Worker C', accepted: 10, rejected: 2, queued: 8, discarded: 2, targetHits: 4, acceptedLastTenTicks: [9, 8, 27, 6, 45, 12, 24, 0, 40, 50] },
      { type: 'manual', alias: 'Eta', worker: 'Worker D', accepted: 14, rejected: 3, queued: 2, discarded: 0, targetHits: 7, acceptedLastTenTicks: [6, 2, 18, 24, 30, 36, 2, 48, 15, 25] },
      { type: 'worker', alias: 'Theta', worker: 'Worker E', accepted: 12, rejected: 1, queued: 5, discarded: 3, targetHits: 6, acceptedLastTenTicks: [11, 22, 33, 44, 10, 0, 30, 40, 5, 15] },
      { type: 'manual', alias: 'Iota', worker: 'Worker F', accepted: 7, rejected: 4, queued: 3, discarded: 1, targetHits: 2, acceptedLastTenTicks: [5, 10, 15, 20, 25, 30, 5, 4, 45, 50] }
    ]" />
    <AttackMatrixCard />
    <TimelineCard />
  </div>
</template>

<style scoped>
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
  gap: 1rem;
  align-items: start;
  width: 100%;
  margin-bottom: 1rem;
}

h2 {
  color: #aaaaaa;
  font-size: 10pt;
  font-weight: 400;
  margin-top: 0px;
  margin-bottom: 10px;
}

h2 .iconify {
  font-size: 18px;
  vertical-align: bottom;
  margin-right: 2px;
}
</style>
