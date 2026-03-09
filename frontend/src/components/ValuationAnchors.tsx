/**
 * ValuationAnchors — EPV + NCAV multi-method valuation comparison tab.
 *
 * Shows a horizontal bar chart comparing Price vs NCAV vs EPV vs DCF percentiles,
 * plus detail cards for EPV (Greenwald) and NCAV (Graham) calculations.
 */

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Cell,
  LabelList,
} from "recharts";
import { TrendingUp, TrendingDown, Shield, Building } from "lucide-react";
import type { ValuationAnchors as ValuationAnchorsType, MarginOfSafety } from "../types";

interface Props {
  anchors: ValuationAnchorsType;
  mos: MarginOfSafety;
}

function fmt(n: number): string {
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  return `$${n.toFixed(2)}`;
}

function pct(n: number, dp = 1): string {
  return `${(n * 100).toFixed(dp)}%`;
}

const COLORS = {
  purple: "#a78bfa",
  white: "#f9fafb",
  amber: "#fbbf24",
  blue: "#3b82f6",
  green: "#22c55e",
  cyan: "#06b6d4",
  red: "#ef4444",
  gray400: "#9ca3af",
  gray600: "#4b5563",
  gray700: "#374151",
  gray800: "#1f2937",
};

export default function ValuationAnchors({ anchors, mos }: Props) {
  const { epv, ncav } = anchors;

  if (!epv && !ncav) {
    return (
      <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-8 text-center text-gray-400">
        Valuation anchors unavailable — insufficient financial data.
      </div>
    );
  }

  // Build comparison data for chart
  const chartData: { name: string; value: number; color: string }[] = [];

  if (ncav?.ncav_per_share != null) {
    chartData.push({ name: "NCAV/Share", value: ncav.ncav_per_share, color: COLORS.purple });
  }
  chartData.push({ name: "Current Price", value: mos.current_price, color: COLORS.white });
  if (mos.p25) chartData.push({ name: "DCF P25", value: mos.p25, color: COLORS.amber });
  if (epv?.epv_per_share != null) {
    chartData.push({ name: "EPV/Share", value: epv.epv_per_share, color: COLORS.blue });
  }
  if (mos.p50) chartData.push({ name: "DCF P50", value: mos.p50, color: COLORS.green });
  if (mos.p75) chartData.push({ name: "DCF P75", value: mos.p75, color: COLORS.cyan });

  // Sort by value ascending for visual clarity
  chartData.sort((a, b) => a.value - b.value);

  return (
    <div className="space-y-6">
      {/* Bar chart comparison */}
      <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4">
        <h3 className="mb-4 text-sm font-semibold text-gray-400">
          Valuation Method Comparison
        </h3>
        <ResponsiveContainer width="100%" height={300}>
          <BarChart data={chartData} margin={{ top: 20, right: 30, left: 20, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
            <XAxis dataKey="name" tick={{ fill: "#9ca3af", fontSize: 12 }} />
            <YAxis tick={{ fill: "#9ca3af", fontSize: 12 }} tickFormatter={(v) => `$${v}`} />
            <Tooltip
              contentStyle={{
                backgroundColor: "#1f2937",
                border: "1px solid #374151",
                borderRadius: "0.5rem",
                color: "#f9fafb",
              }}
              formatter={(value: number) => [fmt(value), "Price"]}
            />
            <Bar dataKey="value" radius={[4, 4, 0, 0]}>
              {chartData.map((entry, index) => (
                <Cell key={index} fill={entry.color} />
              ))}
              <LabelList
                dataKey="value"
                position="top"
                fill="#9ca3af"
                fontSize={11}
                formatter={(v: number) => fmt(v)}
              />
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Detail cards */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* EPV Card */}
        <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Building className="h-4 w-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-gray-400">
              Earnings Power Value (Greenwald)
            </h3>
          </div>
          {epv ? (
            <>
              <div className="mb-3 text-center">
                <div className="text-2xl font-bold text-blue-400">
                  {fmt(epv.epv_per_share)}
                </div>
                <div className="text-xs text-gray-500">per share</div>
              </div>
              <div className="space-y-1">
                {[
                  ["NOPAT", fmt(epv.nopat)],
                  ["WACC", pct(epv.wacc)],
                  ["Tax Rate", pct(epv.tax_rate_used)],
                  ["EPV Total", fmt(epv.epv_total)],
                  ["Franchise Value", fmt(epv.franchise_value)],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    className="flex items-center justify-between border-b border-gray-700/50 px-2 py-1.5 text-sm"
                  >
                    <span className="text-gray-400">{label}</span>
                    <span className="font-medium text-gray-200">{value}</span>
                  </div>
                ))}
              </div>
              <div
                className={`mt-3 rounded-lg py-1.5 text-center text-sm font-semibold ${
                  epv.has_franchise
                    ? "bg-green-900/30 text-green-400"
                    : "bg-red-900/30 text-red-400"
                }`}
              >
                {epv.has_franchise ? (
                  <span className="flex items-center justify-center gap-1">
                    <Shield className="h-3.5 w-3.5" /> Franchise Moat
                  </span>
                ) : (
                  "No Franchise"
                )}
              </div>
            </>
          ) : (
            <div className="py-8 text-center text-sm text-gray-500">
              EPV unavailable — missing EBIT or shares data.
            </div>
          )}
        </div>

        {/* NCAV Card */}
        <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Shield className="h-4 w-4 text-purple-400" />
            <h3 className="text-sm font-semibold text-gray-400">
              Net Current Asset Value (Graham)
            </h3>
          </div>
          {ncav ? (
            <>
              <div className="mb-3 text-center">
                <div className="text-2xl font-bold text-purple-400">
                  {fmt(ncav.ncav_per_share)}
                </div>
                <div className="text-xs text-gray-500">per share</div>
              </div>
              <div className="space-y-1">
                {[
                  ["Current Assets", fmt(ncav.current_assets)],
                  ["Total Liabilities", fmt(ncav.total_liabilities)],
                  ["NCAV Total", fmt(ncav.ncav_total)],
                  ["NCAV/Share", fmt(ncav.ncav_per_share)],
                  ["Discount to NCAV", pct(ncav.discount_to_ncav)],
                ].map(([label, value]) => (
                  <div
                    key={label}
                    className="flex items-center justify-between border-b border-gray-700/50 px-2 py-1.5 text-sm"
                  >
                    <span className="text-gray-400">{label}</span>
                    <span className="font-medium text-gray-200">{value}</span>
                  </div>
                ))}
              </div>
              <div
                className={`mt-3 rounded-lg py-1.5 text-center text-sm font-semibold ${
                  ncav.trades_below_ncav
                    ? "bg-green-900/30 text-green-400"
                    : "bg-red-900/30 text-red-400"
                }`}
              >
                {ncav.trades_below_ncav ? (
                  <span className="flex items-center justify-center gap-1">
                    <TrendingDown className="h-3.5 w-3.5" /> Trades Below NCAV
                  </span>
                ) : (
                  <span className="flex items-center justify-center gap-1">
                    <TrendingUp className="h-3.5 w-3.5" /> Trades Above NCAV
                  </span>
                )}
              </div>
            </>
          ) : (
            <div className="py-8 text-center text-sm text-gray-500">
              NCAV unavailable — missing current assets or liabilities data.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
