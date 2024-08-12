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
  elements
} from 'chart.js'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Tooltip)

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
  }
})

const data = computed(() => ({
  labels: props.labels,
  datasets: [
    {
      label: props.label,
      data: props.data,
      borderColor: '#EF233C',
      pointBackgroundColor: '#EF233C',
      pointHoverBackgroundColor: '#EF233C',
      pointHoverRadius: 5,
      pointBorderColor: 'transparent'
    }
  ]
}))

const options = {
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
      display: false
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
    line: {
      cubicInterpolationMode: 'monotone'
    }
  },
  animations: false,
  interaction: {
    mode: 'index'
  },
  maintainAspectRatio: false,
  responsive: true
}
</script>

<template>
  <Line :data="data" :options="options" />
</template>
