import type { Metadata } from "next"
import { findWp, SORTED_WP_REGISTRY } from "@/lib/wp-registry"
import { WpDetailHeader } from "@/components/dashboard/WpDetailHeader"
import { MetricsPanel } from "@/components/dashboard/MetricsPanel"
import { AlertPanel } from "@/components/dashboard/AlertPanel"
import { LogViewer } from "@/components/dashboard/LogViewer"
import { DebugControlPanel } from "@/components/dashboard/DebugControlPanel"
import { SentinelControlPanel } from "@/components/dashboard/SentinelControlPanel"
import styles from "./page.module.css"

interface Params {
  wp: string
}

export function generateStaticParams() {
  return SORTED_WP_REGISTRY.map((wp) => ({ wp: wp.id }))
}

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>
}): Promise<Metadata> {
  const { wp: wpId } = await params
  const wp = findWp(wpId)
  return {
    title: wp ? `${wp.code} ${wp.label} · 运维控制台` : "WP 详情",
  }
}

export default async function WpDetailPage({
  params,
}: {
  params: Promise<Params>
}) {
  const { wp: wpId } = await params
  const wp = findWp(wpId)

  if (!wp) {
    return (
      <div className={styles.notFound}>
        <p className={styles.notFoundTitle}>智能体 "{wpId}" 未找到</p>
        <p>请检查 URL 或返回总览页面</p>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <WpDetailHeader wp={wp} />

      <div className={styles.body}>
        <MetricsPanel wp={wp} />

        <LogViewer streamUrl={wp.logStream} height={320} />

        <div className={styles.twoCol}>
          <AlertPanel wpId={wp.id} title="WP 告警" />
          {wp.id === "wp11" && <DebugControlPanel />}
          {wp.id === "sentinel" && <SentinelControlPanel />}
        </div>
      </div>
    </div>
  )
}
