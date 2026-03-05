/**
 * ValueDistributionChart
 *
 * Renders the 200-bin intrinsic value histogram with:
 *   - A current price vertical line
 *   - Shaded margin-of-safety zone (price → p25)
 *   - Percentile reference lines (p10, p25, p50, p75, p90)
 */

import React from "react";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from "recharts";
import type { HistogramBin, MarginOfSafety } from "../types";

interface Props {
  marginOfSafety: MarginOfSafety;
}

function fmt(n: number): string {
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(1)}k`;
  return `$${n.toFixed(2)}`;
}

export default function ValueDistributionChart({ marginOfSafety: mos }: Props) {
  const { histogram_data, current_price, p10, p25, p50, p75, p90 } = mos;

  // Colour bins: red below price, amber in MoS zone, green above p25
  const getColor = (bin: HistogramBin): string => {
    const mid = (bin.bin_start + bin.bin_end) / 2;
    if (mid < current_price) return "#ef4444";         // red — below price
    if (mid < p25) return "#f59e0b";                    // amber — MoS zone
    return "#22c55e";                                   // green — above p25
  };

  const pctFmt = (v: number) => `${(v * 100).toFixed(1)}%`;

  return (
    <div className="w-full">
      <div className="mb-3 flex flex-wrap gap-4 text-xs text-gray-400">
        <span>
          <span className="inline-block w-3 h-3 rounded-sm bg-red-500 mr-1" />
          Below current price
        </span>
        <span>
          <span className="inline-block w-3 h-3 rounded-sm bg-amber-500 mr-1" />
          Margin of safety zone
        </span>
        <span>
          <span className="inline-block w-3 h-3 rounded-sm bg-green-500 mr-1" />
          Above P25 (Klarman's anchor)
        </span>
      </div>

      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={histogram_data}
          margin={{ top: 10, right: 20, bottom: 20, left: 10 }}
          barCategoryGap={0}
        >
          <XAxis
            dataKey="bin_start"
            tickFormatter={fmt}
            tick={{ fontSize: 10, fill: "#9ca3af" }}
            interval={Math.floor(histogram_data.length / 8)}
          />
          <YAxis
            tickFormatter={pctFmt}
            tick={{ fontSize: 10, fill: "#9ca3af" }}
            width={48}
          />
          <Tooltip
            formatter={(value: number, _name: string, props: { payload?: HistogramBin }) => {
              if (!props.payload) return [`${(value * 100).toFixed(3)}%`, ""];
              return [
                `${(value * 100).toFixed(3)}%`,
                `${fmt(props.payload.bin_start)} – ${fmt(props.payload.bin_end)}`,
              ];
            }}
            contentStyle={{ background: "#1f2937", border: "1px solid #374151", borderRadius: 6 }}
            labelStyle={{ color: "#e5e7eb" }}
            itemStyle={{ color: "#d1d5db" }}
          />

          {/* Percentile reference lines */}
          {[
            { value: p10, label: "P10", color: "#ef4444" },
            { value: p25, label: "P25", color: "#f59e0b" },
            { value: p50, label: "P50", color: "#22c55e" },
            { value: p75, label: "P75", color: "#3b82f6" },
            { value: p90, label: "P90", color: "#8b5cf6" },
          ].map(({ value, label, color }) => (
            <ReferenceLine
              key={label}
              x={histogram_data.reduce((closest, bin) =>
                Math.abs((bin.bin_start + bin.bin_end) / 2 - value) <
                Math.abs((closest.bin_start + closest.bin_end) / 2 - value)
                  ? bin
                  : closest
              ).bin_start}
              stroke={color}
              strokeDasharray="3 3"
              label={{ value: `${label} ${fmt(value)}`, fill: color, fontSize: 9, position: "insideTopRight" }}
            />
          ))}

          {/* Current price line */}
          <ReferenceLine
            x={histogram_data.reduce((closest, bin) =>
              Math.abs((bin.bin_start + bin.bin_end) / 2 - current_price) <
              Math.abs((closest.bin_start + closest.bin_end) / 2 - current_price)
                ? bin
                : closest
            ).bin_start}
            stroke="#ffffff"
            strokeWidth={2}
            label={{ value: `Price ${fmt(current_price)}`, fill: "#ffffff", fontSize: 10, position: "insideTopLeft" }}
          />

          <Bar dataKey="frequency" isAnimationActive={false}>
            {histogram_data.map((bin, i) => (
              <Cell key={i} fill={getColor(bin)} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>

      {/* MoS summary strip */}
      <div className="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
        <div className="bg-gray-800 rounded p-2">
          <div className="text-gray-400">MoS vs Median</div>
          <div className={`font-bold ${mos.mos_median >= 0 ? "text-green-400" : "text-red-400"}`}>
            {(mos.mos_median * 100).toFixed(1)}%
          </div>
        </div>
        <div className="bg-gray-800 rounded p-2">
          <div className="text-gray-400">MoS vs P25 (Klarman)</div>
          <div className={`font-bold ${mos.mos_downside >= 0 ? "text-green-400" : "text-red-400"}`}>
            {(mos.mos_downside * 100).toFixed(1)}%
          </div>
        </div>
        <div className="bg-gray-800 rounded p-2">
          <div className="text-gray-400">P(Undervalued)</div>
          <div className="font-bold text-blue-400">{(mos.prob_undervalued * 100).toFixed(1)}%</div>
        </div>
      </div>
    </div>
  );
}
