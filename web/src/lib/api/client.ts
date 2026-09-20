import { env } from '$env/dynamic/public';
import type {
	ApiErrorBody,
	CandleOut,
	PairAnalysisOut,
	PositionSizeRequest,
	PositionSizeResponseOut,
	PriceOut,
	ScanResultOut,
	SymbolOut
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

	return response.json() as Promise<T>;
}

export const api = {
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
		})
};
