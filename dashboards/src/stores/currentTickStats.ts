import { defineStore } from 'pinia';
import { ref } from 'vue';
import axios from 'axios';

export interface CurrentTickStats {
  queued: number;
  discarded: number;
  accepted: number;
  rejected: number;
  accepted_delta: number;
  rejected_delta: number;
}

export const useCurrentTickStatsStore = defineStore('currentTickStats', () => {
  const stats = ref<CurrentTickStats | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function fetchStats() {
    isLoading.value = true;
    error.value = null;

    try {
      const apiUrl = `${import.meta.env.VITE_API_URL}/stats/current-tick`;
      console.log(`Fetching game stats from: ${apiUrl}`);

      const response = await axios.get<CurrentTickStats>(apiUrl, { withCredentials: true });
      if (stats.value) {
        stats.value = { ...response.data, discarded: stats.value.discarded ?? 0 };
      } else {
        stats.value = { ...response.data, discarded: 0 };
      }
      console.log('Game Stats fetched:', stats.value);
    } catch (err: any) {
      console.error('Error fetching game stats:', err);
      error.value = err.message || 'An unknown error occurred while fetching game stats';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  function incrementQueued(delta: number = 1) {
    if (stats.value) {
      stats.value.queued += delta;
    } else {
      console.warn("Attempted to increment 'queued' but stats object is null.");
    }
  }

  function incrementDiscarded(delta: number = 1) {
    console.debug("Incrementing discarded by", delta);

    if (stats.value) {
      stats.value.discarded += delta;
    } else {
      console.warn("Attempted to increment 'discarded' but stats object is null.");
    }
  }

  function incrementAccepted(delta: number = 1) {
    if (stats.value) {
      stats.value.accepted += delta;
      stats.value.accepted_delta += delta;
    } else {
      console.warn("Attempted to increment 'accepted' but stats object is null.");
    }
  }

  function incrementRejected(delta: number = 1) {
    if (stats.value) {
      stats.value.rejected += delta;
      stats.value.rejected_delta += delta;
    } else {
      console.warn("Attempted to increment 'rejected' but stats object is null.");
    }
  }

  function resetDiscarded() {
    if (stats.value) {
      stats.value.discarded = 0;
    } else {
      console.warn("Attempted to reset 'discarded' but stats object is null.");
    }
  }

  return {
    stats,
    isLoading,
    error,
    fetchStats,
    incrementQueued,
    incrementDiscarded,
    incrementAccepted,
    incrementRejected,
    resetDiscarded
  };
});
