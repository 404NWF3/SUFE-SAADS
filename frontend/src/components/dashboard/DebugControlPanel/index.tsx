"use client"

import { useWpRun } from "@/lib/hooks/useWpRun"
import { useWp11Nodes } from "@/lib/hooks/useWp11Nodes"
import { RunControl } from "./RunControl"
import { RunProgressTracker } from "./RunProgressTracker"
import { AgentNodeCard } from "./AgentNodeCard"
import { StateInspector } from "./StateInspector"
import { LogViewer } from "@/components/dashboard/LogViewer"
import styles from "./DebugControlPanel.module.css"

export function DebugControlPanel() {
  const { activeRun, isStarting, isCancelling, start, cancel } = useWpRun("wp11")
  const { nodes, isLoading, triggerNode, isTriggering } = useWp11Nodes()

  const handleStart = async (req: Parameters<typeof start>[0]) => {
    await start(req)
  }

  const handleCancel = async (runId: string) => {
    await cancel(runId)
  }

  return (
    <div className={styles.panel}>
      {/* Run control + progress（RunProgressTracker 作为 children 渲染在 RunControl 卡片内） */}
      <RunControl
        activeRun={activeRun}
        isStarting={isStarting}
        isCancelling={isCancelling}
        onStart={handleStart}
        onCancel={handleCancel}
      >
        {activeRun && <RunProgressTracker run={activeRun} />}
      </RunControl>

      {/* Real-time log stream */}
      <LogViewer streamUrl="/api/wp11/logs/stream" />

      {/* State inspector */}
      <StateInspector runId={activeRun?.run_id} />

      {/* Per-node trigger grid */}
      <div className={styles.nodeSection}>
        <div className={styles.nodeSectionHeader}>
          <h2 className={styles.nodeSectionTitle}>图节点触发</h2>
          <span className={styles.nodeCount}>{nodes.length} 个节点</span>
        </div>
        <div className={styles.nodeGrid}>
          {isLoading ? (
            <div style={{ padding: "1rem", fontSize: "0.8rem", color: "var(--text-faint)" }}>
              加载节点列表…
            </div>
          ) : (
            nodes.map((node, i) => (
              <AgentNodeCard
                key={node.node_name}
                node={node}
                index={i}
                isTriggering={isTriggering[node.node_name] ?? false}
                onTrigger={triggerNode}
              />
            ))
          )}
        </div>
      </div>
    </div>
  )
}
