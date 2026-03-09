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

// ── Valuation Anchors ────────────────────────────────────────────────────────

export interface EPVResult {
  epv_total: number;
  epv_per_share: number;
  nopat: number;
  wacc: number;
  tax_rate_used: number;
  franchise_value: number;
  has_franchise: boolean;
}

export interface NCAVResult {
  ncav_total: number;
  ncav_per_share: number;
  current_assets: number;
  total_liabilities: number;
  trades_below_ncav: boolean;
  discount_to_ncav: number;
}

export interface ValuationAnchors {
  epv: EPVResult | null;
  ncav: NCAVResult | null;
}

// ── Quality / Distress Scores ────────────────────────────────────────────────

export interface PiotroskiComponents {
  roa_positive: boolean;
  cfo_positive: boolean;
  delta_roa_positive: boolean;
  accrual_quality: boolean;
  delta_leverage_down: boolean;
  delta_current_ratio_up: boolean;
  no_dilution: boolean;
  delta_gross_margin_up: boolean;
  delta_asset_turnover_up: boolean;
}

export interface PiotroskiScore {
  f_score: number;
  components: PiotroskiComponents;
  classification: "Strong" | "Neutral" | "Weak";
}

export interface AltmanComponents {
  x1_working_capital_ta: number;
  x2_retained_earnings_ta: number;
  x3_ebit_ta: number;
  x4_market_cap_tl: number;
  x5_revenue_ta: number;
}

export interface AltmanZScore {
  z_score: number;
  components: AltmanComponents;
  zone: "Safe" | "Grey" | "Distress";
}

export interface BeneishComponents {
  dsri: number;
  gmi: number;
  aqi: number;
  sgi: number;
  depi: number;
  sgai: number;
  tata: number;
  lvgi: number;
}

export interface BeneishMScore {
  m_score: number;
  components: BeneishComponents;
  likely_manipulator: boolean;
}

export interface QualityScores {
  piotroski: PiotroskiScore | null;
  altman: AltmanZScore | null;
  beneish: BeneishMScore | null;
}

// ── Flow Signals ─────────────────────────────────────────────────────────────

export interface InsiderTransaction {
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

export interface InsiderSummary {
  total_bought: number;
  total_sold: number;
  net_buying: number;
  n_buyers: number;
  n_sellers: number;
  n_transactions: number;
  cluster_buy_detected: boolean;
  cluster_buy_count: number;
}

export interface InsiderData {
  transactions: InsiderTransaction[];
  summary: InsiderSummary;
}

export interface InstitutionalHolder {
  name: string;
  shares: number;
  pct_held: number;
  value: number;
}

export interface InstitutionalData {
  notable_holders: InstitutionalHolder[];
  n_notable_holders: number;
  top_holders: InstitutionalHolder[];
}

export interface ShortInterestData {
  short_percent_of_float: number | null;
  short_ratio: number | null;
  short_interest_high: boolean;
}

export interface FlowSignals {
  insider: InsiderData | null;
  institutional: InstitutionalData | null;
  short_interest: ShortInterestData;
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
  valuation_anchors: ValuationAnchors;
  quality_scores: QualityScores;
  flow_signals: FlowSignals;
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

// ── Backtest ─────────────────────────────────────────────────────────────────

export interface BacktestMetrics {
  cagr: number;
  total_return: number;
  max_drawdown: number;
  sharpe: number;
  calmar: number;
  win_rate?: number;
  final_value: number;
}

export interface BacktestMonthlyPoint {
  date: string;
  portfolio_return: number;
  benchmark_return: number;
  portfolio_equity: number;
  benchmark_equity: number;
}

export interface BacktestResult {
  tickers_held: string[];
  benchmark: string;
  years: number;
  top_n: number;
  weighting: string;
  initial_capital: number;
  n_periods: number;
  portfolio: BacktestMetrics;
  benchmark_results: BacktestMetrics;
  alpha: number;
  monthly_series: BacktestMonthlyPoint[];
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
