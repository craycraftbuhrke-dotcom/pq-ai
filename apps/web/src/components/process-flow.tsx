import { ArrowRight, Gauge } from "lucide-react";

import { StatusBadge } from "@/components/status-badge";
import type { ProcessStage } from "@/lib/demo-data";

type ProcessFlowProps = {
  stages: ProcessStage[];
};

export function ProcessFlow({ stages }: ProcessFlowProps) {
  return (
    <section className="panel process-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">PROCESS CHAIN</span>
          <h2>五段喷涂工艺状态</h2>
        </div>
        <div className="panel-meta">
          <span className="live-dot" />
          实时参数已同步
        </div>
      </div>
      <div className="process-flow">
        {stages.map((stage, index) => (
          <div className="process-step-wrap" key={stage.code}>
            <article className={`process-step process-step-${stage.status}`}>
              <div className="process-step-top">
                <span className="step-order">{String(index + 1).padStart(2, "0")}</span>
                <StatusBadge tone={stage.status}>{stage.health}%</StatusBadge>
              </div>
              <div>
                <h3>{stage.name}</h3>
                <span className="mono">{stage.station}</span>
              </div>
              <div className="step-metrics">
                <span>
                  <Gauge aria-hidden="true" />
                  流量 <strong>{stage.flow}</strong>
                </span>
                <span>
                  RPM <strong>{stage.rpm.toLocaleString()}</strong>
                </span>
              </div>
              <div className="health-track">
                <span style={{ width: `${stage.health}%` }} />
              </div>
            </article>
            {index < stages.length - 1 ? (
              <ArrowRight className="flow-arrow" aria-hidden="true" />
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}
