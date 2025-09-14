import { useEffect, useState, memo } from "react";
import { Typography, Box, CircularProgress, Alert, Button } from "@mui/material";
import { Refresh, WifiOff, Error as ErrorIcon } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import { authService } from "../apiClient/services/authService";
import { useAuth } from "../auth/AuthContext";
import { retryService, isBackendDownError } from "../utils/retryService";

const AuthCallbackPage = memo(() => {
	const navigate = useNavigate();
	const { setUser } = useAuth();
	const [errorMsg, setErrorMsg] = useState<string | null>(null);
	const [errorType, setErrorType] = useState<'backend_down' | 'auth_failed' | 'network' | 'unknown'>('unknown');
	const [loading, setLoading] = useState(true);
	const [retrying, setRetrying] = useState(false);

	const handleRetry = async () => {
		setRetrying(true);
		setErrorMsg(null);
		setErrorType('unknown');
		
		try {
			// Check if backend is back up
			const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
			const isBackendHealthy = await retryService.checkBackendHealth(baseUrl);
			
			if (isBackendHealthy) {
				// Backend is back up, redirect to login
				navigate("/login");
			} else {
				// Still down
				setErrorMsg("Service is still unavailable. Please check your connection and try again.");
				setErrorType('backend_down');
			}
		} catch (error) {
			setErrorMsg("Unable to check service status. Please try again.");
			setErrorType('network');
		} finally {
			setRetrying(false);
		}
	};

	const checkBackendStatus = async (): Promise<boolean> => {
		try {
			const baseUrl = import.meta.env.VITE_API_URL || "http://localhost:8000";
			return await retryService.checkBackendHealth(baseUrl);
		} catch {
			return false;
		}
	};

	useEffect(() => {
		const handleCallback = async () => {
			try {
				const urlParams = new URLSearchParams(window.location.search);
				const error = urlParams.get("error");

				if (error) {
					// Determine error type and show appropriate message
					const isBackendDown = await checkBackendStatus();
					
					if (error === "oauth_failed" && !isBackendDown) {
						setErrorMsg("Authentication failed. Please try logging in again.");
						setErrorType('auth_failed');
					} else if (error === "oauth_failed" || error === "server_error") {
						setErrorMsg("Service temporarily unavailable. The server appears to be down.");
						setErrorType('backend_down');
					} else if (error === "missing_parameters") {
						setErrorMsg("Invalid authentication request. Please try again.");
						setErrorType('auth_failed');
					} else {
						setErrorMsg(`Authentication failed: ${error}`);
						setErrorType('unknown');
					}
					
					setLoading(false);
					// No auto-redirect - let user decide when to retry
					return;
				}

				// If we reach this point, the OAuth callback was successful
				// The backend has set the HTTP-only cookie and redirected us here
				// Add a small delay to ensure the cookie is set before we redirected

				setTimeout(async () => {
					try {
						const userProfile = await authService.getCurrentUser();
						setUser(userProfile);
						navigate("/dashboard");
					} catch (err) {
						// Check if this is a backend down error
						if (isBackendDownError(err)) {
							setErrorMsg("Service temporarily unavailable. Unable to complete login.");
							setErrorType('backend_down');
						} else {
							setErrorMsg("Failed to fetch user profile after login. Please try again.");
							setErrorType('auth_failed');
						}
						setLoading(false);
						// No auto-redirect - let user decide when to retry
					}
				}, 150);
			} catch (err) {
				setErrorMsg("Unexpected error during authentication. Please try again.");
				setErrorType('unknown');
				setLoading(false);
				// No auto-redirect - let user decide when to retry
			}
		};
		handleCallback();
	}, [navigate, setUser]);

	const getErrorIcon = () => {
		switch (errorType) {
			case 'backend_down':
				return <WifiOff />;
			case 'network':
				return <WifiOff />;
			case 'auth_failed':
				return <ErrorIcon />;
			default:
				return <ErrorIcon />;
		}
	};

	const getErrorSeverity = () => {
		switch (errorType) {
			case 'backend_down':
			case 'network':
				return 'warning';
			default:
				return 'error';
		}
	};

	const getRetryButtonText = () => {
		if (retrying) return "Checking...";
		switch (errorType) {
			case 'backend_down':
			case 'network':
				return "Check Connection & Retry";
			default:
				return "Try Again";
		}
	};

	return (
		<Box
			display='flex'
			flexDirection='column'
			alignItems='center'
			justifyContent='center'
			minHeight='100vh'
			gap={2}
			role="status"
			aria-live="polite"
		>
			{errorMsg ? (
				<Alert 
					severity={getErrorSeverity()} 
					sx={{ mt: 2, maxWidth: 500 }} 
					role="alert"
					icon={getErrorIcon()}
				>
					<Box display="flex" flexDirection="column" gap={2}>
						<Typography variant="body1" fontWeight="medium">
							{errorMsg}
						</Typography>
						
						{errorType === 'backend_down' && (
							<Typography variant="body2" color="text.secondary">
								This usually means the server is temporarily unavailable. Please check your connection and try again.
							</Typography>
						)}
						
						{errorType === 'auth_failed' && (
							<Typography variant="body2" color="text.secondary">
								There was an issue with the authentication process. Please try logging in again.
							</Typography>
						)}
						
						<Button
							variant="contained"
							startIcon={retrying ? <CircularProgress size={16} /> : <Refresh />}
							onClick={handleRetry}
							disabled={retrying}
							sx={{ mt: 1, alignSelf: 'flex-start' }}
						>
							{getRetryButtonText()}
						</Button>
					</Box>
				</Alert>
			) : (
				<>
					{loading && <CircularProgress size={40} aria-label="Processing authentication" />}
					<Typography variant='h6' color='text.secondary'>
						Completing authentication...
					</Typography>
					<Typography variant='body2' color='text.secondary' textAlign='center'>
						Please wait while we complete your login.
					</Typography>
				</>
			)}
		</Box>
	);
});

AuthCallbackPage.displayName = 'AuthCallbackPage';

export default AuthCallbackPage;
