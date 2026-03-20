"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { USE_MOCK_API } from "@/lib/api/client"
import { MOCK_LOGS } from "@/lib/api/mock"
import { WpLogEntrySchema, type WpLogEntry } from "@/lib/types/wp"

export type SSELogStatus =
  | "connecting"
  | "connected"
  | "reconnecting"
  | "error"
  | "closed"

const BACKOFF_SCHEDULE = [1000, 2000, 4000, 8000, 16000, 30000]
const MAX_RETRIES = 10

interface UseSSELogOptions {
  maxEntries?: number
  enabled?: boolean
}

export function useSSELog(
  url: string,
  { maxEntries = 500, enabled = true }: UseSSELogOptions = {}
): {
  entries: WpLogEntry[]
  status: SSELogStatus
  retryCount: number
  reconnect: () => void
  clear: () => void
} {
  const [entries, setEntries] = useState<WpLogEntry[]>([])
  const [status, setStatus] = useState<SSELogStatus>("closed")
  const [retryCount, setRetryCount] = useState(0)

  const esRef = useRef<EventSource | null>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const retryCountRef = useRef(0)
  const enabledRef = useRef(enabled)
  const mockIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const mountedRef = useRef(true)

  enabledRef.current = enabled

  const pushEntry = useCallback(
    (entry: WpLogEntry) => {
      setEntries((prev) => {
        const next = [...prev, entry]
        return next.length > maxEntries ? next.slice(next.length - maxEntries) : next
      })
    },
    [maxEntries]
  )

  const closeConnection = useCallback(() => {
    if (esRef.current) {
      esRef.current.close()
      esRef.current = null
    }
    if (timerRef.current !== null) {
      clearTimeout(timerRef.current)
      timerRef.current = null
    }
    if (mockIntervalRef.current !== null) {
      clearInterval(mockIntervalRef.current)
      mockIntervalRef.current = null
    }
  }, [])

  const connect = useCallback(() => {
    if (!enabledRef.current || !mountedRef.current) return
    closeConnection()

    /* ── Mock 模式：setInterval 模拟日志流 ─── */
    if (USE_MOCK_API) {
      setStatus("connected")
      let idx = 0
      mockIntervalRef.current = setInterval(() => {
        if (!mountedRef.current) return
        const entry = MOCK_LOGS[idx % MOCK_LOGS.length]
        if (entry) {
          pushEntry({
            ...entry,
            timestamp: new Date().toISOString(),
          })
        }
        idx++
      }, 2000)
      return
    }

    /* ── 真实 SSE 连接 ─── */
    setStatus(retryCountRef.current === 0 ? "connecting" : "reconnecting")
    const es = new EventSource(url)
    esRef.current = es

    es.onopen = () => {
      if (!mountedRef.current) return
      retryCountRef.current = 0
      setRetryCount(0)
      setStatus("connected")
    }

    es.onmessage = (evt) => {
      if (!mountedRef.current) return
      try {
        const raw: unknown = JSON.parse(evt.data as string)
        const parsed = WpLogEntrySchema.safeParse(raw)
        if (parsed.success) pushEntry(parsed.data)
      } catch {
        // ignore malformed frames
      }
    }

    es.onerror = () => {
      if (!mountedRef.current) return
      es.close()
      esRef.current = null

      const nextRetry = retryCountRef.current + 1
      retryCountRef.current = nextRetry
      setRetryCount(nextRetry)

      if (nextRetry > MAX_RETRIES) {
        setStatus("error")
        return
      }

      setStatus("reconnecting")
      const delay =
        BACKOFF_SCHEDULE[Math.min(nextRetry - 1, BACKOFF_SCHEDULE.length - 1)] ?? 30000
      timerRef.current = setTimeout(connect, delay)
    }
  }, [url, closeConnection, pushEntry])

  /* 手动重连：重置重试计数 */
  const reconnect = useCallback(() => {
    retryCountRef.current = 0
    setRetryCount(0)
    connect()
  }, [connect])

  const clear = useCallback(() => {
    setEntries([])
  }, [])

  /* 初始连接 */
  useEffect(() => {
    mountedRef.current = true
    if (enabled) connect()
    return () => {
      mountedRef.current = false
      closeConnection()
      setStatus("closed")
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [url, enabled])

  /* Tab 重新可见时立即重连 */
  useEffect(() => {
    const onVisibility = () => {
      if (
        !document.hidden &&
        (status === "reconnecting" || status === "error") &&
        enabledRef.current
      ) {
        reconnect()
      }
    }
    document.addEventListener("visibilitychange", onVisibility)
    return () => document.removeEventListener("visibilitychange", onVisibility)
  }, [status, reconnect])

  return { entries, status, retryCount, reconnect, clear }
}
