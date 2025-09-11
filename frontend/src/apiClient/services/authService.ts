/**
 * Authentication service for communicating with the backend OAuth API.
 * Handles secure OAuth 2.0 flow with state, nonce, and PKCE.
 */

export interface UserProfile {
	id: string;
	google_id: string;
	email: string;
	name: string | null;
	picture_url: string | null;
	created_at: string;
}

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
	private tokenKey = "auth_token";
	private userKey = "user_profile";

	constructor() {
		this.baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
	}

	/**
	 * Initiate OAuth login flow with backend
	 */
	async initiateLogin(): Promise<OAuthLoginResponse> {
		try {
			const response = await fetch(`${this.baseUrl}/auth/login`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({
					redirect_uri: `${this.baseUrl}/auth/callback`,
				}),
			});

			if (!response.ok) {
				const errorData: AuthError = await response.json();
				throw new Error(
					errorData.error_description || "Failed to initiate login"
				);
			}

			return await response.json();
		} catch (error) {
			console.error("Login initiation failed:", error);
			throw error;
		}
	}

	/**
	 * Handle OAuth callback and exchange code for tokens
	 */
	async handleCallback(
		code: string,
		state: string,
		code_verifier: string
	): Promise<TokenResponse> {
		try {
			const response = await fetch(`${this.baseUrl}/auth/callback`, {
				method: "POST",
				headers: {
					"Content-Type": "application/json",
				},
				body: JSON.stringify({
					code,
					state,
					code_verifier,
					redirect_uri: `${this.baseUrl}/auth/callback`,
				}),
			});

			if (!response.ok) {
				const errorData: AuthError = await response.json();
				throw new Error(errorData.error_description || "OAuth callback failed");
			}

			const tokenData: TokenResponse = await response.json();
			this.storeAuthData(tokenData);

			return tokenData;
		} catch (error) {
			console.error("OAuth callback failed:", error);
			throw error;
		}
	}

	/**
	 * Get current user information
	 */
	async getCurrentUser(): Promise<UserProfile> {
		try {
			const token = this.getStoredToken();
			if (!token) {
				throw new Error("No authentication token found");
			}

			const response = await fetch(`${this.baseUrl}/auth/me`, {
				headers: {
					Authorization: `Bearer ${token}`,
					"Content-Type": "application/json",
				},
			});

			if (!response.ok) {
				if (response.status === 401) {
					// Token expired, try to refresh
					await this.refreshToken();
					return this.getCurrentUser();
				}
				const errorData: AuthError = await response.json();
				throw new Error(
					errorData.error_description || "Failed to get user info"
				);
			}

			const userData: UserProfile = await response.json();

			// Update stored user data
			sessionStorage.setItem(this.userKey, JSON.stringify(userData));

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
			const token = this.getStoredToken();
			if (!token) {
				throw new Error("No token to refresh");
			}

			const response = await fetch(`${this.baseUrl}/auth/refresh`, {
				method: "POST",
				headers: {
					Authorization: `Bearer ${token}`,
					"Content-Type": "application/json",
				},
			});

			if (!response.ok) {
				const errorData: AuthError = await response.json();
				throw new Error(errorData.error_description || "Token refresh failed");
			}

			const tokenData: TokenResponse = await response.json();
			this.storeAuthData(tokenData);

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
			const token = this.getStoredToken();
			if (token) {
				await fetch(`${this.baseUrl}/auth/logout`, {
					method: "POST",
					headers: {
						Authorization: `Bearer ${token}`,
						"Content-Type": "application/json",
					},
					body: JSON.stringify({
						correlation_id: this.generateCorrelationId(),
					}),
				});
			}
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
		const token = this.getStoredToken();
		const user = this.getStoredUser();
		return !!(token && user);
	}

	/**
	 * Get stored authentication token
	 */
	getStoredToken(): string | null {
		return sessionStorage.getItem(this.tokenKey);
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
	 * Store authentication data in sessionStorage
	 */
	private storeAuthData(tokenData: TokenResponse): void {
		sessionStorage.setItem(this.tokenKey, tokenData.access_token);
		sessionStorage.setItem(this.userKey, JSON.stringify(tokenData.user));
	}

	   /**
		* Clear authentication data from sessionStorage
		*/
	   public clearAuthData(): void {
		   sessionStorage.removeItem(this.tokenKey);
		   sessionStorage.removeItem(this.userKey);
	   }

	/**
	 * Generate correlation ID for request tracing
	 */
	private generateCorrelationId(): string {
		return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(
			/[xy]/g,
			function (c) {
				const r = (Math.random() * 16) | 0;
				const v = c === "x" ? r : (r & 0x3) | 0x8;
				return v.toString(16);
			}
		);
	}

	/**
	 * Redirect to OAuth URL (full page redirect)
	 */
	redirectToOAuth(authUrl: string): void {
		window.location.href = authUrl;
	}
}

export const authService = new AuthService();
