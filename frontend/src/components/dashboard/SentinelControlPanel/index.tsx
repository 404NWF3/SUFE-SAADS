"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { DocRenderer } from "@/components/docs/DocRenderer"
import { processMarkdown } from "@/lib/docs/processor"
import styles from "./SentinelControlPanel.module.css"

type CollectMode = "full" | "nvd" | "github" | "arxiv" | "community"
type TriggerMode = "subprocess" | "openclaw"
type ConnectionStatus = "ready" | "degraded" | "error"
type RunStatus = "starting" | "running" | "cancelling" | "succeeded" | "failed" | "cancelled"

interface ConnectionSnapshot {
  status: ConnectionStatus
  checked_at: string
  workspace_root: string
  workspace_exists: boolean
  workspace_source: string
  preferred_transport: TriggerMode
  issues: string[]
  agent: {
    id: string
    configured: boolean
    workspace: string | null
    workspace_matches: boolean
  }
  gateway: {
    http_url: string
    ws_url: string
    auth_configured: boolean
    reachable: boolean
    protocol: number | null
    server_version: string | null
    default_agent_id: string | null
  }
  hooks: {
    enabled: boolean
    mapping_present: boolean
  }
}

interface RunResponse {
  run_id: string
  status: RunStatus
  mode: CollectMode
  transport: TriggerMode
  use_gateway: boolean
  started_at: string
  ended_at?: string | null
  error?: string | null
  assistant_markdown?: string | null
}

type RunState =
  | { phase: "idle" }
  | { phase: "starting" }
  | { phase: "running"; runId: string; mode: CollectMode; transport: TriggerMode; startedAt: string }
  | { phase: "cancelling"; runId: string }
  | { phase: "done"; runId: string; outcome: "succeeded" | "cancelled" }
  | { phase: "error"; message: string }

const MODE_OPTIONS: { value: CollectMode; label: string; desc: string }[] = [
  { value: "full", label: "全量采集", desc: "NVD + GitHub + arXiv + 社区信号" },
  { value: "nvd", label: "NVD", desc: "CVE 与官方漏洞库" },
  { value: "github", label: "GitHub Advisory", desc: "开源生态安全公告" },
  { value: "arxiv", label: "arXiv", desc: "AI 安全论文与研究动态" },
  { value: "community", label: "社区信号", desc: "Hacker News + Reddit" },
]

const TRIGGER_OPTIONS: { value: TriggerMode; label: string; desc: string }[] = [
  {
    value: "openclaw",
    label: "OpenClaw Gateway",
    desc: "通过本机 OpenClaw Gateway WebSocket RPC 调起 llm-security-intel agent",
  },
  {
    value: "subprocess",
    label: "本地脚本",
    desc: "直接运行 workspace 内的 Python 采集脚本",
  },
]

