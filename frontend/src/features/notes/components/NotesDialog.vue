<script setup lang="ts">
import { ref, onMounted } from 'vue';
import { useDialogFocus } from '../../../composables/useDialogFocus';
const props = defineProps<{
    label: string;
}>();
const emit = defineEmits<{
    close: [
    ];
}>();
const open = ref(false), dialog = ref<HTMLElement | null>(null);
useDialogFocus(open, dialog, () => emit('close'));
onMounted(() => { open.value = true; });
</script>
<template>
  <Teleport to="body">
    <div class="notes-workspace dialog-backdrop" @click.self="emit('close')">
      <section ref="dialog" class="notes-dialog" role="dialog" aria-modal="true" :aria-label="props.label" tabindex="-1" data-lenis-prevent>
        <slot />
      </section>
    </div>
  </Teleport>
</template>
<style scoped src="../styles/theme.css"></style>
<style scoped>
.dialog-backdrop { position: fixed; inset: 0; z-index: 100; display: flex; justify-content: center; padding: 24px; background: rgb(0 0 0 / .65); color: var(--text); }
.notes-dialog { width: min(100%, 1040px); min-height: 0; overflow-y: auto; overscroll-behavior: contain; background: var(--notes-reader); border: 1px solid var(--notes-border); border-radius: 18px; box-shadow: 0 24px 80px #0008; }
@media(max-width:600px) { .dialog-backdrop { padding: 0; } .notes-dialog { border-radius: 0; border: 0; } }
</style>
