
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
			const isAuth = authService.isAuthenticated();
			if (isAuth) {
				try {
					// Prefer stored user for fast load, else fetch fresh
					const storedUser = authService.getStoredUser();
					if (storedUser) {
						setUser(storedUser);
					} else {
						const freshUser = await authService.getCurrentUser();
						setUser(freshUser);
					}
				} catch (err) {
					authService.clearAuthData();
					setUser(null);
				}
			} else {
				setUser(null);
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
				setError(err instanceof Error ? err.message : "Login failed");
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
