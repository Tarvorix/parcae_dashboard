/**
 * App.tsx — Klarman Value Engine Dashboard
 *
 * All data comes from the live FastAPI backend.  No hardcoded scenarios.
 *
 * Layout:
 *   Left sidebar  → Watchlist (live screener results)
 *   Main panel    → 4-tab analysis view for selected ticker
 *     Tab 1: Value Distribution (histogram + MoS overlay)
 *     Tab 2: Downside Panel (Klarman checklist)
 *     Tab 3: FCF Projections (bear/base/bull bands)
 *     Tab 4: Decision Matrix (Kelly sizing)
 */

import React, { useState, useEffect, useCallback } from "react";
import { Search, RefreshCw, TrendingDown, AlertTriangle } from "lucide-react";

import {
  getWatchlist,
  analyzeStock,
  getPortfolioTailRisk,
  addToWatchlist,
} from "./api/client";

import ValueDistributionChart from "./components/ValueDistributionChart";
import DownsidePanel from "./components/DownsidePanel";
import ValuationAnchors from "./components/ValuationAnchors";
import QualityPanel from "./components/QualityPanel";
import FlowSignals from "./components/FlowSignals";
import FCFProjections from "./components/FCFProjections";
import DecisionMatrix from "./components/DecisionMatrix";
import Watchlist from "./components/Watchlist";
import PortfolioRisk from "./components/PortfolioRisk";

import type {
  AnalysisResult,
  PortfolioTailRisk,
  WatchlistCandidate,
} from "./types";

type AnalysisTab = "distribution" | "downside" | "valuation" | "quality" | "flow" | "fcf" | "decision";

const ANALYSIS_TABS: { id: AnalysisTab; label: string }[] = [
  { id: "distribution", label: "Value Distribution" },
  { id: "downside", label: "Downside / Klarman" },
  { id: "valuation", label: "Valuation Anchors" },
  { id: "quality", label: "Quality / Distress" },
  { id: "flow", label: "Flow Signals" },
  { id: "fcf", label: "FCF Projections" },
  { id: "decision", label: "Decision Matrix" },
];

