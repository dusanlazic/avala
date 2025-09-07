// src/stores/filters.ts
import { defineStore } from 'pinia';
import { ref } from 'vue';

type StatusFilter = 'accepted' | 'rejected' | 'queued' | 'all';
type TickRangeFilter = '0' | '4' | '9' | '29' | 'all';

export const useFilterStore = defineStore('filters', () => {
  const selectedStatus = ref<StatusFilter>('all');
  const selectedExploit = ref<string>('all');
  const tickRange = ref<TickRangeFilter>('0');

  function setStatus(status: StatusFilter) {
    selectedStatus.value = status;
  }

  function setExploit(exploit: string) {
    selectedExploit.value = exploit;
  }

  function setTickRange(range: TickRangeFilter) {
    tickRange.value = range;
  }

  function resetFilters() {
    selectedStatus.value = 'all';
    selectedExploit.value = 'all';
    tickRange.value = '0';
  }

  return {
    selectedStatus,
    selectedExploit, // This will hold the currently selected dynamic exploit string
    tickRange,
    setStatus,
    setExploit,
    setTickRange,
    resetFilters,
  };
});
