import { useEffect, useRef } from "react"

const INTERVAL_ENV = import.meta.env.VITE_POLL_INTERVAL_MS
export const DEFAULT_POLL_INTERVAL = INTERVAL_ENV ? parseInt(INTERVAL_ENV, 10) : 5000

export function usePolling(
  fetchFn: () => Promise<void>,
  intervalMs: number = DEFAULT_POLL_INTERVAL,
  enabled: boolean = true,
) {
  const savedFetch = useRef(fetchFn)
  savedFetch.current = fetchFn

  useEffect(() => {
    if (!enabled || intervalMs <= 0) return

    let active = true
    let timeoutId: ReturnType<typeof setTimeout>

    async function poll() {
      if (!active) return
      try {
        await savedFetch.current()
      } catch {
        // Errors handled by caller's state
      }
      if (active) {
        timeoutId = setTimeout(poll, intervalMs)
      }
    }

    // Delay first poll to avoid competing with initial mount fetch
    timeoutId = setTimeout(poll, intervalMs)

    return () => {
      active = false
      clearTimeout(timeoutId)
    }
  }, [intervalMs, enabled])
}
