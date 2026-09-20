<script lang="ts">
	import type { CurrencyExposureOut } from '$lib/api/types';

	let { exposures }: { exposures: CurrencyExposureOut[] } = $props();

	const maxAbs = $derived(Math.max(1, ...exposures.map((e) => Math.abs(e.net_position_count))));
</script>

{#if exposures.length === 0}
	<p class="text-sm text-slate-500">No open exposure from the current scan's confirmed setups.</p>
{:else}
	<div class="flex flex-col gap-2.5">
		{#each exposures as exposure (exposure.currency)}
			{@const widthPct = (Math.abs(exposure.net_position_count) / maxAbs) * 42}
			<div class="flex items-center gap-3 text-sm">
				<span class="w-10 shrink-0 font-medium">{exposure.currency}</span>
				<div class="relative h-4 flex-1 rounded bg-slate-100 dark:bg-slate-800">
					<div
						class="absolute top-0 bottom-0 left-1/2 w-px -translate-x-1/2 bg-slate-300 dark:bg-slate-600"
					></div>
					{#if exposure.net_position_count > 0}
						<div
							class="absolute top-0.5 bottom-0.5 left-1/2 rounded-r bg-emerald-500"
							style="width: {widthPct}%"
						></div>
					{:else if exposure.net_position_count < 0}
						<div
							class="absolute top-0.5 right-1/2 bottom-0.5 rounded-l bg-rose-500"
							style="width: {widthPct}%"
						></div>
					{/if}
				</div>
				<span
					class="w-10 shrink-0 text-right tabular-nums {exposure.net_position_count > 0
						? 'text-emerald-600 dark:text-emerald-400'
						: exposure.net_position_count < 0
							? 'text-rose-600 dark:text-rose-400'
							: 'text-slate-500'}"
				>
					{exposure.net_position_count > 0 ? '+' : ''}{exposure.net_position_count}
				</span>
			</div>
		{/each}
	</div>
	<p class="mt-3 text-xs text-slate-400">
		Positive = net long that currency, negative = net short, from confirmed setups in the latest
		scan.
	</p>
{/if}