export function SentinelControlPanel() {
  const [collectMode, setCollectMode] = useState<CollectMode>("full")
  const [triggerMode, setTriggerMode] = useState<TriggerMode>("openclaw")
  const [runState, setRunState] = useState<RunState>({ phase: "idle" })
  const [connection, setConnection] = useState<ConnectionSnapshot | null>(null)
  const [connectionError, setConnectionError] = useState<string | null>(null)
  const [loadingConnection, setLoadingConnection] = useState(true)
  const [assistantMarkdown, setAssistantMarkdown] = useState("")
  const [assistantHtml, setAssistantHtml] = useState("")
  const [assistantRenderError, setAssistantRenderError] = useState<string | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const autoSelectedTransportRef = useRef(false)

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const applyRunSnapshot = useCallback((data: RunResponse) => {
    setAssistantMarkdown(data.assistant_markdown ?? "")

    if (data.status === "starting" || data.status === "running") {
      setRunState({
        phase: "running",
        runId: data.run_id,
        mode: data.mode,
        transport: data.transport,
        startedAt: data.started_at,
      })
      return
    }

    if (data.status === "cancelling") {
      setRunState({ phase: "cancelling", runId: data.run_id })
      return
    }

    if (data.status === "succeeded") {
      setRunState({ phase: "done", runId: data.run_id, outcome: "succeeded" })
      return
    }

    if (data.status === "cancelled") {
      setRunState({ phase: "done", runId: data.run_id, outcome: "cancelled" })
      return
    }

    setRunState({ phase: "error", message: data.error ?? "任务执行失败" })
  }, [])

  useEffect(() => {
    let cancelled = false

    if (!assistantMarkdown.trim()) {
      setAssistantHtml("")
      setAssistantRenderError(null)
      return
    }

    void processMarkdown(assistantMarkdown)
      .then((html) => {
        if (cancelled) return
        setAssistantHtml(html)
        setAssistantRenderError(null)
      })
      .catch((err) => {
        if (cancelled) return
        setAssistantHtml("")
        setAssistantRenderError(String(err))
      })

    return () => {
      cancelled = true
    }
  }, [assistantMarkdown])

  const startPolling = useCallback(
    (runId: string) => {
      stopPolling()
      pollRef.current = setInterval(async () => {
        try {
          const res = await fetch(`/api/sentinel/runs/${runId}`, { cache: "no-store" })
          if (!res.ok) {
            stopPolling()
            setRunState({ phase: "error", message: `无法获取运行状态（HTTP ${res.status}）` })
            return
          }

          const data = (await res.json()) as RunResponse
          if (data.status === "starting" || data.status === "running" || data.status === "cancelling") {
            applyRunSnapshot(data)
            return
          }

          stopPolling()
          applyRunSnapshot(data)
        } catch {
          // keep polling on transient fetch failures
        }
      }, 2000)
    },
    [applyRunSnapshot, stopPolling]
  )

  const refreshConnection = useCallback(async () => {
    setLoadingConnection(true)
    setConnectionError(null)
    try {
      const res = await fetch("/api/sentinel/connection", { cache: "no-store" })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const data = (await res.json()) as ConnectionSnapshot
      setConnection(data)
      if (!autoSelectedTransportRef.current) {
        setTriggerMode(data.preferred_transport)
        autoSelectedTransportRef.current = true
      }
    } catch (err) {
      setConnectionError(String(err))
    } finally {
      setLoadingConnection(false)
    }
  }, [])

  const restoreActiveRun = useCallback(async () => {
    try {
      const res = await fetch("/api/sentinel/runs/active", { cache: "no-store" })
      if (res.status === 404) {
        return
      }
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      const data = (await res.json()) as RunResponse
      applyRunSnapshot(data)
      startPolling(data.run_id)
    } catch (err) {
      setRunState({ phase: "error", message: `恢复运行状态失败：${String(err)}` })
    }
  }, [applyRunSnapshot, startPolling])

  useEffect(() => {
    void refreshConnection()
    void restoreActiveRun()
    return () => stopPolling()
  }, [refreshConnection, restoreActiveRun, stopPolling])

  const handleStart = async () => {
    if (triggerMode === "openclaw" && connection?.preferred_transport !== "openclaw") {
      setRunState({
        phase: "error",
        message: connection?.issues?.[0] ?? "OpenClaw 连接未就绪",
      })
      return
    }

    setRunState({ phase: "starting" })
    setAssistantMarkdown("")
    setAssistantHtml("")
    setAssistantRenderError(null)
    try {
      const res = await fetch("/api/sentinel/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          mode: collectMode,
          transport: triggerMode,
          use_gateway: triggerMode === "openclaw",
        }),
      })

      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }))
        setRunState({ phase: "error", message: body.detail ?? `HTTP ${res.status}` })
        await refreshConnection()
        return
      }

      const data = (await res.json()) as RunResponse
      applyRunSnapshot(data)
      startPolling(data.run_id)
      await refreshConnection()
    } catch (err) {
      setRunState({ phase: "error", message: String(err) })
    }
  }

  const handleCancel = async () => {
    if (runState.phase !== "running") return
    const { runId } = runState
    setRunState({ phase: "cancelling", runId })
    try {
      const res = await fetch(`/api/sentinel/runs/${runId}`, { method: "DELETE" })
      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }
      startPolling(runId)
    } catch (err) {
      stopPolling()
      setRunState({ phase: "error", message: `取消失败：${String(err)}` })
    }
  }

  const handleReset = () => setRunState({ phase: "idle" })

  const isStarting = runState.phase === "starting"
  const isBusy = runState.phase === "running" || runState.phase === "cancelling" || isStarting
  const openClawReady = connection?.preferred_transport === "openclaw"

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2 className={styles.title}>Sentinel 采集触发</h2>
        {runState.phase === "running" && <span className={styles.runId}>{runState.runId}</span>}
      </div>

      <div className={styles.section}>
        <div className={styles.sectionHeader}>
          <label className={styles.label}>OpenClaw 连接诊断</label>
          <button className={styles.inlineBtn} onClick={() => void refreshConnection()} disabled={loadingConnection}>
            {loadingConnection ? "检测中" : "刷新"}
          </button>
        </div>

        {connection && (
          <div className={styles.connectionCard}>
            <div className={styles.connectionTop}>
              <span
                className={[
                  styles.statusPill,
                  connection.status === "ready"
                    ? styles.statusReady
                    : connection.status === "degraded"
                      ? styles.statusDegraded
                      : styles.statusErrorPill,
                ].join(" ")}
              >
                {connection.status === "ready"
                  ? "OpenClaw 已就绪"
                  : connection.status === "degraded"
                    ? "配置不完整"
                    : "连接失败"}
              </span>
              <span className={styles.metaText}>{connection.gateway.http_url}</span>
            </div>

            <div className={styles.factGrid}>
              <div className={styles.factItem}>
                <span className={styles.factKey}>Workspace</span>
                <span className={styles.factValue}>{connection.workspace_exists ? "存在" : "缺失"}</span>
              </div>
              <div className={styles.factItem}>
                <span className={styles.factKey}>Agent</span>
                <span className={styles.factValue}>{connection.agent.configured ? connection.agent.id : "未配置"}</span>
              </div>
              <div className={styles.factItem}>
                <span className={styles.factKey}>Gateway</span>
                <span className={styles.factValue}>{connection.gateway.reachable ? "可连接" : "不可连接"}</span>
              </div>
              <div className={styles.factItem}>
                <span className={styles.factKey}>Protocol</span>
                <span className={styles.factValue}>{connection.gateway.protocol ?? "-"}</span>
              </div>
            </div>

            <p className={styles.pathText}>{connection.workspace_root}</p>

            {connection.issues.length > 0 && (
              <div className={styles.issueBox}>
                {connection.issues.map((issue) => (
                  <p key={issue} className={styles.issueText}>
                    {issue}
                  </p>
                ))}
              </div>
            )}

            <p className={styles.note}>
              {connection.hooks.enabled
                ? "hooks.enabled=true，但当前面板已优先走 Gateway RPC。"
                : "hooks.enabled=false 不影响当前接入，当前面板直接走 Gateway RPC。"}
            </p>
          </div>
        )}

        {connectionError && <p className={styles.errorText}>诊断请求失败：{connectionError}</p>}
      </div>

      <div className={styles.section}>
        <label className={styles.label}>采集范围</label>
        <div className={styles.modeGrid}>
          {MODE_OPTIONS.map((opt) => (
            <button
              key={opt.value}
              className={[styles.modeChip, collectMode === opt.value ? styles.modeChipActive : ""].join(" ")}
              onClick={() => setCollectMode(opt.value)}
              disabled={isBusy}
              title={opt.desc}
            >
              {opt.label}
            </button>
          ))}
        </div>
        <p className={styles.hint}>{MODE_OPTIONS.find((opt) => opt.value === collectMode)?.desc}</p>
      </div>

      <div className={styles.section}>
        <label className={styles.label}>触发方式</label>
        <div className={styles.triggerGroup}>
          {TRIGGER_OPTIONS.map((opt) => {
            const disabled = isBusy || (opt.value === "openclaw" && !openClawReady)
            return (
              <label
                key={opt.value}
                className={[
                  styles.triggerOption,
                  triggerMode === opt.value ? styles.triggerOptionActive : "",
                  disabled ? styles.triggerOptionDisabled : "",
                ].join(" ")}
              >
                <input
                  type="radio"
                  name="triggerMode"
                  value={opt.value}
                  checked={triggerMode === opt.value}
                  onChange={() => setTriggerMode(opt.value)}
                  disabled={disabled}
                  className={styles.radioInput}
                />
                <div>
                  <span className={styles.triggerLabel}>{opt.label}</span>
                  <span className={styles.triggerDesc}>{opt.desc}</span>
                </div>
              </label>
            )
          })}
        </div>
        {triggerMode === "openclaw" && (
          <p className={styles.gatewayNote}>
            优先从 <code>~/.openclaw/openclaw.json</code> 自动发现 gateway、agent 与 workspace；
            <code>OPENCLAW_GATEWAY_URL</code>、<code>OPENCLAW_GATEWAY_TOKEN</code> 可作为覆盖配置。
          </p>
        )}
      </div>

      <div className={styles.footer}>
        {runState.phase === "idle" && (
          <button className={styles.startBtn} onClick={handleStart} disabled={triggerMode === "openclaw" && !openClawReady}>
            发起采集
          </button>
        )}

        {isStarting && (
          <button className={styles.startBtn} disabled>
            启动中
          </button>
        )}

        {runState.phase === "running" && (
          <>
            <span className={styles.statusRunning}>
              <span className={styles.pulse} />
              采集中 · {MODE_OPTIONS.find((opt) => opt.value === runState.mode)?.label}（{runState.transport}）
            </span>
            <button className={styles.cancelBtn} onClick={handleCancel}>
              取消
            </button>
          </>
        )}

        {runState.phase === "cancelling" && <span className={styles.statusMuted}>取消中</span>}

        {runState.phase === "done" && (
          <>
            <span className={runState.outcome === "succeeded" ? styles.statusDone : styles.statusCancelled}>
              {runState.outcome === "succeeded" ? "采集完成" : "已取消"}
            </span>
            <button className={styles.resetBtn} onClick={handleReset}>
              重置
            </button>
          </>
        )}

        {runState.phase === "error" && (
          <>
            <span className={styles.statusError} title={runState.message}>
              {runState.message.length > 88 ? `${runState.message.slice(0, 88)}...` : runState.message}
            </span>
            <button className={styles.resetBtn} onClick={handleReset}>
              重试
            </button>
          </>
        )}
      </div>

      {(assistantHtml || assistantMarkdown || assistantRenderError) && (
        <div className={styles.section}>
          <label className={styles.label}>Agent 总结</label>
          <div className={styles.summaryCard}>
            {assistantHtml ? (
              <DocRenderer html={assistantHtml} />
            ) : assistantRenderError ? (
              <p className={styles.errorText}>Markdown 渲染失败：{assistantRenderError}</p>
            ) : (
              <pre className={styles.summaryFallback}>{assistantMarkdown}</pre>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
