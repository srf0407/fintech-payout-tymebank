/**
 * Authentication service for communicating with the backend OAuth API.
 * Handles secure OAuth 2.0 flow with state, nonce, and PKCE.
 */

import type { UserProfile } from '../../types';
import { createHeadersWithCorrelationId, logCorrelationId } from '../../utils/correlationService';

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
		try {
			const headers = createHeadersWithCorrelationId();
			const correlationId = headers["X-Correlation-ID"];
			logCorrelationId(correlationId, "Initiating OAuth login");

			const response = await fetch(`${this.baseUrl}/auth/login`, {
				method: "POST",
				headers,
				body: JSON.stringify({
					redirect_uri: `${this.baseUrl}/auth/callback`,
				}),
			});

			if (!response.ok) {
				const errorData: AuthError = await response.json();
				logCorrelationId(correlationId, `Login initiation failed: ${errorData.error_description || "Unknown error"}`);
				throw new Error(
					errorData.error_description || "Failed to initiate login"
				);
			}

			logCorrelationId(correlationId, "OAuth login initiated successfully");
			return await response.json();
		} catch (error) {
			console.error("Login initiation failed:", error);
			throw error;
		}
	}

	
	/**
	 * Get current user information
	 */
	async getCurrentUser(): Promise<UserProfile> {
		try {
			const headers = createHeadersWithCorrelationId();
			const correlationId = headers["X-Correlation-ID"];
			logCorrelationId(correlationId, "Getting current user");

			const response = await fetch(`${this.baseUrl}/auth/me`, {
				credentials: "include", // Include cookies
				headers,
			});

			if (!response.ok) {
				if (response.status === 401) {
					// Token expired, try to refresh
					logCorrelationId(correlationId, "Token expired, attempting refresh");
					await this.refreshToken();
					return this.getCurrentUser();
				}
				const errorData: AuthError = await response.json();
				logCorrelationId(correlationId, `Get current user failed: ${errorData.error_description || "Unknown error"}`);
				throw new Error(
					errorData.error_description || "Failed to get user info"
				);
			}

			const userData: UserProfile = await response.json();

			// Update stored user data
			sessionStorage.setItem(this.userKey, JSON.stringify(userData));

			logCorrelationId(correlationId, "Current user retrieved successfully");
			return userData;
		} catch (error) {
			console.error("Get current user failed:", error);
			throw error;
		}
	}

	/**
	 * Refresh access token
	 */
	async refreshToken(): Promise<TokenResponse> {
		try {
			const headers = createHeadersWithCorrelationId();
			const correlationId = headers["X-Correlation-ID"];
			logCorrelationId(correlationId, "Refreshing access token");

			const response = await fetch(`${this.baseUrl}/auth/refresh`, {
				method: "POST",
				credentials: "include", // Include cookies
				headers,
			});

			if (!response.ok) {
				const errorData: AuthError = await response.json();
				logCorrelationId(correlationId, `Token refresh failed: ${errorData.error_description || "Unknown error"}`);
				throw new Error(errorData.error_description || "Token refresh failed");
			}

			const tokenData: TokenResponse = await response.json();
			// Store user data (token is in cookie)
			sessionStorage.setItem(this.userKey, JSON.stringify(tokenData.user));

			logCorrelationId(correlationId, "Token refreshed successfully");
			return tokenData;
		} catch (error) {
			console.error("Token refresh failed:", error);
			// Clear stored auth data on refresh failure
			this.clearAuthData();
			throw error;
		}
	}

	/**
	 * Logout user
	 */
	async logout(): Promise<void> {
		try {
			const headers = createHeadersWithCorrelationId();
			const correlationId = headers["X-Correlation-ID"];
			logCorrelationId(correlationId, "Logging out user");

			await fetch(`${this.baseUrl}/auth/logout`, {
				method: "POST",
				credentials: "include", // Include cookies
				headers,
				body: JSON.stringify({
					correlation_id: correlationId,
				}),
			});

			logCorrelationId(correlationId, "User logged out successfully");
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
