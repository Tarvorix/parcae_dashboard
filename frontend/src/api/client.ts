/**
 * API client — all fetch calls to the FastAPI backend.
 * In Docker Compose the Vite proxy rewrites /api → http://backend:8000.
 * In dev (direct), set VITE_API_BASE to http://localhost:8000.
 */

import type {
  AnalysisResult,
  BacktestResult,
  CatalystEntry,
  ObservationResult,
  PortfolioTailRisk,
  SavedWatchlistEntry,
  WatchlistCandidate,
} from "../types";

const BASE = import.meta.env.VITE_API_BASE ?? "/api";

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, options);
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(`API ${res.status}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// ── Screener ──────────────────────────────────────────────────────────────────

export async function getWatchlist(topN = 50): Promise<WatchlistCandidate[]> {
  return request<WatchlistCandidate[]>(`/watchlist?top_n=${topN}`);
}

// ── DCF Analysis ──────────────────────────────────────────────────────────────

export async function analyzeStock(
  ticker: string,
  portfolioValue = 100_000
): Promise<AnalysisResult> {
  return request<AnalysisResult>(
    `/analyze/${encodeURIComponent(ticker)}?portfolio_value=${portfolioValue}`
  );
}

// ── Portfolio Tail Risk ───────────────────────────────────────────────────────

export async function getPortfolioTailRisk(
  tickers: string[],
  years = 5,
  confidence = 0.95
): Promise<PortfolioTailRisk> {
  const params = new URLSearchParams({
    tickers: tickers.join(","),
    years: String(years),
    confidence: String(confidence),
  });
  return request<PortfolioTailRisk>(`/portfolio/tail-risk?${params}`);
}

// ── Watchlist DB ──────────────────────────────────────────────────────────────

export async function getSavedWatchlist(): Promise<SavedWatchlistEntry[]> {
  return request<SavedWatchlistEntry[]>("/watchlist/db");
}

export async function addToWatchlist(
  ticker: string
): Promise<{ message: string; id: number }> {
  return request<{ message: string; id: number }>(`/watchlist/${encodeURIComponent(ticker)}`, {
    method: "POST",
  });
}

// ── Catalysts ─────────────────────────────────────────────────────────────────

export async function getPositionCatalysts(
  positionId: number
): Promise<CatalystEntry[]> {
  return request<CatalystEntry[]>(`/position/${positionId}/catalysts`);
}

export async function addCatalyst(
  positionId: number,
  payload: {
    name: string;
    description?: string;
    target_date?: string;
    value_impact_if_hit: number;
    value_impact_if_miss: number;
    prior_probability: number;
  }
): Promise<{ id: number; message: string }> {
  return request<{ id: number; message: string }>(
    `/position/${positionId}/catalyst`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    }
  );
}

export async function recordCatalystObservation(
  positionId: number,
  catalystId: number,
  observation: boolean,
  strength = 1.0,
  notes?: string
): Promise<ObservationResult> {
  return request<ObservationResult>(
    `/position/${positionId}/catalyst/${catalystId}/observe`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        observation,
        observation_strength: strength,
        notes,
      }),
    }
  );
}

// ── Backtest ─────────────────────────────────────────────────────────────────

export async function runBacktest(
  years = 10,
  topN = 10,
  weighting: "equal" | "score" = "equal",
  initialCapital = 100_000,
  universe = "sp500"
): Promise<BacktestResult> {
  const params = new URLSearchParams({
    years: String(years),
    top_n: String(topN),
    weighting,
    initial_capital: String(initialCapital),
    universe,
  });
  return request<BacktestResult>(`/backtest?${params}`, { method: "POST" });
}

// ── Health ────────────────────────────────────────────────────────────────────

export async function healthCheck(): Promise<{ status: string; version: string }> {
  return request<{ status: string; version: string }>("/health");
}
