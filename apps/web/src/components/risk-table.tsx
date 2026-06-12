"use client";

import { ChevronRight } from "lucide-react";
import { useState } from "react";

import type { RiskPoint } from "@/lib/demo-data";

type RiskTableProps = {
  riskPoints: RiskPoint[];
  onSelect?: (pointCode: string) => void;
};

export function RiskTable({ riskPoints, onSelect }: RiskTableProps) {
  const [selected, setSelected] = useState(riskPoints[0].code);

  return (
    <section className="panel risk-panel">
      <div className="panel-heading">
        <div>
          <span className="eyebrow">POINT RISK</span>
          <h2>点位质量风险</h2>
        </div>
        <button className="text-button">查看全部 38 个点位</button>
      </div>
      <div className="risk-table" role="table" aria-label="点位风险">
        <div className="risk-row risk-head" role="row">
          <span>测量点</span>
          <span>预测指标</span>
          <span>预测值 / 标准</span>
          <span>风险</span>
          <span />
        </div>
        {riskPoints.map((point) => (
          <button
            className={`risk-row ${selected === point.code ? "risk-row-selected" : ""}`}
            key={point.code}
            onClick={() => {
              setSelected(point.code);
              onSelect?.(point.code);
            }}
            role="row"
          >
            <span className="point-identity">
              <strong>{point.name}</strong>
              <span>
                {point.part} · <span className="mono">{point.code}</span>
              </span>
            </span>
            <strong>{point.metric}</strong>
            <span className="value-standard">
              <strong>{point.predicted}</strong>
              <span>{point.standard}</span>
            </span>
            <span className="risk-meter">
              <span className="risk-meter-track">
                <span style={{ width: `${point.risk}%` }} />
              </span>
              <strong>{point.risk}</strong>
            </span>
            <ChevronRight aria-hidden="true" />
          </button>
        ))}
      </div>
    </section>
  );
}
