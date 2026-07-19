<script setup lang="ts">
defineProps<{ title: string; open: boolean; wide?: boolean }>()
const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <div v-if="open" class="modal-backdrop" @click.self="emit('close')">
    <section class="modal-panel" :class="{ wide }" role="dialog" aria-modal="true">
      <header class="modal-header">
        <h2>{{ title }}</h2>
        <button class="icon-button" type="button" aria-label="关闭" @click="emit('close')">×</button>
      </header>
      <div class="modal-body"><slot /></div>
    </section>
  </div>
</template>
