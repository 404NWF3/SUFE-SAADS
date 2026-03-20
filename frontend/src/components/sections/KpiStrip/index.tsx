"use client"

import { ScrollReveal } from "@/components/ui/ScrollReveal"
import { CountUp } from "@/components/ui/CountUp"
import styles from "./KpiStrip.module.css"

interface KpiItem {
  value: number
  suffix: string
  label: string
  sub: string
  formatter: (n: number) => string
}

const KPIS: KpiItem[] = [
  {
    value: 2400,
    suffix: "+",
    label: "已入库攻击情报",
    sub: "来自全球漏洞库",
    formatter: (n) => n.toLocaleString("zh-CN"),
  },
  {
    value: 100,
    suffix: "%",
    label: "OWASP LLM Top 10",
    sub: "威胁类型覆盖率",
    formatter: (n) => n.toLocaleString("zh-CN"),
  },
  {
    value: 380,
    suffix: "+",
    label: "自动化测试脚本",
    sub: "WP1-2 生成",
    formatter: (n) => n.toLocaleString("zh-CN"),
  },
  {
    value: 97.3,
    suffix: "%",
    label: "检测模型准确率",
    sub: "WP1-4 基线模型",
    formatter: (n) => n.toFixed(1),
  },
]

export function KpiStrip() {
  return (
    <section className={styles.section} id="kpi-strip" aria-label="关键指标">
      <div className="container">
        <div className="kpi-strip">
          {KPIS.map((kpi, i) => (
            <ScrollReveal key={kpi.label} delay={i as 0 | 1 | 2 | 3}>
              <div className="kpi">
                <div className={`kpi__value ${styles.valueRow}`}>
                  <CountUp
                    to={kpi.value}
                    formatter={kpi.formatter}
                    duration={1600}
                  />
                  <span className={styles.suffix} aria-hidden="true">
                    {kpi.suffix}
                  </span>
                </div>
                <div className="kpi__label">{kpi.label}</div>
                <div className={styles.sub}>{kpi.sub}</div>
              </div>
            </ScrollReveal>
          ))}
        </div>
      </div>
    </section>
  )
}
