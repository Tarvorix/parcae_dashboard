/**
 * FlowSignals — Insider Transactions, Institutional Holdings, Short Interest
 *
 * Displays summary cards, insider transaction list, notable holders,
 * and top institutional holders.
 */

import React from "react";
import { TrendingUp, TrendingDown, Users, AlertTriangle, UserCheck } from "lucide-react";

// ── Types ────────────────────────────────────────────────────────────────────

interface InsiderTransaction {
  owner: string;
  is_director: boolean;
  is_officer: boolean;
  is_ten_pct_owner: boolean;
  officer_title: string;
  transaction_type: "Buy" | "Sell";
  shares: number;
  price: number;
  value: number;
  transaction_code: string;
  date: string;
}

interface InsiderSummary {
  total_bought: number;
  total_sold: number;
  net_buying: number;
  n_buyers: number;
  n_sellers: number;
  n_transactions: number;
  cluster_buy_detected: boolean;
  cluster_buy_count: number;
}

interface InsiderData {
  transactions: InsiderTransaction[];
  summary: InsiderSummary;
}

interface InstitutionalHolder {
  name: string;
  shares: number;
  pct_held: number;
  value: number;
}

interface InstitutionalData {
  notable_holders: InstitutionalHolder[];
  n_notable_holders: number;
  top_holders: InstitutionalHolder[];
}

interface ShortInterestData {
  short_percent_of_float: number | null;
  short_ratio: number | null;
  short_interest_high: boolean;
}

interface FlowSignalsData {
  insider: InsiderData | null;
  institutional: InstitutionalData | null;
  short_interest: ShortInterestData;
}

interface Props {
  signals: FlowSignalsData;
}

