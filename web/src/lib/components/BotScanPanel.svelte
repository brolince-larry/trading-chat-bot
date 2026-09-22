<script lang="ts">
	import { onMount } from 'svelte';
	import { api, ApiError } from '$lib/api/client';
	import type { ScannedCandidateOut, ScanResultOut } from '$lib/api/types';
	import { connectLiveSocket } from '$lib/ws';
	import { deriveVerdict, type BotVerdict } from '$lib/helpers';
	import { formatPrice } from '$lib/format';

	let result = $state<ScanResultOut | null>(null);
	let live = $state(false);
	let error = $state<string | null>(null);
	let openingSymbol = $state<string | null>(null);

	const VERDICT_LABEL: Record<BotVerdict, string> = {
		enter_long: 'ENTER LONG',
		enter_short: 'ENTER SHORT',
		watch: 'WATCH',
		no_setup: 'NO SETUP'
	};

	const VERDICT_CLASS: Record<BotVerdict, string> = {
		enter_long: 'bg-[#12382a] text-[#57d99b] border-[#1c4632]',
		enter_short: 'bg-[#3a1519] text-[#ff9aa3] border-[#4b1e24]',
		watch: 'bg-[#241f10] text-[#e2b955] border-[#463b18]',
		no_setup: 'bg-[#161a20] text-[#5c6570] border-[#232a33]'
	};

	const DOT_CLASS: Record<BotVerdict, string> = {
		enter_long: 'bg-[#3fd98f]',
		enter_short: 'bg-[#ff7683]',
		watch: 'bg-[#e2b955]',
		no_setup: 'bg-[#4a525c]'
	};

	const rows = $derived(
		(result?.candidates ?? [])
			.map((c) => ({ candidate: c, verdict: deriveVerdict(c) }))
			.sort((a, b) => b.candidate.quality_score - a.candidate.quality_score)
	);

	const topSignal = $derived(
		rows.find((r) => r.verdict === 'enter_long' || r.verdict === 'enter_short') ?? null
	);

	async function enter(candidate: ScannedCandidateOut) {
		const setup = candidate.setup;
		if (setup.entry_price == null || setup.stop_loss == null) return;
		openingSymbol = setup.symbol;
		error = null;
		try {
			const sizing = await api.calculatePositionSize({
				symbol: setup.symbol,
				account_balance: '10000',
				risk_percent: '1',
				entry_price: String(setup.entry_price),
				stop_loss_price: String(setup.stop_loss),
				account_currency: 'USD'
			});
			if (sizing.lots === '0' || !sizing.meets_minimum_lot) {
				error = `${setup.symbol}: size below broker minimum lot.`;
				return;
			}
			await api.openPosition({
				symbol: setup.symbol,
				strategy: setup.strategy,
				direction: setup.direction,
				entry_price: String(setup.entry_price),
				stop_loss: String(setup.stop_loss),
				take_profit: setup.take_profits[0] ? String(setup.take_profits[0].price) : null,
				lots: sizing.lots,
				units: sizing.units,
				account_currency: 'USD',
				pip_value_per_unit: sizing.pip_value_per_unit
			});
		} catch (err) {
			error =
				err instanceof ApiError ? `${setup.symbol}: ${err.message}` : `${setup.symbol}: failed.`;
		} finally {
			openingSymbol = null;
		}
	}

	onMount(() => {
		api.runScan().then((r) => (result = r));
		return connectLiveSocket<ScanResultOut>('/ws/scanner', (data) => (result = data), {
			onOpen: () => (live = true),
			onClose: () => (live = false)
		});
	});
</script>

<svelte:head>
	<link
		href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;600;700&display=swap"
		rel="stylesheet"
	/>
</svelte:head>

<div
	class="overflow-hidden rounded-2xl border border-[#222830] bg-[#0b0d10] text-[#e8eaed]"
	style="font-family: 'JetBrains Mono', ui-monospace, Menlo, monospace;"
