import { nextTick, onBeforeUnmount, watch, type Ref } from 'vue'

/** Keep keyboard focus inside an open portal dialog and return it to its opener. */
export function useDialogFocus(open: Ref<boolean>, dialog: Ref<HTMLElement | null>, close: () => void) {
  let opener: HTMLElement | null = null
  let previousOverflow = ''
  let active = false
  const focusable = () => Array.from(dialog.value?.querySelectorAll<HTMLElement>(
    'button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), a[href], [tabindex="0"]',
  ) ?? []).filter(el => el.getClientRects().length && !el.matches(':disabled'))

  function onKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      event.preventDefault()
      close()
    } else if (event.key === 'Tab') {
      const items = focusable()
      const first = items[0]
      const last = items.at(-1)
      if (!first) {
        event.preventDefault()
        dialog.value?.focus()
      } else if (!dialog.value?.contains(document.activeElement)) {
        event.preventDefault()
        first.focus()
      } else if (event.shiftKey && (document.activeElement === first || document.activeElement === dialog.value)) {
        event.preventDefault()
        last?.focus()
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault()
        first.focus()
      }
    }
  }
  function release() {
    if (!active) return
    active = false
    document.removeEventListener('keydown', onKeydown)
    document.body.style.overflow = previousOverflow
    if (opener?.isConnected) opener.focus()
  }
  watch(open, async value => {
    if (!value) { release(); return }
    opener = document.activeElement instanceof HTMLElement ? document.activeElement : null
    previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    active = true
    document.addEventListener('keydown', onKeydown)
    await nextTick()
    if (active) (focusable()[0] ?? dialog.value)?.focus()
  })
  onBeforeUnmount(release)
}
