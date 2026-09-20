import type { ScannedCandidateOut } from './api/types';

export type BotVerdict = 'enter_long' | 'enter_short' | 'watch' | 'no_setup';

/**
 * Collapses a scanned candidate's status+direction into a single symbolic
 * verdict — the only "outcome" the AI scan reports. Deliberately not a
 * sentence: the domain layer already decided rejected/watching/confirmed
 * and long/short/none, so this just names the combination.
 */
export function deriveVerdict(candidate: ScannedCandidateOut): BotVerdict {
	const { status, direction } = candidate.setup;
	if (status === 'confirmed' && direction === 'long') return 'enter_long';
	if (status === 'confirmed' && direction === 'short') return 'enter_short';
	if (status === 'watching') return 'watch';
	return 'no_setup';
}

// Small framework-agnostic helpers kept out of .svelte files so plain
// built-in Map/Set usage here isn't flagged by svelte/prefer-svelte-reactivity
// (that rule assumes any Map/Set in a .svelte file is meant to be reactive
// state, which isn't true for a one-off local computation like these).

export function toggleInSet<T>(set: Set<T>, value: T): Set<T> {
	const next = new Set(set);
	if (next.has(value)) next.delete(value);
	else next.add(value);
	return next;
}

export interface Breakdown {
	key: string;
	wins: number;
	losses: number;
	total: number;
	pnl: number;
}

export function groupByOutcome<T>(
	items: T[],
	keyOf: (item: T) => string,
	pnlOf: (item: T) => number
): Breakdown[] {
	const groups = new Map<string, Breakdown>();
	for (const item of items) {
		const key = keyOf(item);
		const group = groups.get(key) ?? { key, wins: 0, losses: 0, total: 0, pnl: 0 };
		group.total += 1;
		const pnl = pnlOf(item);
		group.pnl += pnl;
		if (pnl > 0) group.wins += 1;
		else group.losses += 1;
		groups.set(key, group);
	}
	return [...groups.values()].sort((a, b) => b.total - a.total);
}
