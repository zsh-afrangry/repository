/**
 * Intersection Observer based scroll-reveal.
 * Elements with class "reveal-item" get "revealed" added when they enter viewport.
 *
 * ⚠ **调用方必须自己断开它**：
 * ```ts
 * const observer = useScrollReveal()
 * onBeforeUnmount(() => observer.disconnect())
 * ```
 *
 * 这里**不能**用 `onScopeDispose()` 做自动清理：本函数的常见调用点是在 `onMounted`
 * 回调里（见 `Dashboard.vue`），那时已经没有活动的 effect scope，`onScopeDispose`
 * 只会打印 "no active effect scope" 警告并且不生效——那比不做清理更糟，因为它看起来
 * 像是已经处理好了。所以清理责任显式交给调用方。
 *
 * ⚠ 另一个坑：本函数在**调用瞬间**就用 `document.querySelectorAll` 抓取 `.reveal-item`。
 * 若在 `setup()` 里直接调用，组件 DOM 尚未挂载，会一个都抓不到，滚动揭示静默失效。
 * **必须在 `onMounted`（或之后）调用。**
 */
export function useScrollReveal() {
  const observer = new IntersectionObserver(
    (entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) {
          entry.target.classList.add('revealed')
          observer.unobserve(entry.target) // Only reveal once
        }
      })
    },
    {
      threshold: 0.15,
      rootMargin: '0px 0px -50px 0px',
    }
  )

  document.querySelectorAll('.reveal-item').forEach((el) => {
    observer.observe(el)
  })

  return observer
}
