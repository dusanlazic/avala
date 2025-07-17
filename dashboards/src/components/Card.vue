<script setup lang="ts">
import { Icon } from '@iconify/vue'
import { computed } from 'vue'

const props = defineProps<{
  title: string
  value: string | number
  icon?: string
  backgroundIcon?: boolean
  subtext?: string
}>()

const formattedValue = computed(() => {
  const num = Number(props.value)
  return isNaN(num) ? props.value : num.toLocaleString()
})

</script>

<template>
  <div class="card">
    <div class="card-header">
      <div class="card-title">
        <Icon v-if="icon" :icon="icon" class="main-icon" />
        <span>{{ title }}</span>
      </div>
    </div>

    <div class="card-value">
      {{ formattedValue }}
    </div>

    <div class="card-subtext">
      {{ subtext || '\u00A0' }}
    </div>

    <Icon
      v-if="backgroundIcon && icon"
      :icon="icon"
      class="background-icon"
      aria-hidden="true"
    />
  </div>
</template>

<style scoped>
.card {
  position: relative;
  background-color: #181818;
  color: #fff;
  padding: 1.25rem;
  border-radius: 0px;
  border: 1px solid #313131;
  overflow: hidden;
  z-index: 0;
}

.card:hover {
  background-color: #1f1f1f;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  font-size: 0.875rem;
  color: #aaa;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.main-icon {
  font-size: 24px;
  color: #aaa;
}

.card-value {
  font-size: 2rem;
  font-weight: 600;
  margin-top: 0.25rem;
}

.card-subtext {
  font-size: 0.75rem;
  color: #777;
  margin-top: 0.25rem;
}

.background-icon {
  position: absolute;
  top: -40px;
  right: -60px;
  opacity: 0.035;
  font-size: 240px;
  color: #ffffff;
  z-index: -1;
}
</style>
