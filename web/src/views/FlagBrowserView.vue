<script setup>
import { ref, onMounted, inject, watch, reactive } from 'vue'
import { Icon } from '@iconify/vue'
import ValueCard from '@/components/ValueCard.vue'
import axios from 'axios'

const tickNumber = inject('tickNumber')

const flagsInCurrentTick = ref(0)
const flagsInLastTick = ref(0)
const flagsManuallyAdded = ref(0)
const flagsTotal = ref(0)

const searchQuery = ref('')
const pageNumber = ref(1)
const displayPerPage = ref(25)

const searchResults = ref([])
const resultsMetadata = ref({
  paging: {
    current: 0,
    hasNext: false,
    hasPrev: false,
    last: 0
  },
  results: {
    executionTime: 0,
    fetched: 0,
    total: 0
  }
})

const errorMessage = ref('')
const searchBar = ref(null)

async function fetchDatabaseStats() {
  try {
    const response = await axios.get(`${import.meta.env.VITE_API_URL}/flags/db-stats`, {
      withCredentials: true
    })
    const data = response.data
    flagsInCurrentTick.value = data.current_tick
    flagsInLastTick.value = data.last_tick
    flagsManuallyAdded.value = data.manual
    flagsTotal.value = data.total
  } catch (error) {
    console.error('Error fetching exploit stats:', error)
  }
}

async function performSearch() {
  try {
    const response = await axios.get(`${import.meta.env.VITE_API_URL}/flags/search`, {
      params: {
        query: searchQuery.value || 'tick >= -1',
        page: pageNumber.value,
        show: displayPerPage.value,
        sort: 'timestamp desc'
      },
      withCredentials: true
    })
    searchResults.value = response.data.results
    resultsMetadata.value = response.data.metadata

    errorMessage.value = ''
  } catch (error) {
    if (error.response) {
      errorMessage.value = error.response.data.detail || 'An error occurred on the server.'
    } else if (error.request) {
      errorMessage.value =
        'No response was received from the server. Please check your network connection.'
    } else {
      errorMessage.value = 'An error occurred while setting up the request: ' + error.message
    }

    searchResults.value = []
  }
}

const nextPage = () => {
  pageNumber.value++
  performSearch()
}

const prevPage = () => {
  pageNumber.value--
  performSearch()
}

const predefinedQuery = (dial) => {
  searchBar.value.focus()
  switch (dial) {
    case 1:
      searchQuery.value = `tick is ${tickNumber.value}`
      break
    case 2:
      searchQuery.value = `tick is ${tickNumber.value - 1}`
      break
    case 3:
      searchQuery.value = 'target is unknown and exploit is manual'
      break
    default:
      searchQuery.value = ''
  }
  fetchDatabaseStats()
  pageNumber.value = 1
  performSearch()
}

watch(tickNumber, () => {
  fetchDatabaseStats()
})

onMounted(() => {
  fetchDatabaseStats()
})
</script>

<template>
  <main>
    <div class="sticky">
      <h2>
        Browse Flags
        <Icon icon="ri:flag-line" />
      </h2>
      <div class="grid-container column-300">
        <ValueCard
          icon="ri:timer-line"
          title="Current tick"
          :number="flagsInCurrentTick"
          @click="predefinedQuery(1)"
        />
        <ValueCard
          icon="ri:history-fill"
          title="Last tick"
          :number="flagsInLastTick"
          @click="predefinedQuery(2)"
        />
        <ValueCard
          icon="ri:cursor-line"
          title="Manually submitted"
          :number="flagsManuallyAdded"
          @click="predefinedQuery(3)"
        />
        <ValueCard
          icon="ri:database-2-fill"
          title="Total flags"
          :number="flagsTotal"
          @click="predefinedQuery(4)"
        />
      </div>
      <input
        class="search-bar"
        ref="searchBar"
        type="text"
        placeholder="target == 10.10.4.3 and tick > 94"
        v-model="searchQuery"
        @keyup.enter="performSearch"
      />
      <div class="search-controls">
        <span>Flags per page</span>
        <select v-model="displayPerPage" @change="performSearch">
          <option>25</option>
          <option>50</option>
          <option>100</option>
        </select>
        <span style="margin-left: 15px">
          Showing {{ resultsMetadata.results.fetched }} out of
          {{ resultsMetadata.results.total }} results ({{
            resultsMetadata.results.executionTime.toFixed(3)
          }}s)
        </span>
        <div class="divider"></div>
        <button class="prev" :disabled="pageNumber === 1" @click="prevPage">
          <Icon icon="ri:arrow-drop-left-fill" :inline="true" />
          Prev
        </button>
        <input type="number" v-model="pageNumber" @change="performSearch" />
        <span>out of {{ resultsMetadata.paging.last }} pages</span>
        <button class="next" :disabled="!resultsMetadata.paging.hasNext" @click="nextPage">
          Next
          <Icon icon="ri:arrow-drop-right-fill" :inline="true" />
        </button>
      </div>
    </div>
    <div class="results">
      <table>
        <thead>
          <tr>
            <th class="tick">tick</th>
            <th class="timestamp">timestamp</th>
            <th class="player">player</th>
            <th class="exploit">exploit</th>
            <th class="target">target</th>
            <th class="status">status</th>
            <th class="value">value</th>
            <th class="response">response</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="errorMessage" style="color: #ef233c">
            <td colspan="8">{{ errorMessage }}</td>
          </tr>
          <tr v-for="result in searchResults" :key="result.id">
            <td class="tick">{{ result.tick }}</td>
            <td class="timestamp">{{ result.timestamp.split('T')[1].split('.')[0] }}</td>
            <td class="player">{{ result.player }}</td>
            <td class="exploit">{{ result.exploit }}</td>
            <td class="target">{{ result.target }}</td>
            <td class="status">{{ result.status }}</td>
            <td class="value">{{ result.value }}</td>
            <td class="response">{{ result.response }}</td>
          </tr>
        </tbody>
      </table>
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

