<script lang="ts">
	import { onMount } from 'svelte';
	import {
		LineSeries,
		createChart,
		type IChartApi,
		type ISeriesApi,
		type LineData,
		type UTCTimestamp
	} from 'lightweight-charts';
	import type { EquityPointOut } from '$lib/api/types';

	let { points, height = 220 }: { points: EquityPointOut[]; height?: number } = $props();

	let container: HTMLDivElement | undefined = $state();
	let chart: IChartApi | null = null;
	let series: ISeriesApi<'Line'> | null = null;

	function toLineData(pts: EquityPointOut[]): LineData[] {
		return pts.map((p) => ({
			time: (new Date(p.timestamp).getTime() / 1000) as UTCTimestamp,
			value: Number(p.balance)
		}));
	}

	onMount(() => {
		if (!container) return;
		chart = createChart(container, {
			height,
			layout: { background: { color: 'transparent' }, textColor: '#94a3b8' },
			grid: { vertLines: { visible: false }, horzLines: { color: 'rgba(148, 163, 184, 0.1)' } },
			timeScale: { timeVisible: true, secondsVisible: false },
			rightPriceScale: { borderVisible: false },
			autoSize: true
		});
		series = chart.addSeries(LineSeries, {
			color: '#10b981',
			lineWidth: 2,
			priceLineVisible: false,
			lastValueVisible: true
		});
		series.setData(toLineData(points));
		chart.timeScale().fitContent();

		return () => {
			chart?.remove();
			chart = null;
			series = null;
		};
	});

	$effect(() => {
		if (series) {
			series.setData(toLineData(points));
			chart?.timeScale().fitContent();
		}
	});
</script>

<div bind:this={container} style="height: {height}px; width: 100%"></div>
