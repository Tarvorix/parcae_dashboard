/**
 * Watchlist — Ranked Candidates Tab
 *
 * Displays the live screener output sorted by composite screen score.
 * Clicking a row triggers analysis for that ticker.
 */

import React from "react";
import { TrendingUp, TrendingDown } from "lucide-react";
import type { WatchlistCandidate } from "../types";

interface Props {
  candidates: WatchlistCandidate[];
  onSelect: (ticker: string) => void;
  selectedTicker: string | null;
  loading: boolean;
}

function fmtB(n: number): string {
  if (n >= 1e12) return `$${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `$${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `$${(n / 1e6).toFixed(0)}M`;
  return `$${n.toFixed(0)}`;
}

export default function Watchlist({ candidates, onSelect, selectedTicker, loading }: Props) {
  if (loading) {
    return (
      <div className="flex items-center justify-center h-48 text-gray-500">
        <div className="text-center">
          <div className="animate-spin w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-3" />
          <div className="text-sm">Running Klarman screen across S&P 500…</div>
        </div>
      </div>
    );
  }

  if (candidates.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-gray-500">
        <TrendingDown size={40} className="mb-3 opacity-40" />
        <div className="text-sm">No candidates pass Klarman filters today</div>
        <div className="text-xs mt-1 text-gray-600">
          EV/EBIT ≤ 10 · FCF Yield ≥ 7% · P/TBV ≤ 1.2
        </div>
      </div>
    );
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="text-gray-500 text-xs border-b border-gray-700">
            <th className="text-left py-2 pr-3">#</th>
            <th className="text-left py-2 pr-4">Ticker</th>
            <th className="text-left py-2 pr-4">Name</th>
            <th className="text-right py-2 px-3">Price</th>
            <th className="text-right py-2 px-3">Mkt Cap</th>
            <th className="text-right py-2 px-3">EV/EBIT</th>
            <th className="text-right py-2 px-3">FCF Yield</th>
            <th className="text-right py-2 px-3">P/TBV</th>
            <th className="text-right py-2 px-3">Sector</th>
            <th className="text-right py-2 pl-3">Score</th>
          </tr>
        </thead>
        <tbody>
          {candidates.map((c, i) => (
            <tr
              key={c.ticker}
              onClick={() => onSelect(c.ticker)}
              className={`border-b border-gray-700/50 cursor-pointer transition-colors ${
                selectedTicker === c.ticker
                  ? "bg-blue-900/30 border-blue-700"
                  : "hover:bg-gray-700/30"
              }`}
            >
              <td className="py-2 pr-3 text-gray-600">{i + 1}</td>
              <td className="py-2 pr-4 font-bold text-blue-400">{c.ticker}</td>
              <td className="py-2 pr-4 text-gray-300 max-w-[160px] truncate">{c.name}</td>
              <td className="py-2 px-3 text-right font-mono">
                ${c.price?.toFixed(2) ?? "—"}
              </td>
              <td className="py-2 px-3 text-right text-gray-400 font-mono">
                {c.market_cap ? fmtB(c.market_cap) : "—"}
              </td>
              <td className="py-2 px-3 text-right font-mono text-amber-400">
                {c.ev_ebit?.toFixed(1) ?? "—"}×
              </td>
              <td className="py-2 px-3 text-right font-mono text-green-400">
                {c.fcf_yield_pct?.toFixed(1) ?? "—"}%
              </td>
              <td className="py-2 px-3 text-right font-mono text-purple-400">
                {c.price_tangible_book?.toFixed(2) ?? "—"}×
              </td>
              <td className="py-2 px-3 text-right text-gray-500 text-xs max-w-[100px] truncate">
                {c.sector ?? "—"}
              </td>
              <td className="py-2 pl-3 text-right">
                <span className="bg-blue-900/40 text-blue-300 font-mono text-xs px-2 py-0.5 rounded">
                  {c.screen_score?.toFixed(3) ?? "—"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
