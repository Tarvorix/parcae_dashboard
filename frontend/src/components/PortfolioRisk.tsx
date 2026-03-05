/**
 * PortfolioRisk — Copula Tail Risk Tab
 *
 * Displays Gaussian copula VaR/CVaR results alongside historical
 * risk metrics for the current open portfolio.
 */

import React, { useState } from "react";
import {
  RadarChart,
  Radar,
  PolarGrid,
  PolarAngleAxis,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import type { PortfolioTailRisk } from "../types";

interface Props {
  riskData: PortfolioTailRisk;
}

function pct(n: number, dp = 2): string {
  return `${(n * 100).toFixed(dp)}%`;
}

export default function PortfolioRisk({ riskData }: Props) {
  const { copula, historical, tickers } = riskData;
  const [tab, setTab] = useState<"copula" | "historical" | "positions">("copula");

  // Radar chart data — normalised risk scores for visual comparison
  const radarData = [
    { metric: "VaR 95", copula: Math.abs(copula.var) * 100, historical: Math.abs(historical.portfolio_var) * 100 },
    { metric: "CVaR 95", copula: Math.abs(copula.cvar) * 100, historical: Math.abs(historical.portfolio_cvar) * 100 },
    { metric: "Max DD", copula: Math.abs(copula.max_drawdown_sim) * 100, historical: Math.abs(historical.portfolio_max_drawdown) * 100 },
    { metric: "Volatility", copula: copula.std_return * 100, historical: historical.portfolio_std_return * 100 },
  ];

  return (
    <div className="space-y-5">
      {/* Portfolio header */}
      <div className="flex flex-wrap gap-2">
        {tickers.map((t) => (
          <span key={t} className="bg-blue-900/40 text-blue-300 text-xs font-mono px-2 py-1 rounded">
            {t}
          </span>
        ))}
      </div>

      {/* Tab switcher */}
      <div className="flex gap-1 bg-gray-800 rounded-lg p-1 w-fit">
        {(["copula", "historical", "positions"] as const).map((t) => (
          <button
            key={t}
            onClick={() => setTab(t)}
            className={`px-4 py-1.5 rounded text-sm capitalize transition-colors ${
              tab === t ? "bg-blue-600 text-white" : "text-gray-400 hover:text-white"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {tab === "copula" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
            {[
              { label: "VaR 95%", value: pct(copula.var), color: "text-red-400" },
              { label: "CVaR 95%", value: pct(copula.cvar), color: "text-red-600" },
              { label: "Max Drawdown", value: pct(copula.max_drawdown_sim), color: "text-amber-400" },
              { label: "Positions", value: String(copula.n_positions), color: "text-blue-400" },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-gray-800 rounded-xl p-4 text-center">
                <div className="text-gray-400 text-xs mb-1">{label}</div>
                <div className={`text-2xl font-bold ${color}`}>{value}</div>
                <div className="text-gray-600 text-xs mt-1">Gaussian Copula</div>
              </div>
            ))}
          </div>

          {/* Weights */}
          <div className="bg-gray-800 rounded-xl p-4">
            <div className="text-gray-400 text-xs uppercase tracking-wider mb-2">
              Equal Weights
            </div>
            <div className="flex flex-wrap gap-2">
              {tickers.map((t, i) => (
                <div key={t} className="flex items-center gap-2 bg-gray-900 rounded px-3 py-1.5 text-sm">
                  <span className="text-blue-400 font-mono">{t}</span>
                  <span className="text-gray-400">{pct(copula.weights[i] ?? 0)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {tab === "historical" && (
        <div className="space-y-4">
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
            {[
              { label: "Historical VaR 95%", value: pct(historical.portfolio_var), color: "text-red-400" },
              { label: "Historical CVaR 95%", value: pct(historical.portfolio_cvar), color: "text-red-600" },
              { label: "Max Drawdown", value: pct(historical.portfolio_max_drawdown), color: "text-amber-400" },
              { label: "Sharpe Ratio", value: historical.portfolio_sharpe.toFixed(2), color: "text-green-400" },
              { label: "Mean Return", value: pct(historical.portfolio_mean_return), color: "text-blue-400" },
              { label: "Std Return", value: pct(historical.portfolio_std_return), color: "text-purple-400" },
            ].map(({ label, value, color }) => (
              <div key={label} className="bg-gray-800 rounded-xl p-4 text-center">
                <div className="text-gray-400 text-xs mb-1">{label}</div>
                <div className={`text-2xl font-bold ${color}`}>{value}</div>
              </div>
            ))}
          </div>

          {/* Comparison radar */}
          <div className="bg-gray-800 rounded-xl p-4">
            <div className="text-gray-400 text-xs uppercase tracking-wider mb-3">
              Copula vs Historical (% per period)
            </div>
            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="#374151" />
                <PolarAngleAxis dataKey="metric" tick={{ fontSize: 11, fill: "#9ca3af" }} />
                <Radar name="Copula" dataKey="copula" stroke="#3b82f6" fill="#3b82f622" strokeWidth={2} />
                <Radar name="Historical" dataKey="historical" stroke="#22c55e" fill="#22c55e22" strokeWidth={2} />
                <Tooltip
                  formatter={(v: number) => `${v.toFixed(2)}%`}
                  contentStyle={{ background: "#1f2937", border: "1px solid #374151", borderRadius: 6 }}
                />
              </RadarChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}

      {tab === "positions" && (
        <div className="overflow-x-auto">
          <table className="w-full text-xs text-right">
            <thead>
              <tr className="text-gray-500 border-b border-gray-700">
                <th className="text-left py-2 pr-4">Ticker</th>
                <th className="py-2 px-2">Weight</th>
                <th className="py-2 px-2">Mean Ret.</th>
                <th className="py-2 px-2">Volatility</th>
                <th className="py-2 px-2">VaR 95%</th>
                <th className="py-2 px-2">CVaR 95%</th>
                <th className="py-2 px-2">Max DD</th>
                <th className="py-2 pl-2">Sharpe</th>
              </tr>
            </thead>
            <tbody>
              {historical.per_position.map((p) => (
                <tr key={p.position_index} className="border-b border-gray-700/50">
                  <td className="text-left py-2 pr-4 text-blue-400 font-bold">
                    {tickers[p.position_index] ?? `P${p.position_index}`}
                  </td>
                  <td className="py-2 px-2 text-gray-300">{pct(p.weight, 0)}</td>
                  <td className={`py-2 px-2 font-mono ${p.mean_return >= 0 ? "text-green-400" : "text-red-400"}`}>
                    {pct(p.mean_return)}
                  </td>
                  <td className="py-2 px-2 font-mono text-purple-400">{pct(p.std_return)}</td>
                  <td className="py-2 px-2 font-mono text-red-400">{pct(p.var)}</td>
                  <td className="py-2 px-2 font-mono text-red-600">{pct(p.cvar)}</td>
                  <td className="py-2 px-2 font-mono text-amber-400">{pct(p.max_drawdown)}</td>
                  <td className="py-2 pl-2 font-mono text-blue-300">{p.sharpe.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