.grid-container.column-300 {
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
}

.search-bar {
  width: 100%;
  font-family: 'Fira Code', monospace;
  font-size: 13pt;
  height: 40px;
  color: #afafaf;
  background-color: #181818;
  border: 1px solid #313131;
  padding: 0px 13px;
  box-sizing: border-box;
}

.search-bar:focus {
  outline: none;
  border-color: #ef233c;
}

.search-controls {
  display: flex;
  gap: 10px;
  margin-top: 14px;
  font-size: 12px;
  font-weight: 600;
  align-items: center;
  color: #6b6b6b;
}

.search-controls .divider {
  margin-left: auto;
}

.search-controls select {
  font-family: 'Fira Code', monospace;
  font-size: 12px;
  padding: 5px;
  background-color: #181818;
  border: 1px solid #313131;
  color: #afafaf;
}

.search-controls select:focus {
  outline: none;
  border-color: #ef233c;
}

.search-controls input {
  font-family: 'Fira Code', monospace;
  font-size: 12px;
  padding: 5px;
  background-color: #181818;
  border: 1px solid #313131;
  color: #afafaf;
  width: 40px;
  text-align: center;
  box-sizing: border-box;
}

.search-controls input:focus {
  outline: none;
  border-color: #ef233c;
}

.search-controls button {
  font-family: 'Fira Code', monospace;
  font-size: 12px;
  padding: 5px 10px;
  background-color: #181818;
  border: 1px solid #313131;
  color: #afafaf;
  overflow: hidden;
  position: relative;
  width: 70px;
}

.search-controls button.prev {
  text-align: right;
}

.search-controls button.next {
  text-align: left;
}

.search-controls button:hover {
  background-color: #1f1f1f;
  cursor: pointer;
}

.search-controls button .iconify {
  font-size: 30px;
  position: absolute;
  top: -3px;
}

.search-controls button.prev .iconify {
  left: 0px;
}

.search-controls button.next .iconify {
  right: 0px;
}

.search-controls button:disabled {
  background-color: #181818;
  border: 1px solid #181818;
  cursor: not-allowed;
  color: #6b6b6b;
}

input::-webkit-outer-spin-button,
input::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

input[type='number'] {
  -moz-appearance: textfield;
}

.results {
  width: 100%;
  height: 55vh;
  overflow-y: scroll;
  scrollbar-width: thin;
  position: relative;
  margin-top: 20px;
}

table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  table-layout: fixed;
  margin-top: 0;
}

thead {
  position: sticky;
  top: 0;
  z-index: 1;
  background-color: #131313;
}

thead tr {
  border: 0px !important;
}

th,
td {
  padding: 5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

td {
  font-weight: 500;
}

tr {
  color: #6b6b6b;
}

tr:hover {
  color: #c4c4c4;
  background-color: #181818;
}

tr:hover td {
  word-wrap: break-word;
  white-space: normal;
  overflow: visible;
}

th {
  text-align: left;
  color: #6b6b6b;
  border-bottom: 1px solid #313131;
}

td.tick,
th.tick {
  width: 6%;
}

td.timestamp,
th.timestamp {
  width: 12%;
}

td.player,
th.player {
  width: 12%;
}

td.exploit,
th.exploit {
  width: 10%;
}

td.target,
th.target {
  width: 12%;
}

td.status,
th.status {
  width: 8%;
}

td.value,
th.value {
  width: 20%;
}

td.response,
th.response {
  width: 20%;
}
</style>
