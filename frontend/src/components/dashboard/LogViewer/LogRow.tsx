import type { RowComponentProps } from "react-window"
import type { WpLogEntry } from "@/lib/types/wp"
import styles from "./LogViewer.module.css"

export interface LogRowData {
  entries: WpLogEntry[]
}

const LEVEL_ROW_CLASS: Record<string, string> = {
  DEBUG: styles.rowDEBUG ?? "",
  INFO: styles.rowINFO ?? "",
  WARN: styles.rowWARN ?? "",
  ERROR: styles.rowERROR ?? "",
}

const LEVEL_TAG_CLASS: Record<string, string> = {
  DEBUG: styles.levelTagDEBUG ?? "",
  INFO: styles.levelTagINFO ?? "",
  WARN: styles.levelTagWARN ?? "",
  ERROR: styles.levelTagERROR ?? "",
}

function formatTime(iso: string): string {
  try {
    const d = new Date(iso)
    return d.toLocaleTimeString("zh-CN", {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    })
  } catch {
    return iso.slice(11, 19)
  }
}

function copyRow(entry: WpLogEntry) {
  const text = `[${entry.timestamp}] [${entry.level}] [${entry.source}] ${entry.message}`
  void navigator.clipboard?.writeText(text)
}

export function LogRow({
  index,
  style,
  entries,
}: RowComponentProps<LogRowData>) {
  const entry = entries[index]
  if (!entry) return null

  const rowClass = LEVEL_ROW_CLASS[entry.level] ?? ""
  const tagClass = LEVEL_TAG_CLASS[entry.level] ?? ""

  return (
    <div
      style={style}
      className={`${styles.row ?? ""} ${rowClass}`}
      onClick={() => copyRow(entry)}
      title="点击复制日志行"
      role="row"
    >
      <span className={styles.rowTime ?? ""}>{formatTime(entry.timestamp)}</span>
      <span className={`${styles.levelTag ?? ""} ${tagClass}`}>{entry.level}</span>
      <span className={styles.rowSource ?? ""}>{entry.source}</span>
      <span className={styles.rowMsg ?? ""}>{entry.message}</span>
    </div>
  )
}
