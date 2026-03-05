/**
 * FCFProjections — FCF Bands Tab
 *
 * Projects FCF over the 10-year holding period using bear/base/bull
 * scenarios from the distributions. Renders a band chart and a table.
 */

import React from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from "recharts";
import type { Distributions } from "../types";

interface Props {
  distributions: Distributions;
  projectionYears?: number;
}

function projectFCF(
  currentRevenue: number,
  revenueGrowth: number,
  fcfMargin: number,
  years: number
): number[] {
  const result: number[] = [];
  for (let y = 1; y <= years; y++) {
    const projRev = currentRevenue * Math.pow(1 + revenueGrowth, y);
    result.push(projRev * fcfMargin);
  }
  return result;
}

function fmtM(n: number): string {
  return `$${(n / 1e6).toFixed(0)}M`;
}

export default function FCFProjections({ distributions: dist, projectionYears = 10 }: Props) {
  const years = Array.from({ length: projectionYears }, (_, i) => i + 1);

  const bearFCFs = projectFCF(
    dist.current_revenue,
    dist.revenue_growth.bear,
    dist.fcf_margin.bear,
    projectionYears
  );
  const baseFCFs = projectFCF(
    dist.current_revenue,
    dist.revenue_growth.base,
    dist.fcf_margin.base,
    projectionYears
  );
  const bullFCFs = projectFCF(
    dist.current_revenue,
    dist.revenue_growth.bull,
    dist.fcf_margin.bull,
    projectionYears
  );

  const data = years.map((yr, i) => ({
    year: `Y${yr}`,
    bear: Math.round(bearFCFs[i] / 1e6),
    base: Math.round(baseFCFs[i] / 1e6),
    bull: Math.round(bullFCFs[i] / 1e6),
  }));

  return (
    <div className="space-y-6">
      {/* Distribution parameters */}
      <div className="grid grid-cols-3 gap-3">
        {[
          { label: "Revenue Growth", key: "revenue_growth" as const },
          { label: "FCF Margin", key: "fcf_margin" as const },
          { label: "Discount Rate", key: "discount_rate" as const },
        ].map(({ label, key }) => (
          <div key={key} className="bg-gray-800 rounded-xl p-3">
            <div className="text-gray-400 text-xs uppercase tracking-wider mb-2">{label}</div>
            <div className="space-y-1 text-xs">
              <div className="flex justify-between">
                <span className="text-red-400">Bear</span>
                <span className="font-mono">{(dist[key].bear * 100).toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-blue-400">Base</span>
                <span className="font-mono">{(dist[key].base * 100).toFixed(1)}%</span>
              </div>
              <div className="flex justify-between">
                <span className="text-green-400">Bull</span>
                <span className="font-mono">{(dist[key].bull * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* FCF band chart */}
      <div className="bg-gray-800 rounded-xl p-4">
        <div className="text-gray-400 text-xs uppercase tracking-wider mb-3">
          Projected Free Cash Flow ($M)
        </div>
        <ResponsiveContainer width="100%" height={280}>
          <AreaChart data={data} margin={{ top: 10, right: 20, bottom: 10, left: 10 }}>
            <XAxis dataKey="year" tick={{ fontSize: 10, fill: "#9ca3af" }} />
            <YAxis
              tickFormatter={(v) => `$${v}M`}
              tick={{ fontSize: 10, fill: "#9ca3af" }}
              width={60}
            />
            <Tooltip
              formatter={(value: number) => [`$${value}M`, ""]}
              contentStyle={{
                background: "#1f2937",
                border: "1px solid #374151",
                borderRadius: 6,
              }}
              labelStyle={{ color: "#e5e7eb" }}
              itemStyle={{ color: "#d1d5db" }}
            />
            <Legend
              wrapperStyle={{ fontSize: 11, color: "#9ca3af" }}
            />
            <Area
              type="monotone"
              dataKey="bull"
              stroke="#22c55e"
              fill="#22c55e22"
              name="Bull"
              strokeWidth={1.5}
            />
            <Area
              type="monotone"
              dataKey="base"
              stroke="#3b82f6"
              fill="#3b82f622"
              name="Base"
              strokeWidth={2}
            />
            <Area
              type="monotone"
              dataKey="bear"
              stroke="#ef4444"
              fill="#ef444422"
              name="Bear"
              strokeWidth={1.5}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Year-by-year table */}
      <div className="bg-gray-800 rounded-xl p-4 overflow-x-auto">
        <table className="w-full text-xs text-right">
          <thead>
            <tr className="text-gray-500 border-b border-gray-700">
              <th className="text-left py-2 pr-4">Year</th>
              <th className="text-red-400 py-2 px-2">Bear</th>
              <th className="text-blue-400 py-2 px-2">Base</th>
              <th className="text-green-400 py-2 px-2">Bull</th>
            </tr>
          </thead>
          <tbody>
            {data.map((row) => (
              <tr key={row.year} className="border-b border-gray-700/50 hover:bg-gray-700/30">
                <td className="text-left py-1.5 pr-4 text-gray-300">{row.year}</td>
                <td className="py-1.5 px-2 text-red-400 font-mono">${row.bear}M</td>
                <td className="py-1.5 px-2 text-blue-400 font-mono font-bold">${row.base}M</td>
                <td className="py-1.5 px-2 text-green-400 font-mono">${row.bull}M</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
