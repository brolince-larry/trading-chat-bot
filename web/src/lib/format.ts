export function formatPrice(value: number | string | null, decimals?: number): string {
	if (value === null) return '—';
	const num = typeof value === 'string' ? Number(value) : value;
	if (!Number.isFinite(num)) return '—';
	// JPY-quoted pairs (e.g. USD_JPY ~150) conventionally show 3 decimal
	// places (down to 1/10 pip); every other pair here trades under 20 and
	// shows 5. No symbol is threaded through to every call site, but this
	// app's fixed instrument universe makes the magnitude an unambiguous
	// stand-in for "is this a JPY pair".
	const resolvedDecimals = decimals ?? (Math.abs(num) >= 20 ? 3 : 5);
	return num.toFixed(resolvedDecimals);
}

export function formatPercent(value: number | null, decimals = 0): string {
	if (value === null) return '—';
	return `${value.toFixed(decimals)}%`;
}

export function formatDateTime(iso: string): string {
	return new Date(iso).toLocaleString(undefined, {
		dateStyle: 'medium',
		timeStyle: 'medium'
	});
}

export function statusColor(status: string): string {
	switch (status) {
		case 'confirmed':
			return 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300';
		case 'watching':
			return 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300';
		case 'invalidated':
			return 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300';
		default:
			return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
	}
}

export function directionColor(direction: string): string {
	if (direction === 'long') return 'text-emerald-600 dark:text-emerald-400';
	if (direction === 'short') return 'text-rose-600 dark:text-rose-400';
	return 'text-slate-500';
}

export function formatMoney(value: number | string | null, decimals = 2): string {
	if (value === null) return '—';
	const num = typeof value === 'string' ? Number(value) : value;
	if (!Number.isFinite(num)) return '—';
	const sign = num > 0 ? '+' : '';
	return `${sign}${num.toFixed(decimals)}`;
}

export function pnlColor(value: number | string | null): string {
	if (value === null) return 'text-slate-500';
	const num = typeof value === 'string' ? Number(value) : value;
	if (!Number.isFinite(num) || num === 0) return 'text-slate-500';
	return num > 0 ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-600 dark:text-rose-400';
}

export function positionStatusLabel(status: string): string {
	switch (status) {
		case 'closed_take_profit':
			return 'take profit';
		case 'closed_stop_loss':
			return 'stop loss';
		case 'closed_manual':
			return 'manual';
		default:
			return status;
	}
}

export function exposureColor(level: string): string {
	switch (level) {
		case 'high':
			return 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300';
		case 'medium':
			return 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300';
		default:
			return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-300';
	}
}
