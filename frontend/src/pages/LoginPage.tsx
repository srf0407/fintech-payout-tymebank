import { useEffect, memo, useCallback } from "react";
import {
	Typography,
	Box,
	Paper,
	Divider,
	Button,
	Alert,
	CircularProgress,
} from "@mui/material";
import { Google as GoogleIcon, WifiOff, Error as ErrorIcon } from "@mui/icons-material";
import styles from "./LoginPage.module.css";
import { useAuth } from "../auth/AuthContext";
import { useNavigate } from "react-router-dom";

const LoginPage = memo(() => {
	const { user, isLoading, error, login, clearError, setError } = useAuth();
	const navigate = useNavigate();

	// Redirect to dashboard if already logged in
	useEffect(() => {
		if (user) {
			navigate("/dashboard");
		}
	}, [user, navigate]);

	// Check for error parameters in URL
	useEffect(() => {
		const urlParams = new URLSearchParams(window.location.search);
		const urlError = urlParams.get("error");
		if (urlError) {
			let errorMessage = "";
			switch (urlError) {
				case "oauth_failed":
					errorMessage = "Authentication failed. Please try logging in again.";
					break;
				case "server_error":
					errorMessage = "The server is currently unavailable. Please try again in a moment.";
					break;
				case "missing_parameters":
					errorMessage = "Invalid authentication request. Please try again.";
					break;
				case "profile_failed":
					errorMessage = "Failed to fetch user profile after login. Please try again.";
					break;
				case "unexpected":
					errorMessage = "Unexpected error during authentication. Please try again.";
					break;
				default:
					errorMessage = `Authentication failed: ${urlError}`;
			}
			
			clearError(); 
			setTimeout(() => {
				setError(errorMessage);
			}, 100);
			
			window.history.replaceState({}, document.title, window.location.pathname);
		}
	}, [clearError, setError]);

	const getErrorType = (errorMessage: string): 'backend_down' | 'auth_failed' | 'network' | 'unknown' => {
		if (errorMessage.includes("server is currently unavailable") || 
			errorMessage.includes("BACKEND_UNAVAILABLE") ||
			errorMessage.includes("server is temporarily unavailable")) {
			return 'backend_down';
		}
		if (errorMessage.includes("authentication") || 
			errorMessage.includes("login failed") ||
			errorMessage.includes("auth")) {
			return 'auth_failed';
		}
		if (errorMessage.includes("network") || 
			errorMessage.includes("connection") ||
			errorMessage.includes("fetch")) {
			return 'network';
		}
		return 'unknown';
	};

	const getErrorIcon = (errorType: 'backend_down' | 'auth_failed' | 'network' | 'unknown') => {
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

	const getErrorSeverity = (errorType: 'backend_down' | 'auth_failed' | 'network' | 'unknown') => {
		switch (errorType) {
			case 'backend_down':
			case 'network':
				return 'warning';
			default:
				return 'error';
		}
	};


	const handleGoogleLogin = useCallback(async () => {
		clearError();
		try {
			await login();
		} catch (error) {
			console.error("Login failed:", error);
		}
	}, [clearError, login]);

	return (
		<div className={styles.root}>
			<Paper elevation={3} className={styles.box}>
				<Box display='flex' flexDirection='column' alignItems='center' gap={2}>
					<img
						src='/fintech-logo.svg'
						alt='Fintech Payout Logo'
						width={56}
						height={56}
						style={{ marginBottom: 8 }}
						onError={(e) => (e.currentTarget.style.display = "none")}
					/>
					<Typography variant='h4' component='h1' gutterBottom>
						TymeBank Payouts
					</Typography>
					<Typography variant='body1' gutterBottom textAlign='center'>
						Secure, fast, and reliable payouts for your business.
					</Typography>
					<Divider style={{ width: "100%", margin: "16px 0" }} />

					{/* Enhanced Error Display */}
					{error && (() => {
						const errorType = getErrorType(error);
						return (
							<Alert
								severity={getErrorSeverity(errorType)}
								onClose={clearError}
								sx={{ width: "100%", mb: 2 }}
								icon={getErrorIcon(errorType)}
							>
								<Box display="flex" flexDirection="column" gap={2}>
									<Typography variant="body1" fontWeight="medium">
										{error}
									</Typography>
									
									{errorType === 'backend_down' && (
										<Typography variant="body2" color="text.secondary">
											This usually means the server is temporarily unavailable. Please try again in a moment.
										</Typography>
									)}
									
									{errorType === 'auth_failed' && (
										<Typography variant="body2" color="text.secondary">
											There was an issue with the authentication process. Please try logging in again.
										</Typography>
									)}
									
									{errorType === 'network' && (
										<Typography variant="body2" color="text.secondary">
											There seems to be a network connectivity issue. Please check your internet connection.
										</Typography>
									)}
								</Box>
							</Alert>
						);
					})()}

					{/* Login Button */}
					<Button
						variant='outlined'
						size='large'
						startIcon={
							isLoading ? <CircularProgress size={20} /> : <GoogleIcon />
						}
						onClick={handleGoogleLogin}
						disabled={isLoading}
						aria-label={isLoading ? "Signing in with Google" : "Continue with Google"}
						aria-describedby="login-description"
						sx={{
							width: "100%",
							height: 48,
							fontSize: "16px",
							fontWeight: 500,
							borderColor: "#dadce0",
							color: "#3c4043",
							"&:hover": {
								borderColor: "#dadce0",
								backgroundColor: "#f8f9fa",
							},
						}}
					>
						{isLoading ? "Signing in..." : "Continue with Google"}
					</Button>

					<Typography
						variant='body2'
						color='text.secondary'
						textAlign='center'
						sx={{ mt: 2 }}
						id="login-description"
					>
						By continuing, you agree to our Terms of Service and Privacy Policy.
					</Typography>
				</Box>
			</Paper>
		</div>
	);
});

LoginPage.displayName = 'LoginPage';

export default LoginPage;
