/**
 * DecisionMatrix — Kelly Sizing Tab
 *
 * Shows the full Kelly criterion calculation, position sizing recommendation,
 * and a comparison table of position sizes at various portfolio values.
 */

import React, { useState } from "react";
import type { KellySizing, MarginOfSafety } from "../types";

interface Props {
  kellySizing: KellySizing;
  marginOfSafety: MarginOfSafety;
  ticker: string;
}

function fmt(n: number, dp = 2): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: dp,
    maximumFractionDigits: dp,
  }).format(n);
}

const PORTFOLIO_SCENARIOS = [50_000, 100_000, 250_000, 500_000, 1_000_000];

export default function DecisionMatrix({ kellySizing: kelly, marginOfSafety: mos, ticker }: Props) {
  const [customPortfolio, setCustomPortfolio] = useState<string>("100000");
  const customValue = parseFloat(customPortfolio) || 100_000;
  const customDollar = customValue * (kelly.kelly_fractional_pct / 100);
  const customShares = Math.floor(customDollar / mos.current_price);

  const ratingColor =
    mos.klarman_score >= 50
      ? "text-green-400 bg-green-900/30"
      : mos.klarman_score >= 25
      ? "text-amber-400 bg-amber-900/30"
      : "text-red-400 bg-red-900/30";

  const verdict =
    mos.passes_mos_threshold
      ? "PASS — Consider initiating a position"
      : "FAIL — Does not meet 30% MoS threshold";

  return (
    <div className="space-y-6">
      {/* Verdict banner */}
      <div
        className={`rounded-xl p-4 border ${
          mos.passes_mos_threshold
            ? "border-green-700 bg-green-900/20 text-green-300"
            : "border-red-700 bg-red-900/20 text-red-300"
        }`}
      >
        <div className="font-bold text-base">{ticker}</div>
        <div className="text-sm mt-0.5">{verdict}</div>
      </div>

      {/* Kelly calculation breakdown */}
      <div className="bg-gray-800 rounded-xl p-4 space-y-3">
        <div className="text-gray-400 text-xs uppercase tracking-wider">Kelly Calculation</div>
        <div className="grid grid-cols-2 gap-3 text-sm">
          {[
            { label: "Full Kelly", value: `${kelly.kelly_full_pct.toFixed(1)}%`, sub: "Before fraction" },
            {
              label: "Quarter-Kelly (×0.25)",
              value: `${kelly.kelly_fractional_pct.toFixed(1)}%`,
              sub: "Applied fraction",
              highlight: true,
            },
            { label: "P(Undervalued)", value: `${(mos.prob_undervalued * 100).toFixed(1)}%`, sub: "Win probability" },
            { label: "MoS vs P25", value: `${(mos.mos_downside * 100).toFixed(1)}%`, sub: "Expected gain" },
          ].map(({ label, value, sub, highlight }) => (
            <div
              key={label}
              className={`rounded-lg p-3 ${highlight ? "bg-blue-900/30 border border-blue-700" : "bg-gray-900"}`}
            >
              <div className="text-gray-400 text-xs">{label}</div>
              <div className={`font-bold text-xl ${highlight ? "text-blue-300" : "text-white"}`}>{value}</div>
              <div className="text-gray-600 text-xs mt-0.5">{sub}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Custom portfolio input */}
      <div className="bg-gray-800 rounded-xl p-4">
        <div className="text-gray-400 text-xs uppercase tracking-wider mb-3">Your Portfolio Size</div>
        <div className="flex items-center gap-3">
          <span className="text-gray-400">$</span>
          <input
            type="number"
            value={customPortfolio}
            onChange={(e) => setCustomPortfolio(e.target.value)}
            className="bg-gray-900 border border-gray-700 rounded px-3 py-2 text-white text-sm w-40 focus:outline-none focus:border-blue-500"
          />
        </div>
        <div className="mt-3 grid grid-cols-3 gap-2 text-center">
          <div className="bg-gray-900 rounded p-2">
            <div className="text-gray-500 text-xs">Allocation %</div>
            <div className="text-white font-bold">{kelly.kelly_fractional_pct.toFixed(1)}%</div>
          </div>
          <div className="bg-gray-900 rounded p-2">
            <div className="text-gray-500 text-xs">Dollar Amount</div>
            <div className="text-blue-400 font-bold">{fmt(customDollar, 0)}</div>
          </div>
          <div className="bg-gray-900 rounded p-2">
            <div className="text-gray-500 text-xs">Shares @ {fmt(mos.current_price)}</div>
            <div className="text-green-400 font-bold">{customShares.toLocaleString()}</div>
          </div>
        </div>
      </div>

      {/* Scenario table */}
      <div className="bg-gray-800 rounded-xl p-4 overflow-x-auto">
        <div className="text-gray-400 text-xs uppercase tracking-wider mb-3">Position Sizing Scenarios</div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-gray-500 border-b border-gray-700">
              <th className="text-left py-2">Portfolio</th>
              <th className="text-right py-2">Allocation</th>
              <th className="text-right py-2">Dollar Amount</th>
              <th className="text-right py-2">Shares</th>
            </tr>
          </thead>
          <tbody>
            {PORTFOLIO_SCENARIOS.map((pv) => {
              const dollars = pv * (kelly.kelly_fractional_pct / 100);
              const shares = Math.floor(dollars / mos.current_price);
              return (
                <tr key={pv} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                  <td className="py-2 text-gray-300">{fmt(pv, 0)}</td>
                  <td className="py-2 text-right text-gray-300">{kelly.kelly_fractional_pct.toFixed(1)}%</td>
                  <td className="py-2 text-right text-blue-400 font-mono">{fmt(dollars, 0)}</td>
                  <td className="py-2 text-right text-green-400 font-mono">{shares.toLocaleString()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
