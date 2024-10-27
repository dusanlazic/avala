<template>
  <span :style="{ color: currentColor }">{{ displayNumber }}</span>
</template>

<script>
export default {
  name: 'AnimatedNumber',
  props: {
    number: {
      type: Number,
      default: 0
    },
    originalColor: {
      type: String,
      default: 'inherit'
    },
    blinkDuration: {
      type: Number,
      default: 500
    }
  },
  data() {
    return {
      displayNumber: 0,
      currentColor: this.originalColor
    }
  },
  watch: {
    number(newVal, oldVal) {
      this.displayNumber = newVal
      if (newVal > oldVal) {
        this.blinkColor('MediumSeaGreen')
      } else {
        this.blinkColor('indianRed')
      }
    }
  },
  methods: {
    blinkColor(color) {
      this.currentColor = color
      setTimeout(() => {
        this.currentColor = this.originalColor
      }, this.blinkDuration)
    }
  }
}
</script>

<style scoped>
span {
  transition: color 0.2s ease;
}
</style>
