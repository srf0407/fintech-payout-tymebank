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

export type { Payout };

class PayoutService {
	private baseUrl: string;

	constructor() {
		this.baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
	}


	async createPayout(
		payoutData: CreatePayoutRequest
	): Promise<CreatePayoutResponse> {
		try {
			const { idempotency_key, ...bodyData } = payoutData;

			const headers = createHeadersWithCorrelationId({
				...(idempotency_key && { "Idempotency-Key": idempotency_key }),
			});

			const correlationId = headers["X-Correlation-ID"];

			const response = await fetch(`${this.baseUrl}/payouts`, {
				method: "POST",
				credentials: "include", // Include cookies
				headers,
				body: JSON.stringify(bodyData),
			});

			if (!response.ok) {
				const errorData: ApiError = await response.json();
				throw new Error(errorData.detail || "Failed to create payout");
			}

			return await response.json();
		} catch (error) {
			console.error("Create payout failed:", error);
			throw error;
		}
	}

	async getPayouts(
		page: number = 1,
		perPage: number = 10
	): Promise<PayoutsListResponse> {
		try {
			const headers = createHeadersWithCorrelationId();
			const correlationId = headers["X-Correlation-ID"];

			const response = await fetch(
				`${this.baseUrl}/payouts?page=${page}&per_page=${perPage}`,
				{
					credentials: "include", // Include cookies
					headers,
				}
			);

			if (!response.ok) {
				const errorData: ApiError = await response.json();
				throw new Error(errorData.detail || "Failed to fetch payouts");
			}

			return await response.json();
		} catch (error) {
			console.error("Get payouts failed:", error);
			throw error;
		}
	}


	async getPayout(payoutId: string): Promise<Payout> {
		try {
			const headers = createHeadersWithCorrelationId();
			const correlationId = headers["X-Correlation-ID"];

			const response = await fetch(`${this.baseUrl}/payouts/${payoutId}`, {
				credentials: "include", // Include cookies
				headers,
			});

			if (!response.ok) {
				const errorData: ApiError = await response.json();
				throw new Error(errorData.detail || "Failed to fetch payout");
			}

			return await response.json();
		} catch (error) {
			console.error("Get payout failed:", error);
			throw error;
		}
	}

	generateIdempotencyKey(): string {
		return `payout_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
	}
	validatePayoutData(
		amount: number,
		currency: Currency
	): ValidationResult {
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
