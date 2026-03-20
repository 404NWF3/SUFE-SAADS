import type { Metadata } from "next"
import { SORTED_WP_REGISTRY } from "@/lib/wp-registry"
import { SystemHealthBar } from "@/components/dashboard/SystemHealthBar"
import { WpStatusCard } from "@/components/dashboard/WpStatusCard"
import { AlertPanel } from "@/components/dashboard/AlertPanel"
import styles from "./page.module.css"

export const metadata: Metadata = {
  title: "总览 · 运维控制台",
}

export default function DashboardPage() {
  return (
    <div className={styles.page}>
      <SystemHealthBar />

      <div className={styles.pageHeader}>
        <h1 className={styles.pageTitle}>智能体总览</h1>
        <p className={styles.pageSub}>
          实时监控 {SORTED_WP_REGISTRY.length} 个智能体的运行状态与关键指标
        </p>
      </div>

      <div className={styles.grid}>
        {SORTED_WP_REGISTRY.map((wp) => (
          <WpStatusCard key={wp.id} wp={wp} />
        ))}
      </div>

      <div className={styles.alertSection}>
        <AlertPanel title="全局安全告警" />
      </div>
    </div>
  )
}
