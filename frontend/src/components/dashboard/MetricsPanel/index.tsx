"use client"

import { useWpMetrics } from "@/lib/hooks/useWpMetrics"
import { SparkLine } from "./SparkLine"
import type { WpMeta } from "@/lib/wp-registry"
import styles from "./MetricsPanel.module.css"

interface MetricsPanelProps {
  wp: WpMeta
}

export function MetricsPanel({ wp }: MetricsPanelProps) {
  const keys = wp.metrics.map((m) => m.key)
  const { series, isLoading } = useWpMetrics(wp.id, keys)

  const seriesMap = Object.fromEntries(series.map((s) => [s.key, s]))

  return (
    <div className={styles.panel}>
      <div className={styles.header}>
        <h2 className={styles.title}>指标趋势（过去 48h）</h2>
      </div>

      <div className={styles.grid}>
        {wp.metrics.map((m) => {
          const s = seriesMap[m.key]
          const values = s?.points.map((p) => p.value) ?? []
          const latest = values[values.length - 1]

          return (
            <div key={m.key} className={styles.metricCard}>
              <div className={styles.metricLabel}>{m.label}</div>
              <div className={styles.metricValue}>
                {isLoading || latest === undefined
                  ? "—"
                  : m.format === "percent"
                    ? latest.toFixed(1)
                    : latest.toLocaleString()}
                {latest !== undefined && m.unit && (
                  <span className={styles.metricUnit}>{m.unit}</span>
                )}
              </div>
              <div className={styles.sparkContainer}>
                {!isLoading && values.length >= 2 && (
                  <SparkLine values={values} height={40} />
                )}
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
