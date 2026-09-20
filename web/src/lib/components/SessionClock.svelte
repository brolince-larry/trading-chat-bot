<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { MarketSessionSnapshotOut } from '$lib/api/types';

	const REFRESH_MS = 30_000;
	const OVERLAP_LABELS: Record<string, string> = {
		london_new_york: 'London / New York overlap — highest liquidity window',
		tokyo_london: 'Tokyo / London overlap',
		sydney_tokyo: 'Sydney / Tokyo overlap'
	};

	let snapshot = $state<MarketSessionSnapshotOut | null>(null);
	let error = $state<string | null>(null);

	function formatClock(iso: string): string {
		// The backend already computed this timestamp's wall-clock time in the
		// target city's zone (the ISO string's offset reflects it). Formatting
		// via `new Date(iso).toLocaleTimeString()` would convert it into the
		// *viewer's* local timezone instead, collapsing every city to the same
		// displayed time — so the hour/minute are read directly off the string.
		const match = iso.match(/T(\d{2}):(\d{2})/);
		if (!match) return iso;
		const hour24 = Number(match[1]);
		const period = hour24 >= 12 ? 'PM' : 'AM';
		const hour12 = hour24 % 12 || 12;
		return `${hour12}:${match[2]} ${period}`;
	}

	async function refresh() {
		try {
			snapshot = await api.getSessions();
			error = null;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load session data.';
		}
	}

	onMount(() => {
		refresh();
		const interval = setInterval(refresh, REFRESH_MS);
		return () => clearInterval(interval);
	});
</script>

<div class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
	<h2 class="text-sm font-semibold">Sessions &amp; World Clock</h2>

	{#if error}
		<p class="mt-2 text-xs text-rose-600 dark:text-rose-400">{error}</p>
	{:else if !snapshot}
		<p class="mt-2 text-xs text-slate-400">Loading…</p>
	{:else}
		<div class="mt-3 flex flex-wrap gap-2">
			{#each snapshot.sessions as session (session.id)}
				<span
					class="flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium {session.is_open
						? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
						: 'bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400'}"
				>
					<span
						class="h-1.5 w-1.5 rounded-full {session.is_open ? 'bg-emerald-500' : 'bg-slate-400'}"
					></span>
					{session.label}
					{session.is_open ? 'open' : 'closed'}
				</span>
			{/each}
		</div>

		{#if snapshot.active_overlaps.length > 0}
			<div class="mt-2 flex flex-col gap-1">
				{#each snapshot.active_overlaps as overlap (overlap)}
					<p class="text-xs font-medium text-sky-700 dark:text-sky-400">
						{OVERLAP_LABELS[overlap] ?? overlap}
					</p>
				{/each}
			</div>
		{/if}

		<div class="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5 sm:grid-cols-3 lg:grid-cols-5">
			{#each snapshot.world_clock as entry (entry.label)}
				<div class="flex flex-col">
					<span class="text-xs text-slate-400">{entry.label}</span>
					<span class="text-sm font-medium tabular-nums">{formatClock(entry.local_time)}</span>
					<span class="text-xs text-slate-400">{entry.utc_offset}</span>
				</div>
			{/each}
		</div>
	{/if}
</div>