>
	<div class="flex items-center justify-between border-b border-[#1c2128] px-5 py-3">
		<span class="text-xs font-semibold tracking-[0.08em] text-[#8a94a1]">AI SCAN</span>
		<span class="flex items-center gap-1.5 text-[11px] text-[#8a94a1]">
			<span class="h-1.5 w-1.5 rounded-full {live ? 'bg-[#3fd98f]' : 'bg-[#4a525c]'}"></span>
			{live ? 'LIVE' : 'CONNECTING'}
		</span>
	</div>

	{#if error}
		<div class="border-b border-[#4b1e24] bg-[#2a1215] px-5 py-2 text-[12px] text-[#ffb3ba]">
			{error}
		</div>
	{/if}

	<div class="border-b border-[#1c2128] px-5 py-4">
		<p class="mb-2 text-[11px] font-semibold tracking-[0.08em] text-[#8a94a1]">TOP SIGNAL</p>
		{#if topSignal}
			<div class="flex flex-wrap items-center gap-4">
				<span class="text-xl font-bold">{topSignal.candidate.setup.symbol}</span>
				<span
					class="rounded-full border px-3 py-1 text-[11px] font-bold tracking-wide {VERDICT_CLASS[
						topSignal.verdict
					]}"
				>
					{VERDICT_LABEL[topSignal.verdict]}
				</span>
				<span class="text-2xl font-semibold tabular-nums">{topSignal.candidate.quality_score}</span>
				<span class="text-[11px] text-[#8a94a1]">SCORE</span>
				<span class="text-sm text-[#c5cbd3] tabular-nums">
					{topSignal.candidate.setup.risk_reward
						? `${topSignal.candidate.setup.risk_reward.toFixed(2)}R`
						: '—'}
				</span>
				<button
					onclick={() => enter(topSignal.candidate)}
					disabled={openingSymbol === topSignal.candidate.setup.symbol}
					class="ml-auto rounded-lg border border-[#6ea8ff] bg-[#6ea8ff] px-4 py-2 text-[12px] font-bold text-[#0b0d10] hover:bg-[#8dbaff] disabled:opacity-50"
				>
					{openingSymbol === topSignal.candidate.setup.symbol ? 'ENTERING…' : 'ENTER'}
				</button>
			</div>
		{:else}
			<span class="text-sm text-[#5c6570]">NO ACTIONABLE SIGNAL</span>
		{/if}
	</div>

	<div
		class="grid grid-cols-[90px_70px_120px_56px_1fr_72px_72px_72px_72px_80px] items-center gap-3 border-b border-[#1c2128] px-5 py-2 text-[10px] font-semibold tracking-[0.06em] text-[#5c6570]"
	>
		<span>SYMBOL</span><span>DIR</span><span>VERDICT</span><span>SCORE</span><span>CONF</span><span
			>R:R</span
		><span>ENTRY</span><span>STOP</span><span>TARGET</span><span class="text-right">ACTION</span>
	</div>

	{#if rows.length === 0}
		<div class="px-5 py-6 text-center text-[12px] text-[#5c6570]">NO DATA</div>
	{:else}
		{#each rows as { candidate, verdict } (candidate.setup.symbol + candidate.setup.strategy)}
			<div
				class="grid grid-cols-[90px_70px_120px_56px_1fr_72px_72px_72px_72px_80px] items-center gap-3 border-b border-[#1c2128] px-5 py-2.5 text-[12px]"
			>
				<span class="font-semibold">{candidate.setup.symbol}</span>
				<span class="flex items-center gap-1.5">
					<span class="h-1.5 w-1.5 rounded-full {DOT_CLASS[verdict]}"></span>
					<span
						class="{candidate.setup.direction === 'long'
							? 'text-[#3fd98f]'
							: candidate.setup.direction === 'short'
								? 'text-[#ff7683]'
								: 'text-[#5c6570]'} uppercase"
					>
						{candidate.setup.direction === 'none' ? '—' : candidate.setup.direction}
					</span>
				</span>
				<span
					class="rounded-full border px-2 py-0.5 text-center text-[10px] font-bold tracking-wide {VERDICT_CLASS[
						verdict
					]}"
				>
					{VERDICT_LABEL[verdict]}
				</span>
				<span class="tabular-nums">{candidate.quality_score}</span>
				<div class="h-2 rounded bg-[#1d232b]">
					<div
						class="h-2 rounded {verdict === 'enter_long' || verdict === 'enter_short'
							? 'bg-[#6ea8ff]'
							: 'bg-[#3a424d]'}"
						style="width: {candidate.quality_score}%"
					></div>
				</div>
				<span class="text-[#c5cbd3] tabular-nums"
					>{candidate.setup.risk_reward ? candidate.setup.risk_reward.toFixed(2) : '—'}</span
				>
				<span class="text-[#c5cbd3] tabular-nums">{formatPrice(candidate.setup.entry_price)}</span>
				<span class="text-[#c5cbd3] tabular-nums">{formatPrice(candidate.setup.stop_loss)}</span>
				<span class="text-[#c5cbd3] tabular-nums">
					{candidate.setup.take_profits[0]
						? formatPrice(candidate.setup.take_profits[0].price)
						: '—'}
				</span>
				<div class="flex justify-end">
					{#if verdict === 'enter_long' || verdict === 'enter_short'}
						<button
							onclick={() => enter(candidate)}
							disabled={openingSymbol === candidate.setup.symbol}
							class="rounded-md border border-[#2c323b] bg-[#171b21] px-2.5 py-1 text-[10px] font-bold hover:bg-[#1f252d] disabled:opacity-50"
						>
							{openingSymbol === candidate.setup.symbol ? '…' : 'ENTER'}
						</button>
					{:else}
						<span class="text-[10px] text-[#3a424d]">—</span>
					{/if}
				</div>
			</div>
		{/each}
	{/if}
</div>
