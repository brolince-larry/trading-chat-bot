export function formatPrice(value: number | string | null, decimals = 5): string {
	if (value === null) return '—';
	const num = typeof value === 'string' ? Number(value) : value;
	return Number.isFinite(num) ? num.toFixed(decimals) : '—';
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