function fmtDollars(n: number): string {
  if (Math.abs(n) >= 1e9) return `$${(n / 1e9).toFixed(2)}B`;
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(0)}K`;
  return `$${n.toLocaleString()}`;
}

export default function FlowSignals({ signals }: Props) {
  const { insider, institutional, short_interest } = signals;

  return (
    <div className="space-y-6">
      {/* Summary cards */}
      <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
        {/* Net Insider Buying */}
        <div
          className={`rounded-xl border bg-gray-800/50 p-4 text-center ${
            insider?.summary
              ? insider.summary.net_buying > 0
                ? "border-green-500"
                : "border-red-500"
              : "border-gray-700"
          }`}
        >
          <div className="text-xs text-gray-400">Net Insider Buying</div>
          {insider?.summary ? (
            <>
              <div
                className={`text-xl font-extrabold ${
                  insider.summary.net_buying > 0 ? "text-green-400" : "text-red-400"
                }`}
              >
                {fmtDollars(insider.summary.net_buying)}
              </div>
              <div className="text-[0.65rem] text-gray-500">
                {insider.summary.n_transactions} transactions
              </div>
            </>
          ) : (
            <div className="text-xl font-extrabold text-gray-600">N/A</div>
          )}
        </div>

        {/* Cluster Buy Alert */}
        <div
          className={`rounded-xl border bg-gray-800/50 p-4 text-center ${
            insider?.summary?.cluster_buy_detected ? "border-green-500" : "border-gray-700"
          }`}
        >
          <div className="text-xs text-gray-400">Cluster Buy Alert</div>
          {insider?.summary?.cluster_buy_detected ? (
            <>
              <div className="text-xl font-extrabold text-green-400">
                {insider.summary.cluster_buy_count} insiders
              </div>
              <div className="text-[0.65rem] text-gray-500">within 90 days</div>
            </>
          ) : (
            <div className="text-xl font-extrabold text-gray-600">None</div>
          )}
        </div>

        {/* Short % of Float */}
        <div
          className={`rounded-xl border bg-gray-800/50 p-4 text-center ${
            short_interest.short_interest_high
              ? "border-red-500"
              : short_interest.short_percent_of_float != null
                ? "border-green-500"
                : "border-gray-700"
          }`}
        >
          <div className="text-xs text-gray-400">Short % of Float</div>
          <div
            className={`text-xl font-extrabold ${
              short_interest.short_interest_high
                ? "text-red-400"
                : short_interest.short_percent_of_float != null
                  ? "text-green-400"
                  : "text-gray-600"
            }`}
          >
            {short_interest.short_percent_of_float != null
              ? `${(short_interest.short_percent_of_float * 100).toFixed(1)}%`
              : "N/A"}
          </div>
          <div className="text-[0.65rem] text-gray-500">
            {short_interest.short_interest_high ? "HIGH" : short_interest.short_percent_of_float != null ? "Normal" : ""}
          </div>
        </div>

        {/* Notable Value Investors */}
        <div
          className={`rounded-xl border bg-gray-800/50 p-4 text-center ${
            institutional && institutional.n_notable_holders > 0
              ? "border-green-500"
              : "border-gray-700"
          }`}
        >
          <div className="text-xs text-gray-400">Notable Value Investors</div>
          <div
            className={`text-xl font-extrabold ${
              institutional && institutional.n_notable_holders > 0 ? "text-green-400" : "text-gray-600"
            }`}
          >
            {institutional ? institutional.n_notable_holders : "N/A"}
          </div>
          <div className="text-[0.65rem] text-gray-500">tracked firms</div>
        </div>
      </div>

      {/* Insider Transactions Table */}
      {insider && insider.transactions.length > 0 && (
        <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <UserCheck className="h-4 w-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-gray-400">Recent Insider Transactions</h3>
          </div>
          <div className="space-y-0.5">
            {insider.transactions.slice(0, 20).map((txn, i) => (
              <div
                key={i}
                className="flex items-center justify-between border-b border-gray-700/50 px-2 py-1.5 text-sm"
              >
                <span className="flex items-center gap-2">
                  {txn.transaction_type === "Buy" ? (
                    <TrendingUp className="h-3.5 w-3.5 text-green-400" />
                  ) : (
                    <TrendingDown className="h-3.5 w-3.5 text-red-400" />
                  )}
                  <span className="text-gray-300">
                    {txn.owner}
                    {txn.officer_title && (
                      <span className="text-gray-500 ml-1">({txn.officer_title})</span>
                    )}
                  </span>
                  <span className="text-gray-600 text-xs">{txn.date}</span>
                </span>
                <span className="flex items-center gap-3">
                  <span
                    className={`font-semibold ${
                      txn.transaction_type === "Buy" ? "text-green-400" : "text-red-400"
                    }`}
                  >
                    {txn.transaction_type}
                  </span>
                  <span className="text-gray-400 text-xs">
                    {txn.shares.toLocaleString()} @ ${txn.price.toFixed(2)}
                  </span>
                  <span className="font-semibold text-gray-300">{fmtDollars(txn.value)}</span>
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Notable Value Investors */}
      {institutional && institutional.notable_holders.length > 0 && (
        <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <AlertTriangle className="h-4 w-4 text-green-400" />
            <h3 className="text-sm font-semibold text-gray-400">Notable Value Investors Holding</h3>
          </div>
          <div className="space-y-0.5">
            {institutional.notable_holders.map((h, i) => (
              <div
                key={i}
                className="flex items-center justify-between border-b border-gray-700/50 px-2 py-1.5 text-sm"
              >
                <span className="font-semibold text-green-400">{h.name}</span>
                <span className="text-gray-400">
                  {h.shares.toLocaleString()} shares · {fmtDollars(h.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Top Institutional Holders */}
      {institutional && institutional.top_holders.length > 0 && (
        <div className="rounded-xl border border-gray-700 bg-gray-800/50 p-4">
          <div className="mb-3 flex items-center gap-2">
            <Users className="h-4 w-4 text-blue-400" />
            <h3 className="text-sm font-semibold text-gray-400">Top Institutional Holders</h3>
          </div>
          <div className="space-y-0.5">
            {institutional.top_holders.map((h, i) => (
              <div
                key={i}
                className="flex items-center justify-between border-b border-gray-700/50 px-2 py-1.5 text-sm"
              >
                <span className="text-gray-300">{h.name}</span>
                <span className="text-gray-500 text-xs">
                  {h.pct_held ? `${(h.pct_held * 100).toFixed(2)}%` : ""} · {fmtDollars(h.value)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
