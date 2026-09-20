import { env } from '$env/dynamic/public';
import type {
	AccountRange,
	AccountSettingsOut,
	AccountSummaryOut,
	ApiErrorBody,
	BotSettingsOut,
	CandleOut,
	HealthOut,
	MarketSessionSnapshotOut,
	NewsFeedOut,
	NotificationOut,
	OpenPositionRequest,
	PairAnalysisOut,
	PerformanceStatsOut,
	PositionOut,
	PositionSizeRequest,
	PositionSizeResponseOut,
	PriceOut,
	RiskLimitsOut,
	RiskLimitsUpdateRequest,
	ScanResultOut,
	SymbolOut,
	TradeAutomationSettingsOut,
	UpdateStopsRequest
} from './types';

const BASE_URL = (env.PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');

export class ApiError extends Error {
	constructor(
		public status: number,
		message: string
	) {
		super(message);
		this.name = 'ApiError';
	}
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
	let response: Response;
	try {
		response = await fetch(`${BASE_URL}${path}`, {
			...init,
			headers: { 'Content-Type': 'application/json', ...init?.headers }
		});
	} catch {
		throw new ApiError(0, 'Could not reach the API server. Is the backend running?');
	}

	if (!response.ok) {
		const body = (await response.json().catch(() => null)) as ApiErrorBody | null;
		const detail = body?.detail;
		const message = Array.isArray(detail)
			? detail.map((d) => d.msg).join('; ')
			: (detail ?? `Request failed with status ${response.status}`);
		throw new ApiError(response.status, message);
	}

	if (response.status === 204) {
		return undefined as T;
	}
	return response.json() as Promise<T>;
}

export const api = {
	getHealth: () => request<HealthOut>('/api/v1/health'),

	getSymbols: () => request<SymbolOut[]>('/api/v1/market/symbols'),

	getCandles: (symbol: string, timeframe = '1h', count = 200) =>
		request<CandleOut[]>(`/api/v1/market/${symbol}/candles?timeframe=${timeframe}&count=${count}`),

	getPrice: (symbol: string) => request<PriceOut>(`/api/v1/market/${symbol}/price`),

	getPairAnalysis: (symbol: string) => request<PairAnalysisOut>(`/api/v1/analysis/${symbol}`),

	runScan: (options?: { symbols?: string[]; min_quality_score?: number }) =>
		request<ScanResultOut>('/api/v1/scanner/run', {
			method: 'POST',
			body: JSON.stringify(options ?? {})
		}),

	calculatePositionSize: (payload: PositionSizeRequest) =>
		request<PositionSizeResponseOut>('/api/v1/risk/position-size', {
			method: 'POST',
			body: JSON.stringify(payload)
		}),

	listPositions: (status: 'open' | 'closed') =>
		request<PositionOut[]>(`/api/v1/positions?status=${status}`),

	getPositionStats: () => request<PerformanceStatsOut>('/api/v1/positions/stats'),

	openPosition: (payload: OpenPositionRequest) =>
		request<PositionOut>('/api/v1/positions/open', {
			method: 'POST',
			body: JSON.stringify(payload)
		}),

	closePosition: (id: string, closePrice?: string) =>
		request<PositionOut>(`/api/v1/positions/${id}/close`, {
			method: 'POST',
			body: JSON.stringify(closePrice ? { close_price: closePrice } : {})
		}),

	updatePositionStops: (id: string, payload: UpdateStopsRequest) =>
		request<PositionOut>(`/api/v1/positions/${id}`, {
			method: 'PATCH',
			body: JSON.stringify(payload)
		}),

	getRiskLimits: () => request<RiskLimitsOut>('/api/v1/risk/limits'),

	updateRiskLimits: (payload: RiskLimitsUpdateRequest) =>
		request<RiskLimitsOut>('/api/v1/risk/limits', {
			method: 'PUT',
			body: JSON.stringify(payload)
		}),

	getSessions: () => request<MarketSessionSnapshotOut>('/api/v1/sessions'),

	getNews: (symbol?: string) =>
		request<NewsFeedOut>(`/api/v1/news${symbol ? `?symbol=${symbol}` : ''}`),

	closeAllPositions: () =>
		request<PositionOut[]>('/api/v1/positions/close-all', { method: 'POST' }),

	getAccountSummary: (range: AccountRange = '1m') =>
		request<AccountSummaryOut>(`/api/v1/account/summary?period=${range}`),

	getAccountSettings: () => request<AccountSettingsOut>('/api/v1/account/settings'),

	updateAccountSettings: (payload: AccountSettingsOut) =>
		request<AccountSettingsOut>('/api/v1/account/settings', {
			method: 'PUT',
			body: JSON.stringify(payload)
		}),

	getBotSettings: () => request<BotSettingsOut>('/api/v1/bot/settings'),

	updateBotSettings: (payload: BotSettingsOut) =>
		request<BotSettingsOut>('/api/v1/bot/settings', {
			method: 'PUT',
			body: JSON.stringify(payload)
		}),

	getAutomationSettings: () => request<TradeAutomationSettingsOut>('/api/v1/automations/settings'),

	updateAutomationSettings: (payload: TradeAutomationSettingsOut) =>
		request<TradeAutomationSettingsOut>('/api/v1/automations/settings', {
			method: 'PUT',
			body: JSON.stringify(payload)
		}),

	listNotifications: (unreadOnly = false) =>
		request<NotificationOut[]>(`/api/v1/notifications${unreadOnly ? '?unread_only=true' : ''}`),

	markNotificationRead: (id: string) =>
		request<void>(`/api/v1/notifications/${id}/read`, { method: 'POST' }),

	markAllNotificationsRead: () =>
		request<void>('/api/v1/notifications/read-all', { method: 'POST' })
};
