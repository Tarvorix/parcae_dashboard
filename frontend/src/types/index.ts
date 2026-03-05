// ── Screener / Watchlist ──────────────────────────────────────────────────────

export interface WatchlistCandidate {
  ticker: string;
  name: string;
  price: number;
  market_cap: number;
  ev_ebit: number;
  fcf_yield_pct: number;
  price_tangible_book: number;
  net_debt_ebitda: number | null;
  sector: string | null;
  industry: string | null;
  screen_score: number;
}

// ── Distributions (bear/base/bull) ────────────────────────────────────────────

export interface DistributionParams {
  bear: number;
  base: number;
  bull: number;
}

export interface Distributions {
  revenue_growth: DistributionParams;
  fcf_margin: DistributionParams;
  net_margin: DistributionParams;
  discount_rate: DistributionParams;
  current_fcf: number;
  current_revenue: number;
  shares_outstanding: number;
}

// ── Histogram ─────────────────────────────────────────────────────────────────

export interface HistogramBin {
  bin_start: number;
  bin_end: number;
  count: number;
  frequency: number;
}

// ── Margin of Safety ──────────────────────────────────────────────────────────

export interface MarginOfSafety {
  current_price: number;
  p10: number;
  p25: number;
  p50: number;
  p75: number;
  p90: number;
  mos_median: number;
  mos_downside: number;
  prob_undervalued: number;
  klarman_score: number;
  passes_mos_threshold: boolean;
  histogram_data: HistogramBin[];
}

// ── Kelly Sizing ──────────────────────────────────────────────────────────────

export interface KellySizing {
  kelly_full_pct: number;
  kelly_fractional_pct: number;
  dollar_amount: number;
  shares: number;
}

// ── Analysis result ───────────────────────────────────────────────────────────

export interface AnalysisResult {
  ticker: string;
  name: string | null;
  sector: string | null;
  industry: string | null;
  distributions: Distributions;
  margin_of_safety: MarginOfSafety;
  kelly_sizing: KellySizing;
}

// ── Portfolio Tail Risk ───────────────────────────────────────────────────────

export interface CopulaResult {
  var: number;
  cvar: number;
  max_drawdown_sim: number;
  mean_return: number;
  std_return: number;
  n_positions: number;
  weights: number[];
}

export interface PositionStats {
  position_index: number;
  weight: number;
  mean_return: number;
  std_return: number;
  var: number;
  cvar: number;
  max_drawdown: number;
  sharpe: number;
}

export interface HistoricalRisk {
  portfolio_var: number;
  portfolio_cvar: number;
  portfolio_max_drawdown: number;
  portfolio_sharpe: number;
  portfolio_mean_return: number;
  portfolio_std_return: number;
  per_position: PositionStats[];
}

export interface PortfolioTailRisk {
  tickers: string[];
  copula: CopulaResult;
  historical: HistoricalRisk;
}

// ── Catalysts ─────────────────────────────────────────────────────────────────

export interface CatalystEntry {
  id: number;
  name: string;
  description: string | null;
  target_date: string | null;
  prior_probability: number;
  current_probability: number | null;
  value_impact_if_hit: number;
  value_impact_if_miss: number;
  n_observations: number;
  is_resolved: boolean;
  resolved_outcome: boolean | null;
}

export interface ObservationResult {
  catalyst_id: number;
  updated_probability: number;
  n_observations: number;
  distribution: {
    mean: number;
    std: number;
    p10: number;
    p25: number;
    p50: number;
    p75: number;
    p90: number;
    n_observations: number;
  };
}

// ── Saved Watchlist DB ────────────────────────────────────────────────────────

export interface SavedWatchlistEntry {
  id: number;
  ticker: string;
  name: string | null;
  sector: string | null;
  klarman_score: number | null;
  mos_downside: number | null;
  screen_score: number | null;
  last_analyzed_at: string | null;
}
