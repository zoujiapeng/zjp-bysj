<script setup lang="ts">
defineProps<{
  page: number
  pageSize: number
  total: number
}>()

const emit = defineEmits<{ change: [page: number] }>()
</script>

<template>
  <div class="pagination" v-if="total > pageSize">
    <button type="button" :disabled="page <= 1" @click="emit('change', page - 1)">上一页</button>
    <span>第 {{ page }} 页，共 {{ Math.ceil(total / pageSize) }} 页（{{ total }} 条）</span>
    <button type="button" :disabled="page * pageSize >= total" @click="emit('change', page + 1)">下一页</button>
  </div>
</template>
