/**
 * QualityPanel — Quality & Distress Scoring Tab
 *
 * Displays Piotroski F-Score (0-9), Altman Z-Score, Beneish M-Score
 * with score cards, component checklists, and ratio tables.
 */

import React from "react";
import { CheckCircle, XCircle, AlertTriangle, Shield, Activity } from "lucide-react";
import type { QualityScores } from "../types";

interface Props {
  scores: QualityScores;
}

function pct(n: number, dp = 1): string {
  return `${(n * 100).toFixed(dp)}%`;
}

function scoreColor(score: number, max: number): string {
  const pct = score / max;
  if (pct >= 0.78) return "text-green-400";
  if (pct >= 0.44) return "text-amber-400";
  return "text-red-400";
}

function zoneBorderColor(zone: string): string {
  if (zone === "Safe") return "border-green-500";
  if (zone === "Grey") return "border-amber-500";
  return "border-red-500";
}

function zoneTextColor(zone: string): string {
  if (zone === "Safe") return "text-green-400";
  if (zone === "Grey") return "text-amber-400";
  return "text-red-400";
}

const PIOTROSKI_LABELS: Record<string, string> = {
  roa_positive: "ROA > 0 (Positive net income / total assets)",
  cfo_positive: "CFO > 0 (Positive operating cash flow)",
  delta_roa_positive: "ROA Improving (YoY increase)",
  accrual_quality: "Accrual Quality (CFO > Net Income)",
  delta_leverage_down: "Leverage Decreasing (LTD/TA declining)",
  delta_current_ratio_up: "Current Ratio Improving (YoY increase)",
  no_dilution: "No Dilution (Shares stable or decreasing)",
  delta_gross_margin_up: "Gross Margin Improving (YoY increase)",
  delta_asset_turnover_up: "Asset Turnover Improving (Rev/TA increasing)",
};

const ALTMAN_LABELS: Record<string, [string, number]> = {
  x1_working_capital_ta: ["X1: Working Capital / Total Assets", 1.2],
  x2_retained_earnings_ta: ["X2: Retained Earnings / Total Assets", 1.4],
  x3_ebit_ta: ["X3: EBIT / Total Assets", 3.3],
  x4_market_cap_tl: ["X4: Market Cap / Total Liabilities", 0.6],
  x5_revenue_ta: ["X5: Revenue / Total Assets", 1.0],
};

const BENEISH_LABELS: Record<string, [string, string]> = {
  dsri: ["DSRI — Days Sales in Receivables Index", "Rising receivables vs revenue"],
  gmi: ["GMI — Gross Margin Index", ">1 = deteriorating margins"],
  aqi: ["AQI — Asset Quality Index", "Non-current asset growth vs total"],
  sgi: ["SGI — Sales Growth Index", "Revenue growth rate"],
  depi: ["DEPI — Depreciation Index", ">1 = slowing depreciation"],
  sgai: ["SGAI — SGA Expense Index", "SGA growth vs revenue growth"],
  tata: ["TATA — Total Accruals to Total Assets", "Earnings quality signal"],
  lvgi: ["LVGI — Leverage Index", ">1 = increasing leverage"],
};

function isBeneishConcern(key: string, val: number): boolean {
  if (key === "dsri" && val > 1.05) return true;
  if (key === "gmi" && val > 1.0) return true;
  if (key === "aqi" && val > 1.0) return true;
  if (key === "sgi" && val > 1.2) return true;
  if (key === "tata" && val > 0.05) return true;
  if (key === "lvgi" && val > 1.1) return true;
  return false;
}

