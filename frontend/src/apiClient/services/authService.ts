/**
 * Authentication service for communicating with the backend OAuth API.
 * Handles secure OAuth 2.0 flow with state, nonce, and PKCE.
 */

import type { UserProfile } from '../../types';
import { createHeadersWithCorrelationId } from '../../utils/correlationService';
import { retryService, RETRY_CONFIGS, isBackendDownError } from '../../utils/retryService';

export type { UserProfile };

export interface TokenResponse {
	access_token: string;
	token_type: string;
	expires_in: number;
	user: UserProfile;
}

export interface OAuthLoginResponse {
	authorization_url: string;
	state: string;
	code_verifier: string;
	expires_at: string;
}

export interface AuthError {
	error: string;
	error_description: string;
	correlation_id?: string;
}

class AuthService {
	private baseUrl: string;
	private userKey = "user_profile";

	constructor() {
		this.baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
	}

	/**
	 * Initiate OAuth login flow with backend
	 */
	async initiateLogin(): Promise<OAuthLoginResponse> {
		const headers = createHeadersWithCorrelationId();
		const correlationId = headers["X-Correlation-ID"];

		// First, check if backend is reachable
		const isBackendHealthy = await retryService.checkBackendHealth(this.baseUrl);
		if (!isBackendHealthy) {
			const error = new Error("BACKEND_UNAVAILABLE:The server is currently unavailable. Please try again in a moment.");
			(error as any).isBackendDown = true;
			throw error;
		}

		const result = await retryService.retry(
			async () => {
				const response = await fetch(`${this.baseUrl}/auth/login`, {
					method: "POST",
					headers,
					body: JSON.stringify({
						redirect_uri: `${this.baseUrl}/auth/callback`, // URL where Google will send the user back after they complete authentication
					}),
				});

				if (!response.ok) {
					const errorData: AuthError = await response.json();
					const error = new Error(
						errorData.error_description || "Failed to initiate login"
					);
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
			console.error("Login initiation failed after retries:", result.error);
			
			// Check if this is a backend down error
			if (isBackendDownError(result.error)) {
				const error = new Error("BACKEND_UNAVAILABLE:The server is currently unavailable. Please try again in a moment.");
				(error as any).isBackendDown = true;
				throw error;
			}
			
			throw result.error;
		}

		return result.data!;
	}

	
	/**
	 * Get current user information
	 */
	async getCurrentUser(): Promise<UserProfile> {
		const headers = createHeadersWithCorrelationId();
		const correlationId = headers["X-Correlation-ID"];

		const result = await retryService.retry(
			async () => {
				const response = await fetch(`${this.baseUrl}/auth/me`, {
					credentials: "include",
					headers,
					signal: AbortSignal.timeout(5000),
				});

				if (!response.ok) {
					if (response.status === 401) {
						await this.refreshToken();
						return this.getCurrentUser();
					}
					const errorData: AuthError = await response.json();
					let errorMessage = errorData.error_description || "Failed to get user info";
					
					if (errorMessage.includes('session has expired') || errorMessage.includes('expired')) {
						errorMessage = "Server is currently unavailable. Please try again later.";
					}
					
					const error = new Error(errorMessage);
					(error as any).status = response.status;
					(error as any).response = response;
					throw error;
				}

				const userData: UserProfile = await response.json();


				sessionStorage.setItem(this.userKey, JSON.stringify(userData));

				return userData;
			},
			RETRY_CONFIGS.STANDARD,
			correlationId
		);

		if (!result.success) {
			console.error("Get current user failed after retries:", result.error);
			throw result.error;
		}

		return result.data!;
	}

	/**
	 * Refresh access token
	 */
	async refreshToken(): Promise<TokenResponse> {
		const headers = createHeadersWithCorrelationId();
		const correlationId = headers["X-Correlation-ID"];

		const result = await retryService.retry(
			async () => {
				const response = await fetch(`${this.baseUrl}/auth/refresh`, {
					method: "POST",
					credentials: "include", // Include cookies
					headers,
					signal: AbortSignal.timeout(5000), // 5 second timeout
				});

				if (!response.ok) {
					const errorData: AuthError = await response.json();
					let errorMessage = errorData.error_description || "Token refresh failed";
					
					// Convert session expiration errors to server unavailability when server is down
					if (errorMessage.includes('session has expired') || errorMessage.includes('expired')) {
						errorMessage = "Server is currently unavailable. Please try again later.";
					}
					
					const error = new Error(errorMessage);
					(error as any).status = response.status;
					(error as any).response = response;
					throw error;
				}

				const tokenData: TokenResponse = await response.json();
				// Store user data (token is in cookie)
				sessionStorage.setItem(this.userKey, JSON.stringify(tokenData.user));

				return tokenData;
			},
			RETRY_CONFIGS.QUICK, // Use quick retry for token refresh
			correlationId
		);

		if (!result.success) {
			console.error("Token refresh failed after retries:", result.error);
			// Clear stored auth data on refresh failure
			this.clearAuthData();
			throw result.error;
		}

		return result.data!;
	}

	/**
	 * Logout user
	 */
	async logout(): Promise<void> {
		try {
			const headers = createHeadersWithCorrelationId();
			const correlationId = headers["X-Correlation-ID"];

			await fetch(`${this.baseUrl}/auth/logout`, {
				method: "POST",
				credentials: "include", // Include cookies
				headers,
				body: JSON.stringify({
					correlation_id: correlationId,
				}),
			});

		} catch (error) {
			console.error("Logout request failed:", error);
		} finally {
			// Always clear local auth data
			this.clearAuthData();
		}
	}

	/**
	 * Check if user is authenticated
	 */
	isAuthenticated(): boolean {
		const user = this.getStoredUser();
		return !!user;
	}

	/**
	 * Get stored user profile
	 */
	getStoredUser(): UserProfile | null {
		const userStr = sessionStorage.getItem(this.userKey);
		if (!userStr) return null;

		try {
			return JSON.parse(userStr);
		} catch {
			return null;
		}
	}

	/**
	 * Clear authentication data from sessionStorage
	 */
	public clearAuthData(): void {
		sessionStorage.removeItem(this.userKey);
	}


	/**
	 * Redirect to OAuth URL (full page redirect)
	 */
	redirectToOAuth(authUrl: string): void {
		window.location.href = authUrl;
	}
}

export const authService = new AuthService();
