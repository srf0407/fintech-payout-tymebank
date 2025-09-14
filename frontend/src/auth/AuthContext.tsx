
import React, { createContext, useContext, useState, useEffect } from "react";
import type { ReactNode } from "react";
import { authService, type UserProfile } from "../apiClient/services/authService";

interface AuthContextType {
	user: UserProfile | null;
	isLoading: boolean;
	error: string | null;
	login: () => Promise<void>;
	logout: () => Promise<void>;
	clearError: () => void;
	setUser: (user: UserProfile | null) => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);


export const AuthProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
	const [user, setUser] = useState<UserProfile | null>(null);
	const [isLoading, setIsLoading] = useState(false);
	const [error, setError] = useState<string | null>(null);

	// Initialize authentication state on mount
	useEffect(() => {
		const initializeAuth = async () => {
			setIsLoading(true);
			try {
				// Try to get current user (this will check the cookie)
				const freshUser = await authService.getCurrentUser();
				setUser(freshUser);
			} catch (err) {
				// If we can't get user, clear any stored data and set user to null
				authService.clearAuthData();
				setUser(null);
			} finally {
				setIsLoading(false);
			}
		};
		initializeAuth();
	}, []);


		/**
		 * Initiates the OAuth login flow. Redirects to the provider on success.
		 */
		const login = async () => {
			setIsLoading(true);
			setError(null);
			try {
				const authData = await authService.initiateLogin();
				authService.redirectToOAuth(authData.authorization_url);
			} catch (err) {
				if (err instanceof Error && err.message.includes("BACKEND_UNAVAILABLE")) {
					// Extract user-friendly message
					const errorMessage = err.message.split(":")[1] || "The server is currently unavailable. Please try again in a moment.";
					setError(errorMessage);
				} else {
					setError(err instanceof Error ? err.message : "Login failed");
				}
			} finally {
				setIsLoading(false);
			}
		};


		/**
		 * Logs out the user and clears all authentication state.
		 */
		const logout = async () => {
			setIsLoading(true);
			setError(null);
			try {
				await authService.logout();
				setUser(null);
			} catch (err) {
				setError(err instanceof Error ? err.message : "Logout failed");
			} finally {
				setIsLoading(false);
			}
		};


		/**
		 * Clears the current authentication error.
		 */
		const clearError = () => {
			setError(null);
		};


		return (
			<AuthContext.Provider
				value={{
					user,
					isLoading,
					error,
					login,
					logout,
					clearError,
					setUser
				}}
			>
				{children}
			</AuthContext.Provider>
		);
};


/**
 * Custom hook to access authentication context.
 * Throws if used outside of AuthProvider.
 */
export const useAuth = () => {
	const ctx = useContext(AuthContext);
	if (!ctx) throw new Error("useAuth must be used within AuthProvider");
	return ctx;
};
