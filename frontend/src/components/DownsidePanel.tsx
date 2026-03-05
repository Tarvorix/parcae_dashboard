/**
 * DownsidePanel — Klarman Checklist Tab
 *
 * Shows the downside-focused analysis: Klarman score, MoS breakdown,
 * and a pass/fail checklist for each Klarman criterion.
 */

import React from "react";
import { CheckCircle, XCircle, AlertCircle } from "lucide-react";
import type { AnalysisResult } from "../types";

interface Props {
  analysis: AnalysisResult;
}

interface CheckItem {
  label: string;
  value: string;
  pass: boolean | null;
  threshold: string;
}

function pct(n: number, dp = 1): string {
  return `${(n * 100).toFixed(dp)}%`;
}

function fmt(n: number): string {
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  return `$${n.toFixed(2)}`;
}

export default function DownsidePanel({ analysis }: Props) {
  const { margin_of_safety: mos, distributions: dist } = analysis;

  const checks: CheckItem[] = [
    {
      label: "Margin of Safety vs P25 (Klarman)",
      value: pct(mos.mos_downside),
      pass: mos.mos_downside >= 0.30,
      threshold: "≥ 30%",
    },
    {
      label: "Probability Undervalued",
      value: pct(mos.prob_undervalued),
      pass: mos.prob_undervalued >= 0.65,
      threshold: "≥ 65%",
    },
    {
      label: "FCF Margin (base case)",
      value: pct(dist.fcf_margin.base),
      pass: dist.fcf_margin.base >= 0.05,
      threshold: "≥ 5%",
    },
    {
      label: "FCF Margin (bear case)",
      value: pct(dist.fcf_margin.bear),
      pass: dist.fcf_margin.bear > 0,
      threshold: "> 0% (stays FCF positive in downside)",
    },
    {
      label: "Revenue Growth (base case)",
      value: pct(dist.revenue_growth.base),
      pass: dist.revenue_growth.base > -0.05,
      threshold: "> −5% (not structurally declining)",
    },
    {
      label: "Discount Rate (bear case)",
      value: pct(dist.discount_rate.bear),
      pass: dist.discount_rate.bear >= 0.10,
      threshold: "≥ 10% (adequately risk-adjusted)",
    },
  ];

  const passCount = checks.filter((c) => c.pass).length;
  const scoreColor =
    mos.klarman_score >= 50
      ? "text-green-400"
      : mos.klarman_score >= 25
      ? "text-amber-400"
      : "text-red-400";

  return (
    <div className="space-y-6">
      {/* Klarman Score hero */}
      <div className="bg-gray-800 rounded-xl p-6 text-center">
        <div className="text-gray-400 text-sm mb-1">Klarman Score</div>
        <div className={`text-6xl font-bold ${scoreColor}`}>
          {mos.klarman_score.toFixed(1)}
        </div>
        <div className="text-gray-500 text-xs mt-1">out of 100</div>
        <div className="mt-3 text-sm text-gray-300">
          {passCount} / {checks.length} criteria passed
        </div>
      </div>

      {/* Percentile table */}
      <div className="bg-gray-800 rounded-xl p-4">
        <div className="text-gray-400 text-xs mb-3 uppercase tracking-wider">
          Intrinsic Value Distribution
        </div>
        <div className="grid grid-cols-5 gap-2 text-center">
          {[
            { label: "P10", value: mos.p10, color: "text-red-400" },
            { label: "P25", value: mos.p25, color: "text-amber-400" },
            { label: "P50", value: mos.p50, color: "text-green-400" },
            { label: "P75", value: mos.p75, color: "text-blue-400" },
            { label: "P90", value: mos.p90, color: "text-purple-400" },
          ].map(({ label, value, color }) => (
            <div key={label} className="bg-gray-900 rounded p-2">
              <div className="text-gray-500 text-xs">{label}</div>
              <div className={`font-bold text-sm ${color}`}>{fmt(value)}</div>
            </div>
          ))}
        </div>
        <div className="mt-2 text-center">
          <span className="text-gray-500 text-xs">Current Price: </span>
          <span className="text-white font-bold text-sm">{fmt(mos.current_price)}</span>
        </div>
      </div>

      {/* Checklist */}
      <div className="bg-gray-800 rounded-xl p-4 space-y-3">
        <div className="text-gray-400 text-xs uppercase tracking-wider mb-2">
          Klarman Criteria Checklist
        </div>
        {checks.map((item) => (
          <div key={item.label} className="flex items-start gap-3">
            <div className="mt-0.5 flex-shrink-0">
              {item.pass === null ? (
                <AlertCircle className="text-gray-500" size={18} />
              ) : item.pass ? (
                <CheckCircle className="text-green-400" size={18} />
              ) : (
                <XCircle className="text-red-400" size={18} />
              )}
            </div>
            <div className="flex-1 min-w-0">
              <div className="text-sm text-gray-200">{item.label}</div>
              <div className="text-xs text-gray-500">Threshold: {item.threshold}</div>
            </div>
            <div
              className={`text-sm font-mono font-bold ${
                item.pass ? "text-green-400" : "text-red-400"
              }`}
            >
              {item.value}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
