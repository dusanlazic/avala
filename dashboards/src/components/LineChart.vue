<script setup>
import { computed } from 'vue'
import { Line } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Tooltip,
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
  },
  showAxis: {
    type: Boolean,
    default: true
  }
})

const maxValue = computed(() => {
  if (props.data.length === 0) {
    return 0;  // Return 0 if the data array is empty
  }

  const maxDataValue = Math.max(...props.data);
  return maxDataValue === 0 ? 1 : maxDataValue;  // Ensure max is at least 1 if maxDataValue is 0
});

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
      display: props.showAxis,
      min: 0,
      max: maxValue.value,
      ticks: {
        color: 'grey',
        font: {
          size: 10
        },
        stepSize: maxValue.value,
        callback: function(value) {
          if (value === 0 || value === maxValue.value) {
            return value;
          }
          return null;
        }
      },
      grid: {
        display: false
      }
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
}))
</script>

<template>
  <Line :data="data" :options="options" />
</template>
