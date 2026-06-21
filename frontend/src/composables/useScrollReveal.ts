/**
 * Intersection Observer based scroll-reveal.
 * Elements with class "reveal-item" get "revealed" added when they enter viewport.
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
