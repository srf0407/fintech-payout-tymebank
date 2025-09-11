/**
 * Payout service for communicating with the backend payouts API.
 */

export interface Payout {
	id: string;
	amount: number;
	currency: string;
	status: "pending" | "processing" | "succeeded" | "failed" | "cancelled";
	created_at: string;
	updated_at: string;
	user_id: string;
	external_id?: string;
	failure_reason?: string;
}

export interface CreatePayoutRequest {
	amount: number;
	currency: string;
	idempotency_key?: string;
}

export interface CreatePayoutResponse {
	payout: Payout;
	message: string;
}

export interface PayoutsListResponse {
	payouts: Payout[];
	total: number;
	page: number;
	per_page: number;
	total_pages: number;
}

export interface ApiError {
	detail: string;
	correlation_id?: string;
}

class PayoutService {
	private baseUrl: string;

	constructor() {
		this.baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
	}

	/**
	 * Create a new payout
	 */
	async createPayout(
		payoutData: CreatePayoutRequest
	): Promise<CreatePayoutResponse> {
		try {
			const response = await fetch(`${this.baseUrl}/payouts`, {
				method: "POST",
				credentials: "include", // Include cookies
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify(payoutData),
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

	/**
	 * Get paginated list of payouts
	 */
	async getPayouts(
		page: number = 1,
		perPage: number = 10
	): Promise<PayoutsListResponse> {
		try {
			const response = await fetch(
				`${this.baseUrl}/payouts?page=${page}&per_page=${perPage}`,
				{
					credentials: "include", // Include cookies
					headers: {
						"Content-Type": "application/json",
					},
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

	/**
	 * Get a specific payout by ID
	 */
	async getPayout(payoutId: string): Promise<Payout> {
		try {
			const response = await fetch(`${this.baseUrl}/payouts/${payoutId}`, {
				credentials: "include", // Include cookies
				headers: {
					"Content-Type": "application/json",
				},
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

	/**
	 * Generate idempotency key for payout creation
	 */
	generateIdempotencyKey(): string {
		return `payout_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
	}
}

export const payoutService = new PayoutService();
