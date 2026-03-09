/**
 * BacktestPanel — Walk-Forward Backtest Results
 *
 * Shows equity curve (portfolio vs benchmark), metric cards,
 * and tickers held.
 */

import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";
import type { BacktestResult } from "../types";

interface Props {
  result: BacktestResult;
  onClose: () => void;
}

function pct(n: number, dp = 2): string {
  return `${(n * 100).toFixed(dp)}%`;
}

function fmt(n: number): string {
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  return `$${n.toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
}

export default function BacktestPanel({ result, onClose }: Props) {
  const { portfolio, benchmark_results, alpha, monthly_series } = result;

  const metrics: { label: string; portfolio: string; benchmark: string; color?: string }[] = [
    { label: "CAGR", portfolio: pct(portfolio.cagr), benchmark: pct(benchmark_results.cagr) },
    { label: "Total Return", portfolio: pct(portfolio.total_return), benchmark: pct(benchmark_results.total_return) },
    { label: "Max Drawdown", portfolio: pct(portfolio.max_drawdown), benchmark: pct(benchmark_results.max_drawdown) },
    { label: "Sharpe", portfolio: portfolio.sharpe.toFixed(2), benchmark: benchmark_results.sharpe.toFixed(2) },
    { label: "Calmar", portfolio: portfolio.calmar.toFixed(2), benchmark: benchmark_results.calmar.toFixed(2) },
    { label: "Win Rate", portfolio: pct(portfolio.win_rate ?? 0), benchmark: "—" },
    {
      label: "Alpha",
      portfolio: pct(alpha),
      benchmark: "—",
      color: alpha > 0 ? "text-green-400" : "text-red-400",
    },
  ];

  return (
    <div className="bg-gray-900 rounded-2xl border border-blue-800/50 p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h2 className="text-base font-bold text-blue-300">Walk-Forward Backtest</h2>
          <div className="text-xs text-gray-500 mt-0.5">
            {result.weighting}-weight · Top {result.top_n} · {result.years}yr ·{" "}
            {result.tickers_held.length} tickers held
          </div>
        </div>
        <button onClick={onClose} className="text-gray-500 hover:text-white text-xs">
          ✕ Close
        </button>
      </div>

      {/* Metric cards */}
      <div className="grid grid-cols-7 gap-2 mb-5">
        {metrics.map(({ label, portfolio: pVal, benchmark: bVal, color }) => (
          <div key={label} className="bg-gray-800 rounded-lg p-2 text-center">
            <div className="text-[0.65rem] text-gray-400">{label}</div>
            <div className={`text-sm font-bold ${color ?? "text-blue-400"}`}>{pVal}</div>
            <div className="text-[0.6rem] text-gray-600">Bench: {bVal}</div>
          </div>
        ))}
      </div>

      {/* Equity curve */}
      <ResponsiveContainer width="100%" height={320}>
        <AreaChart data={monthly_series} margin={{ top: 10, right: 20, left: 20, bottom: 10 }}>
          <defs>
            <linearGradient id="portfolioGrad" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
          <XAxis
            dataKey="date"
            tick={{ fill: "#9ca3af", fontSize: 10 }}
            tickFormatter={(v) => v.substring(0, 7)}
            interval={Math.floor(monthly_series.length / 8)}
          />
          <YAxis
            tick={{ fill: "#9ca3af", fontSize: 10 }}
            tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#1f2937",
              border: "1px solid #374151",
              borderRadius: "0.5rem",
              color: "#f9fafb",
              fontSize: "0.75rem",
            }}
            formatter={(value: number, name: string) => [
              fmt(value),
              name === "portfolio_equity" ? "Portfolio" : result.benchmark,
            ]}
          />
          <Legend
            formatter={(value: string) =>
              value === "portfolio_equity" ? "Portfolio" : result.benchmark
            }
          />
          <Area
            type="monotone"
            dataKey="portfolio_equity"
            stroke="#3b82f6"
            strokeWidth={2}
            fill="url(#portfolioGrad)"
          />
          <Area
            type="monotone"
            dataKey="benchmark_equity"
            stroke="#6b7280"
            strokeWidth={1.5}
            strokeDasharray="4 4"
            fill="transparent"
          />
        </AreaChart>
      </ResponsiveContainer>

      {/* Final values */}
      <div className="grid grid-cols-2 gap-4 mt-4">
        <div className="bg-gray-800 rounded-lg p-3 text-center">
          <div className="text-xs text-gray-400">Portfolio Final Value</div>
          <div className="text-lg font-bold text-blue-400">{fmt(portfolio.final_value)}</div>
          <div className="text-[0.65rem] text-gray-500">from {fmt(result.initial_capital)}</div>
        </div>
        <div className="bg-gray-800 rounded-lg p-3 text-center">
          <div className="text-xs text-gray-400">{result.benchmark} Final Value</div>
          <div className="text-lg font-bold text-gray-400">
            {fmt(benchmark_results.final_value)}
          </div>
          <div className="text-[0.65rem] text-gray-500">from {fmt(result.initial_capital)}</div>
        </div>
      </div>

      {/* Tickers held */}
      <div className="mt-4 text-xs text-gray-500">
        <span className="font-semibold text-gray-400">Tickers held: </span>
        {result.tickers_held.join(", ")}
      </div>
    </div>
  );
}
