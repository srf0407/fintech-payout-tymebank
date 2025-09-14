/**
 * Polling service for real-time payout status updates.
 * Polls the backend API at regular intervals to check for status changes.
 */

import { payoutService, type Payout } from "./payoutService";
import { retryService, RETRY_CONFIGS } from "../../utils/retryService";

export type { Payout };

export interface PollingStatus {
	isPolling: boolean;
	lastUpdate: Date | null;
	error: string | null;
	pollCount: number;
}

export type PayoutUpdateCallback = (updatedPayouts: Payout[]) => void;
export type PollingStatusCallback = (status: PollingStatus) => void;

class PollingService {
	private pollInterval: number | null = null;
	private isPolling = false;
	private pollCount = 0;
	private lastUpdate: Date | null = null;
	private error: string | null = null;
	private currentPayouts: Payout[] = [];
	private currentPage: number = 1;
	private perPage: number = 10;

	private payoutUpdateCallbacks: Set<PayoutUpdateCallback> = new Set();
	private statusCallbacks: Set<PollingStatusCallback> = new Set();

	// Configuration
	private readonly POLL_INTERVAL = 3000; // 3 seconds
	private readonly MAX_POLL_COUNT = 1000; // Prevent infinite polling
	private readonly ERROR_RETRY_DELAY = 10000; // 10 seconds on error

	/**
	 * Start polling for payout updates
	 */
	startPolling(currentPayouts: Payout[]): void {
		if (this.isPolling) {
			console.log("Polling already active");
			return;
		}

		this.currentPayouts = currentPayouts ? [...currentPayouts] : [];
		this.isPolling = true;
		this.pollCount = 0;
		this.error = null;

		this.notifyStatusChange();
		this.scheduleNextPoll();

		console.log("Started polling for payout updates");
	}

	/**
	 * Stop polling
	 */
	stopPolling(): void {
		if (this.pollInterval) {
			window.clearTimeout(this.pollInterval);
			this.pollInterval = null;
		}

		this.isPolling = false;
		this.notifyStatusChange();

		console.log("Stopped polling for payout updates");
	}

	/**
	 * Update the current payouts list (called when user creates new payouts)
	 */
	updateCurrentPayouts(payouts: Payout[]): void {
		this.currentPayouts = payouts ? [...payouts] : [];
	}

	/**
	 * Update the current page and per page settings
	 */
	updateCurrentPage(page: number, perPage: number = 10): void {
		this.currentPage = page;
		this.perPage = perPage;
	}

	/**
	 * Add callback for payout updates
	 */
	onPayoutUpdate(callback: PayoutUpdateCallback): () => void {
		this.payoutUpdateCallbacks.add(callback);

		return () => {
			this.payoutUpdateCallbacks.delete(callback);
		};
	}

	/**
	 * Add callback for polling status updates
	 */
	onStatusChange(callback: PollingStatusCallback): () => void {
		this.statusCallbacks.add(callback);

		return () => {
			this.statusCallbacks.delete(callback);
		};
	}

	/**
	 * Get current polling status
	 */
	getStatus(): PollingStatus {
		return {
			isPolling: this.isPolling,
			lastUpdate: this.lastUpdate,
			error: this.error,
			pollCount: this.pollCount,
		};
	}

	private async scheduleNextPoll(): Promise<void> {
		if (!this.isPolling) return;

		this.pollInterval = window.setTimeout(async () => {
			if (this.isPolling) {
				await this.performPoll();
				this.scheduleNextPoll();
			}
		}, this.POLL_INTERVAL);
	}

	private async performPoll(): Promise<void> {
		this.pollCount++;

		// Prevent infinite polling
		if (this.pollCount > this.MAX_POLL_COUNT) {
			console.warn("Max poll count reached, stopping polling");
			this.stopPolling();
			return;
		}

		const result = await retryService.retry(
			async () => {
				// Get current payouts from API for the current page
				const response = await payoutService.getPayouts(
					this.currentPage,
					this.perPage
				);
				return response.items;
			},
			RETRY_CONFIGS.CONSERVATIVE, // Use conservative retry for background polling
			`polling-${this.pollCount}`
		);

		if (result.success) {
			const newPayouts = result.data!;

			// Check for changes
			const changes = this.detectChanges(this.currentPayouts, newPayouts);

			if (changes.length > 0) {
				console.log(
					`Found ${changes.length} payout changes:`,
					changes.map((p) => ({ id: p.id, status: p.status }))
				);

				// Update current payouts
				this.currentPayouts = newPayouts;
				this.lastUpdate = new Date();
				this.error = null;

				// Notify callbacks
				this.notifyPayoutUpdates(newPayouts);
				this.notifyStatusChange();
			} else {
				// No changes, just update status
				this.lastUpdate = new Date();
				this.error = null;
				this.notifyStatusChange();
			}
		} else {
			this.error =
				result.error instanceof Error 
					? result.error.message 
					: typeof result.error === 'string' 
						? result.error 
						: "Unable to fetch payout updates";
			this.notifyStatusChange();

			// On error, wait longer before next poll
			if (this.isPolling) {
				this.pollInterval = window.setTimeout(() => {
					if (this.isPolling) {
						this.scheduleNextPoll();
					}
				}, this.ERROR_RETRY_DELAY);
			}
		}
	}

	private detectChanges(oldPayouts: Payout[], newPayouts: Payout[]): Payout[] {
		const changes: Payout[] = [];

		// Safety check for undefined arrays
		if (!oldPayouts || !newPayouts) {
			return changes;
		}

		// Create maps for efficient lookup
		const oldMap = new Map(oldPayouts.map((p) => [p.id, p]));
		const newMap = new Map(newPayouts.map((p) => [p.id, p]));

		// Check for status changes in existing payouts
		for (const [id, newPayout] of newMap) {
			const oldPayout = oldMap.get(id);

			if (oldPayout && oldPayout.status !== newPayout.status) {
				changes.push(newPayout);
			}
		}

		// Check for new payouts
		for (const [id, newPayout] of newMap) {
			if (!oldMap.has(id)) {
				changes.push(newPayout);
			}
		}

		return changes;
	}

	private notifyPayoutUpdates(payouts: Payout[]): void {
		this.payoutUpdateCallbacks.forEach((callback) => {
			try {
				callback(payouts);
			} catch (error) {
				console.error("Error in payout update callback:", error);
			}
		});
	}

	private notifyStatusChange(): void {
		const status = this.getStatus();
		this.statusCallbacks.forEach((callback) => {
			try {
				callback(status);
			} catch (error) {
				console.error("Error in status callback:", error);
			}
		});
	}

	/**
	 * Cleanup resources
	 */
	destroy(): void {
		this.stopPolling();
		this.payoutUpdateCallbacks.clear();
		this.statusCallbacks.clear();
	}
}

// Export singleton instance
export const pollingService = new PollingService();
