// Common types used across the application

export interface UserProfile {
	id: string;
	google_id: string;
	email: string;
	name: string | null;
	picture_url: string | null;
	created_at: string;
}

export interface Payout {
	id: string;
	amount: string | number;
	currency: Currency;
	status: PayoutStatus;
	created_at: string;
	updated_at: string;
	user_id: string;
	external_id?: string;
	failure_reason?: string;
	provider_reference?: string;
	provider_status?: string;
	error_code?: string;
	error_message?: string;
}

export type Currency = "USD" | "ZAR" | "EUR";

export type PayoutStatus =
	| "pending"
	| "processing"
	| "succeeded"
	| "failed"
	| "cancelled";

export interface CreatePayoutRequest {
	amount: number;
	currency: Currency;
	idempotency_key?: string;
}

export interface CreatePayoutResponse {
	payout: Payout;
	message: string;
}

export interface PayoutsListResponse {
	items: Payout[];
	total: number;
	page: number;
	page_size: number;
}

export interface ApiError {
	detail: string;
	correlation_id?: string;
}

export interface ValidationResult {
	isValid: boolean;
	error?: string;
}

export interface PayoutFormState {
	amount: number;
	currency: Currency;
	isSubmitting: boolean;
	error: string | null;
}

export interface PayoutListState {
	payouts: Payout[];
	isLoading: boolean;
	error: string | null;
	currentPage: number;
	totalPages: number;
}

export interface PollingStatus {
	isPolling: boolean;
	lastUpdate: Date | null;
	error: string | null;
	pollCount: number;
}

export interface UsePollingReturn {
	isPolling: boolean;
	lastUpdate: Date | null;
	error: string | null;
	pollCount: number;
	startPolling: (payouts: Payout[]) => void;
	stopPolling: () => void;
	updatePayouts: (payouts: Payout[]) => void;
	updateCurrentPage: (page: number, perPage?: number) => void;
	onPayoutUpdate: (callback: (payouts: Payout[]) => void) => () => void;
}

export interface ErrorState {
	error: string | null;
	correlationId?: string;
	timestamp?: Date;
}

export interface ErrorHandlerReturn {
	error: ErrorState | null;
	handleError: (error: Error | string, correlationId?: string) => void;
	clearError: () => void;
	hasError: boolean;
}

// Component Props Types
export interface PayoutFormProps {
	onSubmit: (data: CreatePayoutRequest) => Promise<void>;
	isLoading?: boolean;
	error?: string | null;
	onErrorChange?: (error: string | null) => void;
}

export interface PayoutListProps {
	payouts: Payout[];
	isLoading?: boolean;
	error?: string | null;
	currentPage: number;
	totalPages: number;
	onPageChange: (page: number) => void;
	onErrorChange?: (error: string | null) => void;
}

export interface UserProfileProps {
	user: UserProfile;
	onLogout: () => Promise<void>;
	isLoading?: boolean;
}

export interface PollingIndicatorProps {
	isPolling: boolean;
	lastUpdate: Date | null;
	error: string | null;
	pollCount: number;
}

// Utility Types
export type StatusColor = "success" | "warning" | "info" | "error" | "default";

export interface CurrencyOption {
	code: Currency;
	label: string;
}

// API Response Types
export interface ApiResponse<T> {
	data: T;
	error?: string;
	correlationId: string;
}

export interface PaginatedResponse<T> {
	items: T[];
	total: number;
	page: number;
	page_size: number;
}
