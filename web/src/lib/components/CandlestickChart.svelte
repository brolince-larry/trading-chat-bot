<script lang="ts">
	import { onMount } from 'svelte';
	import {
		CandlestickSeries,
		LineSeries,
		createChart,
		type CandlestickData,
		type IChartApi,
		type IPriceLine,
		type ISeriesApi,
		type LineData,
		type UTCTimestamp
	} from 'lightweight-charts';
	import { api, ApiError } from '$lib/api/client';
	import type { PriceOut } from '$lib/api/types';
	import { connectLiveSocket } from '$lib/ws';

	// Mirrors app/domain/market/models.py Timeframe.minutes — used only to
	// figure out which forming bar a live tick belongs to.
	const TIMEFRAME_MINUTES: Record<string, number> = {
		'1m': 1,
		'15m': 15,
		'1h': 60,
		'4h': 240,
		'1d': 1440
	};

	let {
		symbol,
		timeframe = '1h',
		entryPrice = null,
		stopLoss = null,
		takeProfit = null,
		height = 380
	}: {
		symbol: string;
		timeframe?: string;
		entryPrice?: number | null;
		stopLoss?: number | null;
		takeProfit?: number | null;
		height?: number;
	} = $props();

	let container: HTMLDivElement | undefined = $state();
	let chart: IChartApi | null = null;
	let candleSeries: ISeriesApi<'Candlestick'> | null = null;
	let ema20Series: ISeriesApi<'Line'> | null = null;
	let ema50Series: ISeriesApi<'Line'> | null = null;
	let entryLine: IPriceLine | null = null;
	let stopLine: IPriceLine | null = null;
	let targetLine: IPriceLine | null = null;

	let loading = $state(true);
	let error = $state<string | null>(null);
	let stopLiveTicks: (() => void) | null = null;

	function computeEma(values: number[], period: number): number[] {
		if (values.length === 0) return [];
		const k = 2 / (period + 1);
		const out: number[] = [];
		let prev = values[0];
		for (const value of values) {
			prev = value * k + prev * (1 - k);
			out.push(prev);
		}
		return out;
	}

	function syncLine(
		current: IPriceLine | null,
		price: number | null,
		color: string,
		title: string
	): IPriceLine | null {
		if (!candleSeries) return null;
		if (current) candleSeries.removePriceLine(current);
		if (price === null) return null;
		return candleSeries.createPriceLine({
			price,
			color,
			lineWidth: 2,
			lineStyle: 2, // dashed
			axisLabelVisible: true,
			title
		});
	}

	async function loadCandles() {
		if (!candleSeries) return;
		loading = true;
		error = null;
		try {
			const candles = await api.getCandles(symbol, timeframe, 200);
			const bars: CandlestickData[] = candles.map((c) => ({
				time: (new Date(c.timestamp).getTime() / 1000) as UTCTimestamp,
				open: Number(c.open),
				high: Number(c.high),
				low: Number(c.low),
				close: Number(c.close)
			}));
			candleSeries.setData(bars);

			const closes = candles.map((c) => Number(c.close));
			const ema20: LineData[] = computeEma(closes, 20).map((value, i) => ({
				time: bars[i].time,
				value
			}));
			const ema50: LineData[] = computeEma(closes, 50).map((value, i) => ({
				time: bars[i].time,
				value
			}));
			ema20Series?.setData(ema20);
			ema50Series?.setData(ema50);

			chart?.timeScale().fitContent();
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load chart data.';
		} finally {
			loading = false;
		}
	}

	function applyLiveTick(price: PriceOut) {
		if (!candleSeries) return;
		const mid = (Number(price.bid) + Number(price.ask)) / 2;
		const minutes = TIMEFRAME_MINUTES[timeframe] ?? 60;
		const bucketSeconds = minutes * 60;
		const nowSeconds = Math.floor(Date.now() / 1000);
		const barTime = (Math.floor(nowSeconds / bucketSeconds) * bucketSeconds) as UTCTimestamp;
		candleSeries.update({
			time: barTime,
			open: mid,
			high: mid,
			low: mid,
			close: mid
		});
	}

	onMount(() => {
		if (!container) return;
		chart = createChart(container, {
			height,
			layout: { background: { color: 'transparent' }, textColor: '#94a3b8' },
			grid: {
				vertLines: { color: 'rgba(148, 163, 184, 0.1)' },
				horzLines: { color: 'rgba(148, 163, 184, 0.1)' }
			},
			timeScale: { timeVisible: true, secondsVisible: false },
			autoSize: true
		});
		candleSeries = chart.addSeries(CandlestickSeries, {
			upColor: '#10b981',
			downColor: '#f43f5e',
			borderVisible: false,
			wickUpColor: '#10b981',
			wickDownColor: '#f43f5e'
		});
		ema20Series = chart.addSeries(LineSeries, {
			color: '#38bdf8',
			lineWidth: 1,
			title: 'EMA 20',
			priceLineVisible: false,
			lastValueVisible: false
		});
		ema50Series = chart.addSeries(LineSeries, {
			color: '#f59e0b',
			lineWidth: 1,
			title: 'EMA 50',
			priceLineVisible: false,
			lastValueVisible: false
		});

		loadCandles();

		return () => {
			stopLiveTicks?.();
			chart?.remove();
			chart = null;
			candleSeries = null;
			ema20Series = null;
			ema50Series = null;
		};
	});

	// Re-fetch when the symbol or timeframe changes.
	$effect(() => {
		if (candleSeries) loadCandles();
	});

	// Keep entry/stop/target price lines in sync with the current trade setup.
	$effect(() => {
		entryLine = syncLine(entryLine, entryPrice, '#38bdf8', 'Entry');
		stopLine = syncLine(stopLine, stopLoss, '#f43f5e', 'Stop');
		targetLine = syncLine(targetLine, takeProfit, '#10b981', 'Target');
	});

	// Live price ticks keep the forming bar moving in real time.
	$effect(() => {
		stopLiveTicks?.();
		const currentSymbol = symbol;
		stopLiveTicks = connectLiveSocket<Record<string, PriceOut>>('/ws/prices', (prices) => {
			const tick = prices[currentSymbol];
			if (tick) applyLiveTick(tick);
		});
		return () => stopLiveTicks?.();
	});
</script>

<div class="flex flex-col gap-2">
	{#if error}
		<div
			class="rounded border border-rose-300 bg-rose-50 px-3 py-2 text-xs text-rose-800 dark:border-rose-800 dark:bg-rose-950/40 dark:text-rose-300"
		>
			{error}
		</div>
	{/if}
	<div class="relative">
		{#if loading}
			<div
				class="absolute inset-0 flex items-center justify-center text-sm text-slate-400"
				style="height: {height}px"
			>
				Loading chart…
			</div>
		{/if}
		<div bind:this={container} style="height: {height}px; width: 100%"></div>
	</div>
</div>
