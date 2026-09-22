import { env } from '$env/dynamic/public';

const BASE_URL = (env.PUBLIC_API_BASE_URL ?? 'http://localhost:8000').replace(/\/$/, '');

function wsUrl(path: string): string {
	return `${BASE_URL.replace(/^http/, 'ws')}${path}`;
}

interface LiveSocketOptions {
	onOpen?: () => void;
	onClose?: () => void;
	reconnectDelayMs?: number;
}

/**
 * Connect to a broadcast-only WebSocket channel with automatic reconnect.
 * Returns a cleanup function — call it (e.g. from a Svelte `$effect` return)
 * to close the connection and stop reconnecting.
 */
export function connectLiveSocket<T>(
	path: string,
	onMessage: (data: T) => void,
	options: LiveSocketOptions = {}
): () => void {
	let socket: WebSocket | null = null;
	let reconnectTimer: ReturnType<typeof setTimeout> | null = null;
	let closedByCaller = false;

	function connect() {
		socket = new WebSocket(wsUrl(path));

		socket.onopen = () => options.onOpen?.();

		socket.onmessage = (event: MessageEvent<string>) => {
			try {
				onMessage(JSON.parse(event.data) as T);
			} catch {
				// Ignore a malformed frame; the next one will arrive shortly.
			}
		};

		socket.onclose = () => {
			options.onClose?.();
			if (!closedByCaller) {
				reconnectTimer = setTimeout(connect, options.reconnectDelayMs ?? 2000);
			}
		};

		socket.onerror = () => socket?.close();
	}

	connect();

	return () => {
		closedByCaller = true;
		if (reconnectTimer) clearTimeout(reconnectTimer);
		socket?.close();
	};
}
