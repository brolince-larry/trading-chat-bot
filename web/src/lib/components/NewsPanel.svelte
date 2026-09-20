<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { NewsFeedOut } from '$lib/api/types';
	import { formatDateTime } from '$lib/format';

	let { symbol = undefined }: { symbol?: string } = $props();

	let feed = $state<NewsFeedOut | null>(null);
	let error = $state<string | null>(null);

	async function load() {
		try {
			feed = await api.getNews(symbol);
			error = null;
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load news.';
		}
	}

	onMount(load);

	$effect(() => {
		load();
	});
</script>

<div class="rounded border border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900">
	<h2 class="text-sm font-semibold">Market News</h2>

	{#if error}
		<p class="mt-2 text-xs text-rose-600 dark:text-rose-400">{error}</p>
	{:else if !feed}
		<p class="mt-2 text-xs text-slate-400">Loading…</p>
	{:else if !feed.connected}
		<div
			class="mt-2 rounded border border-dashed border-slate-300 px-3 py-4 text-center text-xs text-slate-500 dark:border-slate-700 dark:text-slate-400"
		>
			{feed.message}
		</div>
	{:else if feed.items.length === 0}
		<p class="mt-2 text-xs text-slate-400">No recent news for this pair.</p>
	{:else}
		<ul class="mt-2 flex flex-col gap-3">
			{#each feed.items as item (item.headline + item.published_at)}
				<li class="text-sm">
					<div class="flex items-center gap-2">
						{#if item.impact}
							<span
								class="rounded-full px-2 py-0.5 text-xs font-medium {item.impact === 'high'
									? 'bg-rose-100 text-rose-800 dark:bg-rose-900/40 dark:text-rose-300'
									: item.impact === 'medium'
										? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
										: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300'}"
							>
								{item.impact}
							</span>
						{/if}
						<span class="text-xs text-slate-400">{item.source}</span>
						<span class="text-xs text-slate-400">{formatDateTime(item.published_at)}</span>
					</div>
					{#if item.url}
						<a href={item.url} target="_blank" rel="external noreferrer" class="hover:underline"
							>{item.headline}</a
						>
					{:else}
						<p>{item.headline}</p>
					{/if}
				</li>
			{/each}
		</ul>
	{/if}
</div>