export default function App() {
  // ── State ────────────────────────────────────────────────────────────────────
  const [watchlist, setWatchlist] = useState<WatchlistCandidate[]>([]);
  const [watchlistLoading, setWatchlistLoading] = useState(false);
  const [watchlistError, setWatchlistError] = useState<string | null>(null);

  const [selectedTicker, setSelectedTicker] = useState<string | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResult | null>(null);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  const [activeTab, setActiveTab] = useState<AnalysisTab>("distribution");
  const [portfolioValue, setPortfolioValue] = useState(100_000);

  const [portfolioRisk, setPortfolioRisk] = useState<PortfolioTailRisk | null>(null);
  const [portfolioRiskLoading, setPortfolioRiskLoading] = useState(false);

  const [tickerInput, setTickerInput] = useState("");
  const [showPortfolioPanel, setShowPortfolioPanel] = useState(false);
  const [analysisTickers, setAnalysisTickers] = useState<string[]>([]);

  // ── Data loading ──────────────────────────────────────────────────────────────

  const loadWatchlist = useCallback(async () => {
    setWatchlistLoading(true);
    setWatchlistError(null);
    try {
      const data = await getWatchlist(50);
      setWatchlist(data);
    } catch (e) {
      setWatchlistError(e instanceof Error ? e.message : "Failed to load watchlist");
    } finally {
      setWatchlistLoading(false);
    }
  }, []);

  const loadAnalysis = useCallback(
    async (ticker: string) => {
      setAnalysisLoading(true);
      setAnalysisError(null);
      setAnalysis(null);
      try {
        const data = await analyzeStock(ticker, portfolioValue);
        setAnalysis(data);
        setActiveTab("distribution");

        // Track tickers analyzed (for portfolio risk)
        setAnalysisTickers((prev) =>
          prev.includes(ticker) ? prev : [...prev, ticker]
        );
      } catch (e) {
        setAnalysisError(e instanceof Error ? e.message : "Analysis failed");
      } finally {
        setAnalysisLoading(false);
      }
    },
    [portfolioValue]
  );

  const loadPortfolioRisk = useCallback(async () => {
    if (analysisTickers.length < 2) return;
    setPortfolioRiskLoading(true);
    try {
      const data = await getPortfolioTailRisk(analysisTickers);
      setPortfolioRisk(data);
    } catch {
      // Portfolio risk is optional — fail silently
    } finally {
      setPortfolioRiskLoading(false);
    }
  }, [analysisTickers]);

  // Initial load
  useEffect(() => {
    loadWatchlist();
  }, [loadWatchlist]);

  // ── Handlers ──────────────────────────────────────────────────────────────────

  const handleTickerSelect = (ticker: string) => {
    setSelectedTicker(ticker);
    loadAnalysis(ticker);
  };

  const handleManualSearch = (e: React.FormEvent) => {
    e.preventDefault();
    const t = tickerInput.trim().toUpperCase();
    if (!t) return;
    setSelectedTicker(t);
    loadAnalysis(t);
    setTickerInput("");
  };

  const handleSaveToWatchlist = async (ticker: string) => {
    try {
      await addToWatchlist(ticker);
    } catch {
      // non-critical
    }
  };

  // ── Render ────────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-950 text-white font-sans flex flex-col">
      {/* Header */}
      <header className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <TrendingDown className="text-blue-400" size={24} />
          <div>
            <h1 className="text-lg font-bold text-white">Klarman Value Engine</h1>
            <p className="text-xs text-gray-500">Parcae Dashboard · Seth Klarman / Benjamin Graham</p>
          </div>
        </div>

        {/* Manual ticker search */}
        <form onSubmit={handleManualSearch} className="flex items-center gap-2">
          <input
            type="text"
            placeholder="Enter ticker…"
            value={tickerInput}
            onChange={(e) => setTickerInput(e.target.value)}
            className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 w-36"
          />
          <button
            type="submit"
            className="bg-blue-600 hover:bg-blue-500 rounded-lg px-3 py-2 text-sm transition-colors"
          >
            <Search size={16} />
          </button>
        </form>

        {/* Portfolio value input */}
        <div className="flex items-center gap-2 text-sm">
          <span className="text-gray-400">Portfolio $</span>
          <input
            type="number"
            value={portfolioValue}
            onChange={(e) => setPortfolioValue(parseFloat(e.target.value) || 100_000)}
            className="bg-gray-800 border border-gray-700 rounded px-2 py-1.5 text-white w-28 text-sm focus:outline-none focus:border-blue-500"
          />
        </div>
      </header>

      <div className="flex flex-1 overflow-hidden">
        {/* Left sidebar — watchlist */}
        <aside className="w-64 border-r border-gray-800 flex flex-col overflow-hidden">
          <div className="px-4 py-3 border-b border-gray-800 flex items-center justify-between">
            <span className="text-xs text-gray-400 uppercase tracking-wider">Screener</span>
            <button
              onClick={loadWatchlist}
              disabled={watchlistLoading}
              className="text-gray-400 hover:text-white transition-colors"
              title="Refresh screen"
            >
              <RefreshCw size={14} className={watchlistLoading ? "animate-spin" : ""} />
            </button>
          </div>

          {watchlistError && (
            <div className="px-4 py-2 text-xs text-red-400 flex items-center gap-1">
              <AlertTriangle size={12} />
              {watchlistError}
            </div>
          )}

          <div className="overflow-y-auto flex-1 py-1">
            {watchlistLoading ? (
              <div className="px-4 py-6 text-center text-gray-600 text-xs">
                <div className="animate-spin w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full mx-auto mb-2" />
                Screening S&P 500…
              </div>
            ) : watchlist.length === 0 ? (
              <div className="px-4 py-6 text-center text-gray-600 text-xs">
                No candidates pass Klarman filters
              </div>
            ) : (
              watchlist.map((c) => (
                <button
                  key={c.ticker}
                  onClick={() => handleTickerSelect(c.ticker)}
                  className={`w-full text-left px-4 py-3 border-b border-gray-800/50 transition-colors ${
                    selectedTicker === c.ticker
                      ? "bg-blue-900/30 border-l-2 border-l-blue-500"
                      : "hover:bg-gray-800/50"
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-blue-400 text-sm">{c.ticker}</span>
                    <span className="text-xs text-gray-500">{c.fcf_yield_pct?.toFixed(1)}% FCF</span>
                  </div>
                  <div className="text-xs text-gray-500 truncate mt-0.5">{c.name}</div>
                  <div className="text-xs text-gray-600 mt-0.5">
                    EV/EBIT: {c.ev_ebit?.toFixed(1)} · P/TBV: {c.price_tangible_book?.toFixed(2)}
                  </div>
                </button>
              ))
            )}
          </div>

          {/* Portfolio risk button */}
          {analysisTickers.length >= 2 && (
            <div className="px-4 py-3 border-t border-gray-800">
              <button
                onClick={() => {
                  setShowPortfolioPanel((v) => !v);
                  if (!portfolioRisk) loadPortfolioRisk();
                }}
                className="w-full bg-purple-900/40 hover:bg-purple-800/40 border border-purple-700 text-purple-300 text-xs rounded-lg py-2 transition-colors"
              >
                {showPortfolioPanel ? "Hide" : "View"} Portfolio Risk
                <span className="ml-1 opacity-60">({analysisTickers.length} positions)</span>
              </button>
            </div>
          )}
        </aside>

        {/* Main panel */}
        <main className="flex-1 overflow-y-auto p-6">
          {/* Portfolio Risk overlay */}
          {showPortfolioPanel && (
            <div className="mb-6 bg-gray-900 rounded-2xl border border-purple-800/50 p-5">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-base font-bold text-purple-300">Portfolio Tail Risk</h2>
                <button
                  onClick={() => setShowPortfolioPanel(false)}
                  className="text-gray-500 hover:text-white text-xs"
                >
                  ✕ Close
                </button>
              </div>
              {portfolioRiskLoading ? (
                <div className="text-center text-gray-500 py-8 text-sm">
                  <div className="animate-spin w-6 h-6 border-2 border-purple-500 border-t-transparent rounded-full mx-auto mb-2" />
                  Running copula simulation…
                </div>
              ) : portfolioRisk ? (
                <PortfolioRisk riskData={portfolioRisk} />
              ) : (
                <div className="text-gray-500 text-sm">No data</div>
              )}
            </div>
          )}

          {/* Analysis panel */}
          {!selectedTicker && (
            <div className="flex flex-col items-center justify-center h-full text-center text-gray-600">
              <TrendingDown size={64} className="mb-4 opacity-20" />
              <div className="text-xl font-bold text-gray-500 mb-2">
                Select a ticker from the watchlist
              </div>
              <div className="text-sm">
                Or type any ticker in the search box above for a full Monte Carlo DCF analysis.
              </div>
            </div>
          )}

          {selectedTicker && (
            <div>
              {/* Ticker header */}
              <div className="flex items-center justify-between mb-5">
                <div>
                  <h2 className="text-2xl font-bold">{selectedTicker}</h2>
                  {analysis && (
                    <div className="text-sm text-gray-400 mt-0.5">
                      {analysis.name}{" "}
                      {analysis.sector && (
                        <span className="text-gray-600">· {analysis.sector}</span>
                      )}
                    </div>
                  )}
                </div>
                {analysis && (
                  <button
                    onClick={() => handleSaveToWatchlist(selectedTicker)}
                    className="text-xs bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-lg px-3 py-1.5 transition-colors text-gray-300"
                  >
                    + Save to Watchlist
                  </button>
                )}
              </div>

              {/* Klarman score badge */}
              {analysis && (
                <div className="flex items-center gap-3 mb-5">
                  <div
                    className={`rounded-xl px-4 py-2 text-center min-w-[90px] ${
                      analysis.margin_of_safety.klarman_score >= 50
                        ? "bg-green-900/40 border border-green-700"
                        : analysis.margin_of_safety.klarman_score >= 25
                        ? "bg-amber-900/40 border border-amber-700"
                        : "bg-red-900/40 border border-red-700"
                    }`}
                  >
                    <div className="text-xs text-gray-400">Klarman Score</div>
                    <div
                      className={`text-3xl font-bold ${
                        analysis.margin_of_safety.klarman_score >= 50
                          ? "text-green-400"
                          : analysis.margin_of_safety.klarman_score >= 25
                          ? "text-amber-400"
                          : "text-red-400"
                      }`}
                    >
                      {analysis.margin_of_safety.klarman_score.toFixed(1)}
                    </div>
                  </div>

                  <div className="grid grid-cols-3 gap-2 flex-1">
                    {[
                      {
                        label: "Current Price",
                        value: `$${analysis.margin_of_safety.current_price.toFixed(2)}`,
                        color: "text-white",
                      },
                      {
                        label: "MoS vs P25",
                        value: `${(analysis.margin_of_safety.mos_downside * 100).toFixed(1)}%`,
                        color:
                          analysis.margin_of_safety.mos_downside >= 0.3
                            ? "text-green-400"
                            : "text-red-400",
                      },
                      {
                        label: "Kelly Position",
                        value: `${analysis.kelly_sizing.kelly_fractional_pct.toFixed(1)}%`,
                        color: "text-blue-400",
                      },
                    ].map(({ label, value, color }) => (
                      <div key={label} className="bg-gray-800 rounded-xl p-3 text-center">
                        <div className="text-gray-400 text-xs">{label}</div>
                        <div className={`font-bold text-lg ${color}`}>{value}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Tab navigation */}
              <div className="flex gap-1 bg-gray-800/50 rounded-xl p-1 mb-5 w-fit">
                {ANALYSIS_TABS.map((tab) => (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                      activeTab === tab.id
                        ? "bg-blue-600 text-white font-medium"
                        : "text-gray-400 hover:text-white"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Loading / error states */}
              {analysisLoading && (
                <div className="flex flex-col items-center justify-center h-64 text-gray-500">
                  <div className="animate-spin w-10 h-10 border-2 border-blue-500 border-t-transparent rounded-full mb-4" />
                  <div>Running 100K Monte Carlo paths for {selectedTicker}…</div>
                </div>
              )}

              {analysisError && (
                <div className="bg-red-900/20 border border-red-700 rounded-xl p-4 text-red-300 flex items-start gap-3">
                  <AlertTriangle size={20} className="flex-shrink-0 mt-0.5" />
                  <div>
                    <div className="font-bold">Analysis failed</div>
                    <div className="text-sm mt-1">{analysisError}</div>
                  </div>
                </div>
              )}

              {/* Tab content */}
              {!analysisLoading && !analysisError && analysis && (
                <div className="bg-gray-900 rounded-2xl border border-gray-800 p-5">
                  {activeTab === "distribution" && (
                    <ValueDistributionChart marginOfSafety={analysis.margin_of_safety} />
                  )}
                  {activeTab === "downside" && <DownsidePanel analysis={analysis} />}
                  {activeTab === "valuation" && (
                    <ValuationAnchors
                      anchors={analysis.valuation_anchors}
                      mos={analysis.margin_of_safety}
                    />
                  )}
                  {activeTab === "quality" && (
                    <QualityPanel scores={analysis.quality_scores} />
                  )}
                  {activeTab === "flow" && (
                    <FlowSignals signals={analysis.flow_signals} />
                  )}
                  {activeTab === "fcf" && (
                    <FCFProjections distributions={analysis.distributions} />
                  )}
                  {activeTab === "decision" && (
                    <DecisionMatrix
                      kellySizing={analysis.kelly_sizing}
                      marginOfSafety={analysis.margin_of_safety}
                      ticker={selectedTicker}
                    />
                  )}
                </div>
              )}
            </div>
          )}
        </main>
      </div>
    </div>
  );
}
