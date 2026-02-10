<script setup lang="ts">
import { computed } from 'vue'
import { BaseEdge, EdgeProps, getBezierPath } from '@vue-flow/core'

const props = defineProps<EdgeProps>()

const emit = defineEmits(['click'])

const path = computed(() => {
  const [pathString] = getBezierPath({
    sourceX: props.sourceX,
    sourceY: props.sourceY,
    targetX: props.targetX,
    targetY: props.targetY,
  })
  return pathString
})

function onClick(event: MouseEvent) {
  emit('click', event, props.id)
}
</script>

<template>
  <BaseEdge
    :path="path"
    :style="{
      stroke: selected ? '#409eff' : '#b37feb',
      strokeWidth: selected ? 3 : 2,
    }"
    :marker-end="markerEnd"
    class="workflow-edge"
    @click="onClick"
  />
</template>

<style scoped lang="scss">
.workflow-edge {
  transition: all 0.2s;
  
  &:hover {
    stroke: #409eff;
    stroke-width: 3;
  }
}
</style>
