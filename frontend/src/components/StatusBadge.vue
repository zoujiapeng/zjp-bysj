<script setup lang="ts">
import { computed } from 'vue'
import {
  caseStatusLabels,
  conditionLabels,
  followupStatusLabels,
  referralStatusLabels,
  riskLabels,
  roleLabels,
} from '../utils'

const props = defineProps<{ value: string; label?: string }>()

const labelMap: Record<string, string> = {
  ...riskLabels,
  ...caseStatusLabels,
  ...followupStatusLabels,
  ...referralStatusLabels,
  ...conditionLabels,
  ...roleLabels,
  NORMAL: '普通',
  RESTRICTED: '受限',
}

const text = computed(() => props.label ?? labelMap[props.value] ?? props.value)
const className = computed(() => `badge badge-${props.value.toLowerCase()}`)
</script>

<template>
  <span :class="className">{{ text }}</span>
</template>
