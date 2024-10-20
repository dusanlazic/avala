<script setup>
import { onMounted, ref } from 'vue'
import { Icon } from '@iconify/vue'
import axios from 'axios'

const flagFormat = ref(new RegExp('FLAG[a-z]{12}', 'g'))

const flagsInput = ref('')
const matchedFlags = ref([])

const submitting = ref(false)
const errorMessage = ref('')

const updateMatches = () => {
  matchedFlags.value = flagsInput.value.match(flagFormat.value) || []
}

async function submitFlags() {
  submitting.value = true

  try {
    const response = await axios.post(
      `${import.meta.env.VITE_API_URL}/flags/queue`,
      {
        values: matchedFlags.value,
        target: 'unknown',
        exploit: 'manual'
      },
      {
        withCredentials: true
      }
    )

    alert(
      `Successfully enqueued ${response.data.enqueued} flags. ${response.data.discarded} duplicates were discarded.`
    )
  } catch (error) {
    console.error('Error submitting flags:', error)
  }

  submitting.value = false
}

async function getFlagFormat() {
  try {
    const response = await axios.get(`${import.meta.env.VITE_API_URL}/connect/game`, {
      withCredentials: true
    })
    flagFormat.value = new RegExp(response.data.flag_format, 'g')
  } catch (error) {
    console.error('Error fetching flag format:', error)
  }
}

onMounted(() => {
  getFlagFormat()
})
</script>

<template>
  <main>
    <h2>
      Submit Flags Manually
      <Icon icon="ri:cursor-line" />
    </h2>
    <textarea
      placeholder="Paste text containing one or more flags"
      rows="20"
      v-model="flagsInput"
      @input="updateMatches()"
      spellcheck="false"
    ></textarea>

    <!-- <div class="flags">
      <div class="match" v-for="flag in matchedFlags" :key="flag">
        {{ flag }}
      </div>
    </div> -->

    <div class="flags">
      <table>
        <thead>
          <tr>
            <th class="flag">flag</th>
            <th class="response">response</th>
            <th class="status">status</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="errorMessage" style="color: #ef233c">
            <td colspan="8">{{ errorMessage }}</td>
          </tr>
          <tr v-for="flag in matchedFlags" :key="flag">
            <td class="flag">{{ flag }}</td>
            <td class="response"></td>
            <td class="status">matched</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="submit-controls">
      <button :disabled="matchedFlags.length === 0 || submitting" @click="submitFlags()">
        <span v-if="submitting">Pushing {{ matchedFlags.length }} flags...</span>
        <span v-else>Push {{ matchedFlags.length }} flags</span>
      </button>
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

textarea {
  background-color: #181818;
  border: 1px solid #313131;
  color: #afafaf;
  font-size: 16px;
  box-sizing: border-box;
  width: 100%;
  height: 218px;
  padding: 5px;
  resize: none;
  overflow-y: scroll;
  scrollbar-width: thin;
}

textarea:focus {
  outline: none;
  border-color: #ef233c;
}

.submit-controls {
  display: flex;
  justify-content: flex-end;
  margin-top: 10px;
}

button {
  font-family: 'Fira Code', monospace;
  font-size: 14px;
  padding: 5px 10px;
  background-color: #181818;
  border: 1px solid #313131;
  color: #afafaf;
  overflow: hidden;
  position: relative;
  width: 180px;
  height: 40px;
}

button:hover {
  background-color: #1f1f1f;
  cursor: pointer;
}

button:disabled {
  background-color: #181818;
  border: 1px solid #181818;
  cursor: not-allowed;
  color: #6b6b6b;
}

.flags {
  width: 100%;
  height: 50vh;
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
  margin: 0;
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

td.status,
th.status {
  width: 14%;
}

td.flag,
th.flag {
  width: 43%;
}

td.response,
th.response {
  width: 43%;
}
</style>
