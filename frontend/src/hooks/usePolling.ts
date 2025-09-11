/**
 * React hook for polling-based real-time updates.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import {
	pollingService,
	type PollingStatus,
} from "../apiClient/services/pollingService";
import type { UsePollingReturn, Payout } from "../types";

export const usePolling = (): UsePollingReturn => {
	const [status, setStatus] = useState<PollingStatus>(
		pollingService.getStatus()
	);
	const statusUnsubscribe = useRef<(() => void) | null>(null);

	const startPolling = useCallback((payouts: Payout[]) => {
		pollingService.startPolling(payouts);
	}, []);

	const stopPolling = useCallback(() => {
		pollingService.stopPolling();
	}, []);

	const updatePayouts = useCallback((payouts: Payout[]) => {
		pollingService.updateCurrentPayouts(payouts);
	}, []);

	const onPayoutUpdate = useCallback(
		(callback: (payouts: Payout[]) => void) => {
			return pollingService.onPayoutUpdate(callback);
		},
		[]
	);

	useEffect(() => {
		// Subscribe to status changes
		statusUnsubscribe.current = pollingService.onStatusChange(
			(newStatus: PollingStatus) => {
				setStatus(newStatus);
			}
		);

		// Cleanup on unmount
		return () => {
			if (statusUnsubscribe.current) {
				statusUnsubscribe.current();
			}
		};
	}, []);

	return {
		isPolling: status.isPolling,
		lastUpdate: status.lastUpdate,
		error: status.error,
		pollCount: status.pollCount,
		startPolling,
		stopPolling,
		updatePayouts,
		onPayoutUpdate,
	};
};
