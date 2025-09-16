/**
 * Payout service for communicating with the backend payouts API.
 */

import type { 
	Payout, 
	CreatePayoutRequest, 
	CreatePayoutResponse, 
	PayoutsListResponse, 
	ApiError,
	Currency,
	ValidationResult
} from '../../types';
import { createHeadersWithCorrelationId } from '../../utils/correlationService';
import { retryService, RETRY_CONFIGS } from '../../utils/retryService';

export type { Payout };

class PayoutService {
	private baseUrl: string;

	constructor() {
		this.baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
	}

	async createPayout(
		payoutData: CreatePayoutRequest
	): Promise<CreatePayoutResponse> {
		const { idempotency_key, ...bodyData } = payoutData;

		const headers = createHeadersWithCorrelationId({
			...(idempotency_key && { "Idempotency-Key": idempotency_key }),
		});

		const correlationId = headers["X-Correlation-ID"];

		const result = await retryService.retry(
			async () => {
				const response = await fetch(`${this.baseUrl}/payouts`, {
					method: "POST",
					credentials: "include",
					headers,
					body: JSON.stringify(bodyData),
					signal: AbortSignal.timeout(10000),
				});

				if (!response.ok) {
					const errorData: ApiError = await response.json();
					// Convert errorData.detail to string safely
					let errorMessage = "Failed to create payout";
					if (errorData.detail) {
						if (typeof errorData.detail === "string") {
							errorMessage = errorData.detail;
						} else if (typeof errorData.detail === "object") {
							errorMessage =
								errorData.detail.message || JSON.stringify(errorData.detail);
						}
					}

					// Convert session expiration errors to server unavailability when server is down
					if (
						errorMessage.includes("session has expired") ||
						errorMessage.includes("expired")
					) {
						errorMessage =
							"Server is currently unavailable. Please try again later.";
					}

					const error = new Error(errorMessage);
					(error as any).status = response.status;
					(error as any).response = response;
					throw error;
				}

				return await response.json();
			},
			RETRY_CONFIGS.AGGRESSIVE, // Use aggressive retry for payout creation
			correlationId
		);

		if (!result.success) {
			console.error("Create payout failed after retries:", result.error);
			throw result.error;
		}

		return result.data!;
	}

	/**
	 * Current approach: Simple pagination with query parameters
	
	 * 3. Real-time subscriptions:Server-Sent Events for live updates instead of polling
	 *    - Instant updates, better UX, lower server load
	 *    - Rejected: Additional complexity, polling works fine for MVP
	 * 
	 * 
	 * Current approach chosen for simplicity and rapid development.
	 */
	async getPayouts(
		page: number = 1,
		perPage: number = 10
	): Promise<PayoutsListResponse> {
		const headers = createHeadersWithCorrelationId();
		const correlationId = headers["X-Correlation-ID"];

		const result = await retryService.retry(
			async () => {
				const response = await fetch(
					`${this.baseUrl}/payouts?page=${page}&per_page=${perPage}`,
					{
						credentials: "include", // Include cookies
						headers,
						signal: AbortSignal.timeout(5000), // 5 second timeout
					}
				);

				if (!response.ok) {
					const errorData: ApiError = await response.json();
					// Convert errorData.detail to string safely
					let errorMessage = "Failed to fetch payouts";
					if (errorData.detail) {
						if (typeof errorData.detail === "string") {
							errorMessage = errorData.detail;
						} else if (typeof errorData.detail === "object") {
							errorMessage =
								errorData.detail.message || JSON.stringify(errorData.detail);
						}
					}

					// Convert session expiration errors to server unavailability when server is down
					if (
						errorMessage.includes("session has expired") ||
						errorMessage.includes("expired")
					) {
						errorMessage =
							"Server is currently unavailable. Please try again later.";
					}

					const error = new Error(errorMessage);
					(error as any).status = response.status;
					(error as any).response = response;
					throw error;
				}

				return await response.json();
			},
			RETRY_CONFIGS.STANDARD,
			correlationId
		);

		if (!result.success) {
			console.error("Get payouts failed after retries:", result.error);
			throw result.error;
		}

		return result.data!;
	}

	// Ai hallucination no get payout end point even on be
	// async getPayout(payoutId: string): Promise<Payout> {
	// 	const headers = createHeadersWithCorrelationId();
	// 	const correlationId = headers["X-Correlation-ID"];

	// 	const result = await retryService.retry(
	// 		async () => {
	// 			const response = await fetch(`${this.baseUrl}/payouts/${payoutId}`, {
	// 				credentials: "include", // Include cookies
	// 				headers,
	// 			});

	// 			if (!response.ok) {
	// 					const errorData: ApiError = await response.json();
	// 					let errorMessage = "Failed to fetch payout";
	// 					if (errorData.detail) {
	// 						if (typeof errorData.detail === "string") {
	// 							errorMessage = errorData.detail;
	// 						} else if (typeof errorData.detail === "object") {
	// 							errorMessage =
	// 								errorData.detail.message || JSON.stringify(errorData.detail);
	// 						}
	// 					}
	// 					const error = new Error(errorMessage);
	// 					(error as any).status = response.status;
	// 					(error as any).response = response;
	// 					throw error;
	// 			}

	// 			return await response.json();
	// 		},
	// 		RETRY_CONFIGS.STANDARD,
	// 		correlationId
	// 	);

	// 	if (!result.success) {
	// 		console.error("Get payout failed after retries:", result.error);
	// 		throw result.error;
	// 	}

	// 	return result.data!;
	// }

	generateIdempotencyKey(): string {
		return `payout_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
	}
	validatePayoutData(amount: number, currency: Currency): ValidationResult {
		if (amount <= 0) {
			return { isValid: false, error: "Amount must be greater than 0" };
		}

		if (amount > 1000000) {
			return { isValid: false, error: "Amount cannot exceed 1,000,000" };
		}

		const amountStr = amount.toString();
		const decimalParts = amountStr.split(".");
		if (decimalParts.length > 1 && decimalParts[1].length > 2) {
			return { isValid: false, error: "Amount can only have 2 decimal places" };
		}

		const validCurrencies = ["USD", "ZAR", "EUR"];
		if (!validCurrencies.includes(currency)) {
			return { isValid: false, error: "Invalid currency selected" };
		}

		return { isValid: true };
	}
}

export const payoutService = new PayoutService();
