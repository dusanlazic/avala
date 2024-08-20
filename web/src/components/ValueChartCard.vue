<script setup>
import { Icon } from '@iconify/vue'
import LineChart from './LineChart.vue'
import AnimatedNumber from './AnimatedNumber.vue'

const props = defineProps({
  icon: {
    type: String,
    required: true
  },
  title: {
    type: String,
    required: true
  },
  number: {
    type: [String, Number],
    required: true
  },
  unit: {
    type: [String]
  },
  data: {
    type: Array,
    required: true
  },
  labels: {
    type: Array,
    required: true
  }
})
</script>

<template>
  <div class="card">
    <div class="card-info">
      <p class="title">
        <Icon :icon="icon" />
        {{ title }}
      </p>
      <p class="number">
        <AnimatedNumber :number="number" :duration="700" />
        <span class="unit">{{ unit }}</span>
      </p>
    </div>

    <div class="card-chart">
      <LineChart :data="data" :labels="labels" :label="title" />
    </div>
  </div>
</template>

<style scoped>
.card {
  font-weight: 500;
  font-size: 18px;
  background-color: #181818;
  padding: 22px 25px 20px 25px;
  border: 1px solid #313131;
  overflow: hidden;
  display: flex;
  justify-content: space-between;
  align-items: stretch;
}

.card:hover {
  background-color: #1f1f1f;
}

.card-chart {
  position: relative;
  height: 76px;
  width: 60%;
}

.title {
  margin: 0;
  display: flex;
  gap: 9px;
  align-items: center;
}

.number {
  margin: 5px 0px 0px 0px;
  font-size: 36px;
  font-weight: 600;
}

.unit {
  color: #6b6b6b;
  font-size: 28px;
  margin-left: 10px;
}

.iconify {
  padding-bottom: 3px;
  font-size: 24px;
}
</style>
