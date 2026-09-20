// Mirrors app/schemas/*.py on the FastAPI backend. Keep field names and
// shapes in sync with those Pydantic models.

export type Direction = 'long' | 'short' | 'none';
export type SetupStatus = 'rejected' | 'watching' | 'confirmed' | 'invalidated';
export type TrendDirection = 'bullish' | 'bearish' | 'neutral';
export type MarketRegime = 'trending' | 'ranging' | 'transitioning';
export type ExposureLevel = 'low' | 'medium' | 'high';

export interface SymbolOut {
	name: string;
	base_currency: string;
	quote_currency: string;
	pip_size: string;
	contract_size: string;
	min_lot: string;
	max_lot: string;
}

export interface CandleOut {
	timestamp: string;
	open: string;
	high: string;
	low: string;
	close: string;
	volume: string;
}

export interface PriceOut {
	symbol: string;
	bid: string;
	ask: string;
	spread_pips: string;
	timestamp: string;
}

export interface TimeframeAnalysisOut {
	timeframe: string;
	last_close: number;
	ema_20: number | null;
	ema_50: number | null;
	ema_200: number | null;
	rsi_14: number | null;
	atr_14: number | null;
	adx_14: number | null;
	trend: TrendDirection;
	regime: MarketRegime;
	support_levels: number[];
	resistance_levels: number[];
}

export interface PairAnalysisOut {
	symbol: string;
	higher_timeframe: TimeframeAnalysisOut;
	entry_timeframe: TimeframeAnalysisOut;
}

export interface TakeProfitOut {
	price: number;
	r_multiple: number;
}

export interface TradeSetupOut {
	symbol: string;
	strategy: string;
	direction: Direction;
	status: SetupStatus;
	reason: string;
	invalidation: string;
	entry_price: number | null;
	entry_trigger: string | null;
	stop_loss: number | null;
	take_profits: TakeProfitOut[];
	risk_reward: number | null;
	warnings: string[];
}

export interface ScannedCandidateOut {
	setup: TradeSetupOut;
	quality_score: number;
	higher_timeframe: string;
	entry_timeframe: string;
	spread_pips: string | null;
}

export interface SkippedSymbolOut {
	symbol: string;
	reason: string;
}

export interface CurrencyExposureOut {
	currency: string;
	net_position_count: number;
	level: ExposureLevel;
	contributing_symbols: string[];
}

export interface ScanResultOut {
	scanned_at: string;
	symbols_scanned: number;
	candidates: ScannedCandidateOut[];
	skipped: SkippedSymbolOut[];
	currency_exposure: CurrencyExposureOut[];
}

export interface PositionSizeRequest {
	symbol: string;
	account_balance: string;
	risk_percent: string;
	entry_price: string;
	stop_loss_price: string;
	account_currency?: string;
	quote_to_account_rate?: string | null;
}

export interface PositionSizeResponseOut {
	symbol: string;
	account_currency: string;
	risk_amount: string;
	stop_distance_pips: string;
	pip_value_per_unit: string;
	lots: string;
	units: string;
	meets_minimum_lot: boolean;
	warnings: string[];
}

export interface ApiErrorBody {
	detail: string | { msg: string; loc: (string | number)[] }[];
}

export type PositionStatus = 'open' | 'closed_take_profit' | 'closed_stop_loss' | 'closed_manual';

export interface OpenPositionRequest {
	symbol: string;
	strategy: string;
	direction: Direction;
	entry_price: string;
	stop_loss: string;
	take_profit?: string | null;
	lots: string;
	units: string;
	account_currency?: string;
	pip_value_per_unit: string;
}

export interface PositionOut {
	id: string;
	symbol: string;
	strategy: string;
	direction: Direction;
	status: PositionStatus;
	entry_price: string;
	stop_loss: string;
	take_profit: string | null;
	lots: string;
	units: string;
	account_currency: string;
	opened_at: string;
	closed_at: string | null;
	close_price: string | null;
	realized_pnl: string | null;
	risk_multiple: string | null;
	unrealized_pnl: string | null;
}

export interface PerformanceStatsOut {
	closed_count: number;
	win_count: number;
	loss_count: number;
	win_rate: number | null;
	total_realized_pnl: string;
	average_r_multiple: number | null;
	expectancy_r: number | null;
	profit_factor: number | null;
}

export interface RiskLimitsOut {
	max_risk_per_trade_percent: string;
	max_daily_loss_percent: string;
	max_open_positions: number;
	max_spread_pips: string;
	max_correlated_exposure: ExposureLevel;
	min_risk_reward: string | null;
	max_drawdown_percent: string | null;
}

export type RiskLimitsUpdateRequest = RiskLimitsOut;

export interface UpdateStopsRequest {
	stop_loss?: string | null;
	take_profit?: string | null;
}

export interface SessionStatusOut {
	id: string;
	label: string;
	timezone: string;
	is_open: boolean;
	local_time: string;
	next_open_utc: string;
	next_close_utc: string;
}

export interface WorldClockEntryOut {
	label: string;
	timezone: string;
	local_time: string;
	utc_offset: string;
}

export interface MarketSessionSnapshotOut {
	generated_at: string;
	sessions: SessionStatusOut[];
	world_clock: WorldClockEntryOut[];
	active_overlaps: string[];
}

export interface NewsItemOut {
	headline: string;
	source: string;
	published_at: string;
	url: string | null;
	symbols: string[];
	impact: string | null;
}

export interface NewsFeedOut {
	connected: boolean;
	message: string;
	items: NewsItemOut[];
}

export interface AccountSettingsOut {
	starting_balance: string;
}

export interface EquityPointOut {
	timestamp: string;
	balance: string;
}

export interface PairPerformanceOut {
	symbol: string;
	realized_pnl: string;
	trade_count: number;
}

export interface AccountSummaryOut {
	starting_balance: string;
	balance: string;
	total_realized_pnl: string;
	total_unrealized_pnl: string;
	total_pnl_percent: number;
	active_trades: number;
	win_rate: number | null;
	equity_curve: EquityPointOut[];
	top_pairs: PairPerformanceOut[];
}

export type AccountRange = '1d' | '1w' | '1m' | '3m' | '6m' | '1y' | 'all';

export interface BotSettingsOut {
	enabled: boolean;
	active_symbols: string[];
	active_strategies: string[];
}

export interface TradeAutomationSettingsOut {
	breakeven_enabled: boolean;
	breakeven_at_r: string;
	trailing_stop_enabled: boolean;
	trailing_stop_pips: string;
}

export type NotificationType = 'trade_closed' | 'new_signal' | 'risk_alert' | 'bot_update';

export interface HealthOut {
	status: string;
	app_name: string;
	environment: string;
	market_data_provider: string;
}

export interface NotificationOut {
	id: string;
	type: NotificationType;
	message: string;
	symbol: string | null;
	created_at: string;
	read: boolean;
}
