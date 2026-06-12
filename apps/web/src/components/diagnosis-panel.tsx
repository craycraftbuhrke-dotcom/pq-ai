import { BrainCircuit, CircleHelp, TrendingDown, TrendingUp } from "lucide-react";

import type { DiagnosisFactor } from "@/lib/dashboard-data";

type DiagnosisPanelProps = {
  pointCode: string;
  summary: string;
  confidence: number;
  factors: DiagnosisFactor[];
};

export function DiagnosisPanel({
  pointCode,
  summary,
  confidence,
  factors,
}: DiagnosisPanelProps) {
  return (
    <section className="panel diagnosis-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">AI DIAGNOSIS</span>
          <h2>AI 诊断</h2>
        </div>
        <span className="confidence">置信度 {Math.round(confidence * 100)}%</span>
      </div>
      <div className="diagnosis-lead">
        <BrainCircuit aria-hidden="true" />
        <p>
          <strong className="mono">{pointCode}</strong>：{summary}
        </p>
      </div>
      <div className="factor-list">
        {factors.map((factor) => (
          <div className="factor-row" key={factor.name}>
            <span className="factor-direction">
              {factor.direction === "negative" ? (
                <TrendingDown aria-label="负向影响" />
              ) : (
                <TrendingUp aria-label="正向影响" />
              )}
            </span>
            <span className="factor-name">{factor.name}</span>
            <span className="factor-bar">
              <span style={{ width: `${factor.impact * 200}%` }} />
            </span>
            <strong>{Math.round(factor.impact * 100)}%</strong>
          </div>
        ))}
      </div>
      <p className="diagnosis-note">
        <CircleHelp aria-hidden="true" />
        当前结论为相关性诊断，执行推荐并复测后才能确认为已验证原因。
      </p>
    </section>
  );
}
