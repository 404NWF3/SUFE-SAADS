"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { USE_MOCK_API } from "@/lib/api/client"
import { MOCK_LOGS } from "@/lib/api/mock"
import { WpLogEntrySchema, type WpLogEntry, type WpVerboseLogEntry } from "@/lib/types/wp"

/**
 * 将后端 SSE 事件（{type, node, ts, ...}）或 mock 日志格式（{timestamp, level, ...}）
 * 统一转换为 WpVerboseLogEntry。无法识别的事件返回 null（调用方跳过）。
 *
 * 新增事件类型：
 *  - run_header  → 运行头（等价于 StepDebugger 的 banner）
 *  - node_verbose → 节点状态关键字段 JSON（等价于 --verbose 输出）
 */
function toLogEntry(raw: unknown): WpVerboseLogEntry | null {
  // 先尝试 mock / 直接兼容格式
  const direct = WpLogEntrySchema.safeParse(raw)
  if (direct.success) return direct.data

  if (typeof raw !== "object" || raw === null) return null
  const evt = raw as Record<string, unknown>
  const ts =
    typeof evt.ts === "string" ? evt.ts : new Date().toISOString()

  switch (evt.type) {
    case "run_header":
      return {
        timestamp: ts,
        level: "INFO",
        source: "系统",
        message: `══ SAADS WP1-1 Intel Pipeline ══  run_id: ${evt.run_id ?? "?"}  mode: ${evt.run_mode ?? "?"}  runtime: ${evt.source_runtime_mode ?? "?"}  model: ${evt.llm_model ?? "?"}`,
      }
    case "init":
      return {
        timestamp: ts,
        level: "INFO",
        source: "系统",
        message: `▶ 运行启动 — ${evt.run_id ?? "?"} (${evt.run_mode ?? "?"})`,
      }
    case "node_complete": {
      const errCount = typeof evt.error_count === "number" ? evt.error_count : 0
      const errSuffix = errCount > 0 ? ` ⚠ ${errCount} 个节点错误` : ""
      const idx = typeof evt.node_index === "number" ? `[${String(evt.node_index).padStart(2, "0")}] ` : ""
      const elapsed = typeof evt.elapsed_ms === "number" ? ` ${evt.elapsed_ms.toFixed(1)}ms` : ""
      return {
        timestamp: ts,
        level: errCount > 0 ? "WARN" : "INFO",
        source: String(evt.display_name ?? evt.node ?? "节点"),
        message: `${idx}完成 — ${evt.percent ?? 0}%${elapsed}${errSuffix}`,
      }
    }
    case "node_detail":
      return {
        timestamp: ts,
        level: "DEBUG",
        source: String(evt.display_name ?? evt.node ?? "详情"),
        message: String(evt.message ?? ""),
      }
    case "node_verbose": {
      const key = String(evt.key ?? "?")
      const valueStr = String(evt.value ?? "")
      // 单行预览：取前 120 字符
      const preview = valueStr.length > 120 ? valueStr.slice(0, 120) + "…" : valueStr
      return {
        timestamp: ts,
        level: "DEBUG",
        source: String(evt.display_name ?? evt.node ?? "详情"),
        message: `${key}: ${preview}`,
        verboseKey: key,
        verboseJson: valueStr,
        truncated: evt.truncated === true,
      }
    }
    case "node_error_detail":
      return {
        timestamp: ts,
        level: "ERROR",
        source: String(evt.display_name ?? evt.node ?? "错误"),
        message: String(evt.message ?? ""),
      }
    case "error":
      return {
        timestamp: ts,
        level: "ERROR",
        source: String(evt.node ?? "运行时错误"),
        message: String(evt.message ?? "未知错误"),
      }
    case "done":
      return {
        timestamp: new Date().toISOString(),
        level: evt.status === "succeeded" ? "INFO" : "WARN",
        source: "系统",
        message: `■ 运行结束 — ${evt.status ?? "unknown"} (${evt.percent ?? 0}%)`,
      }
    case "heartbeat":
    case "idle":
      return null
    default:
      return null
  }
}

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
  entries: WpVerboseLogEntry[]
  status: SSELogStatus
  retryCount: number
  reconnect: () => void
  clear: () => void
} {
  const [entries, setEntries] = useState<WpVerboseLogEntry[]>([])
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
    (entry: WpVerboseLogEntry) => {
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
        const entry = toLogEntry(raw)
        if (entry) pushEntry(entry)
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
