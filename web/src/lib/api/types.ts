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
