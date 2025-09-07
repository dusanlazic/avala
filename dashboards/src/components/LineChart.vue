<script setup>
import { computed, defineProps } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
  Filler,
  elements
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip, Filler)


const props = defineProps({
  data: {
    type: Array,
    required: true
  },
  labels: {
    type: Array,
    required: true
  },
  label: {
    type: String,
    required: true
  },
  yMax: {
    type: Number,
    required: false,
    default: 1
  }
})

const data = computed(() => ({
  labels: props.labels,
  datasets: [
    {
      label: props.label,
      data: props.data,
      borderColor: '#EF233C',
      borderWidth: 2,
      pointBackgroundColor: '#EF233C',
      pointHoverBackgroundColor: '#EF233C',
      pointHoverRadius: 5,
      pointBorderColor: 'transparent',
      fill: false
    }
  ]
}))

const options = computed(() => ({
  scales: {
    x: {
      display: false,
      grid: {
        display: false
      },
      title: {
        display: false
      }
    },
    y: {
      display: false,
      min: 0,
      max: props.yMax
    }
  },
  plugins: {
    legend: {
      display: false
    }
  },
  elements: {
    point: {
      radius: 0,
      hitRadius: 25
    },
  },
  animation: false,
  interaction: {
    mode: 'index',
    intersect: false
  },
  maintainAspectRatio: false,
  responsive: true
}));
</script>

<template>
  <Line :data="data" :options="options" style="height: 45px;" />
</template>
