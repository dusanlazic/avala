import { defineStore } from 'pinia';
import { ref } from 'vue';
import axios from 'axios';

export interface GameStats {
  queued: number;
  accepted: number;
  rejected: number;
  accepted_previous_tick: number;
  rejected_previous_tick: number;
}

export const useGameStatsStore = defineStore('gameStats', () => {
  const stats = ref<GameStats | null>(null);
  const isLoading = ref(false);
  const error = ref<string | null>(null);

  async function fetchStats() {
    isLoading.value = true;
    error.value = null;

    try {
      const apiUrl = `${import.meta.env.VITE_API_URL}/stats/totals`;
      console.log(`Fetching game stats from: ${apiUrl}`);

      const response = await axios.get<GameStats>(apiUrl, { withCredentials: true });

      stats.value = response.data;
      console.log('Game Stats fetched:', stats.value);

    } catch (err: any) {
      console.error('Error fetching game stats:', err);
      error.value = err.message || 'An unknown error occurred while fetching game stats';
      throw err;
    } finally {
      isLoading.value = false;
    }
  }

  return {
    stats,
    isLoading,
    error,
    fetchStats,
  };
});