export default function QualityPanel({ scores }: Props) {
  const { piotroski, altman, beneish } = scores;

  if (!piotroski && !altman && !beneish) {
    return (
      <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-8 text-center text-gray-400">
        Quality scores unavailable — insufficient financial data.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Score cards row */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        {/* Piotroski */}
        <div
          className={`rounded-xl border bg-gray-800/50 p-4 text-center ${
            piotroski
              ? piotroski.f_score >= 7
                ? "border-green-500"
                : piotroski.f_score >= 4
                  ? "border-amber-500"
                  : "border-red-500"
              : "border-gray-700"
          }`}
        >
          <div className="text-xs text-gray-400">Piotroski F-Score</div>
          {piotroski ? (
            <>
              <div className={`text-4xl font-extrabold ${scoreColor(piotroski.f_score, 9)}`}>
                {piotroski.f_score} / 9
              </div>
              <div className="text-xs text-gray-500">{piotroski.classification}</div>
            </>
          ) : (
            <>
              <div className="text-4xl font-extrabold text-gray-600">N/A</div>
              <div className="text-xs text-gray-500">Insufficient EDGAR data</div>
            </>
          )}
        </div>

        {/* Altman */}
        <div
          className={`rounded-xl border bg-gray-800/50 p-4 text-center ${
            altman ? zoneBorderColor(altman.zone) : "border-gray-700"
          }`}
        >
          <div className="text-xs text-gray-400">Altman Z-Score</div>
          {altman ? (
            <>
              <div className={`text-4xl font-extrabold ${zoneTextColor(altman.zone)}`}>
                {altman.z_score.toFixed(2)}
              </div>
              <div className="text-xs text-gray-500">{altman.zone}</div>
            </>
          ) : (
            <>
              <div className="text-4xl font-extrabold text-gray-600">N/A</div>
              <div className="text-xs text-gray-500">Missing balance sheet data</div>
            </>
          )}
        </div>

        {/* Beneish */}
        <div
          className={`rounded-xl border bg-gray-800/50 p-4 text-center ${
            beneish
              ? beneish.likely_manipulator
                ? "border-red-500"
                : "border-green-500"
              : "border-gray-700"
          }`}
        >
          <div className="text-xs text-gray-400">Beneish M-Score</div>
          {beneish ? (
            <>
              <div
                className={`text-4xl font-extrabold ${
                  beneish.likely_manipulator ? "text-red-400" : "text-green-400"
                }`}
              >
                {beneish.m_score.toFixed(2)}
              </div>
              <div className="text-xs text-gray-500">
                {beneish.likely_manipulator ? "Likely Manipulator" : "Unlikely Manipulator"}
              </div>
            </>
          ) : (
            <>
              <div className="text-4xl font-extrabold text-gray-600">N/A</div>
              <div className="text-xs text-gray-500">Insufficient EDGAR data</div>
            </>
          )}
        </div>
      </div>

      {/* Piotroski 9-Item Checklist */}
      {piotroski && (
        <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Shield className="h-4 w-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-gray-400">
              Piotroski F-Score Components
            </h3>
          </div>
          <div className="space-y-0.5">
            {Object.entries(PIOTROSKI_LABELS).map(([key, label]) => {
              const passed = (piotroski.components as unknown as Record<string, boolean>)[key];
              return (
                <div
                  key={key}
                  className="flex items-center justify-between border-b border-gray-700/50 px-2 py-1.5 text-sm"
                >
                  <span className="flex items-center gap-2">
                    {passed ? (
                      <CheckCircle className="h-4 w-4 text-green-400" />
                    ) : (
                      <XCircle className="h-4 w-4 text-red-400" />
                    )}
                    <span className="text-gray-300">{label}</span>
                  </span>
                  <span
                    className={`font-semibold ${passed ? "text-green-400" : "text-red-400"}`}
                  >
                    {passed ? "PASS" : "FAIL"}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Altman Z-Score Components */}
      {altman && (
        <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Activity className="h-4 w-4 text-amber-400" />
            <h3 className="text-sm font-semibold text-gray-400">
              Altman Z-Score Components
            </h3>
          </div>
          <div className="space-y-0.5">
            {Object.entries(ALTMAN_LABELS).map(([key, [label, weight]]) => {
              const val = (altman.components as unknown as Record<string, number>)[key] ?? 0;
              const weighted = val * weight;
              return (
                <div
                  key={key}
                  className="flex items-center justify-between border-b border-gray-700/50 px-2 py-1.5 text-sm"
                >
                  <span className="text-gray-300">{label}</span>
                  <span className="flex gap-4">
                    <span className="text-gray-500">
                      Ratio: {val.toFixed(4)}
                    </span>
                    <span className="font-semibold text-blue-400">
                      Weighted: {weighted.toFixed(4)}
                    </span>
                  </span>
                </div>
              );
            })}
          </div>
          <div className="mt-3 flex justify-center gap-4 text-xs">
            <span className="text-green-400">Safe &gt; 2.99</span>
            <span className="text-amber-400">Grey 1.81 – 2.99</span>
            <span className="text-red-400">Distress &lt; 1.81</span>
          </div>
        </div>
      )}

      {/* Beneish M-Score Components */}
      {beneish && (
        <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-red-400" />
            <h3 className="text-sm font-semibold text-gray-400">
              Beneish M-Score Variables
            </h3>
          </div>
          <div className="space-y-0.5">
            {Object.entries(BENEISH_LABELS).map(([key, [label, tooltip]]) => {
              const val = (beneish.components as unknown as Record<string, number>)[key] ?? 0;
              const concern = isBeneishConcern(key, val);
              return (
                <div
                  key={key}
                  className="flex items-center justify-between border-b border-gray-700/50 px-2 py-1.5 text-sm"
                  title={tooltip}
                >
                  <span className="text-gray-300">{label}</span>
                  <span className={`font-semibold ${concern ? "text-red-400" : "text-green-400"}`}>
                    {val.toFixed(4)}
                  </span>
                </div>
              );
            })}
          </div>
          <div
            className={`mt-3 text-center text-xs ${
              beneish.likely_manipulator ? "text-red-400" : "text-green-400"
            }`}
          >
            M-Score = {beneish.m_score.toFixed(2)} — Threshold: -1.78 (M &gt; -1.78 = likely
            manipulation)
          </div>
        </div>
      )}
    </div>
  );
}
