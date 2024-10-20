<script setup>
import { Icon } from '@iconify/vue'
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
  change: {
    type: Number,
    required: false
  },
  number: {
    type: [String, Number],
    required: true
  },
  unit: {
    type: [String]
  }
})
</script>

<template>
  <div class="card">
    <Icon class="background-icon" :icon="icon" />
    <p class="title">
      <Icon :icon="icon" />
      {{ title }}
      <span class="change">{{ change }}</span>
    </p>
    <p class="number">
      <AnimatedNumber :number="number" :duration="700" />
      <span class="unit">{{ unit }}</span>
    </p>
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
  position: relative;
}

.card:hover {
  background-color: #1f1f1f;
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

.background-icon {
  position: absolute;
  top: -40px;
  right: -60px;
  opacity: 0.035;
  font-size: 240px;
  color: #ffffff;
}

.change {
  color: #6b6b6b;
}
</style>
