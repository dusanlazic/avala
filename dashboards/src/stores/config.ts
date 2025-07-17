import { defineStore } from 'pinia';
import { ref } from 'vue';
import axios from 'axios';

interface GameConfig {
  flag_format: string;
  own_team_hosts: string[];
  nop_team_hosts: string[];
  opp_team_hosts: string[];
}

interface ScheduleConfig {
  first_tick_start: string;
  tick_duration: number;
  network_open_tick: number;
  total_ticks: number;
}

export interface AppConfig {
  game: GameConfig;
  schedule: ScheduleConfig;
}

export const useConfigStore = defineStore('config', () => {
  const config = ref<AppConfig | null>(null);

  async function fetchConfig() {
    try {
      const response = await axios.get(import.meta.env.VITE_API_URL + '/configure', { withCredentials: true });
      config.value = response.data;
      console.log('Config fetched:', config.value);
    } catch (error) {
      console.error('Error fetching config:', error);
      throw error;
    }
  }

  return {
    config: config,
    fetchConfig
  }
})
