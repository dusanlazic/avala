import { defineStore } from 'pinia';
import { ref } from 'vue';
import axios from 'axios';

interface ExploitTableEntry {
  exploit_name: string;
  unique_hosts_current_tick: number;
  flags_queued_current_tick: number;
  flags_accepted_current_tick: number;
  flags_rejected_current_tick: number;
  flags_accepted_last_10_ticks: number[];
}

export const useAttackStatsStore = defineStore('attackStats', () => {
  const hosts = ref<string[] | null>(null);
  const services = ref<string[] | null>(null);
  const exploits = ref<string[] | null>(null);
  const exploitsTable = ref<ExploitTableEntry[] | null>(null);

  async function fetchHosts() {
    try {
      const apiUrl = `${import.meta.env.VITE_API_URL}/stats/hosts`;
      console.log(`Fetching hosts from: ${apiUrl}`);
      const response = await axios.get<string[]>(apiUrl, { withCredentials: true });
      hosts.value = response.data;
      console.log('Hosts fetched:', hosts.value);
    } catch (error) {
      console.error('Error fetching hosts:', error);
      throw error;
    }
  }

  async function fetchServices() {
    try {
      const apiUrl = `${import.meta.env.VITE_API_URL}/stats/services`;
      console.log(`Fetching services from: ${apiUrl}`);
      const response = await axios.get<string[]>(apiUrl, { withCredentials: true });
      services.value = response.data;
      console.log('Services fetched:', services.value);
    } catch (error) {
      console.error('Error fetching services:', error);
      throw error;
    }
  }

  async function fetchExploits() {
    try {
      const apiUrl = `${import.meta.env.VITE_API_URL}/stats/exploits`;
      console.log(`Fetching exploits from: ${apiUrl}`);
      const response = await axios.get<string[]>(apiUrl, { withCredentials: true });
      exploits.value = response.data;
      console.log('Exploits fetched:', exploits.value);
    } catch (error) {
      console.error('Error fetching exploits:', error);
      throw error;
    }
  }

  async function fetchExploitsTable() {
    try {
      const apiUrl = `${import.meta.env.VITE_API_URL}/stats/exploits-table`;
      console.log(`Fetching exploits table from: ${apiUrl}`);
      const response = await axios.get<ExploitTableEntry[]>(apiUrl, { withCredentials: true });
      exploitsTable.value = response.data;
      console.log('Exploits table fetched:', exploitsTable.value);
    } catch (error) {
      console.error('Error fetching exploits table:', error);
      throw error;
    }
  }

  async function fetchAllAttackStats() {
    await Promise.all([
      fetchHosts(),
      fetchServices(),
      fetchExploits(),
      fetchExploitsTable(),
    ]);
  }


  return {
    hosts,
    services,
    exploits,
    exploitsTable,
    fetchHosts,
    fetchServices,
    fetchExploitsTable,
    fetchAllAttackStats,
  };
});
