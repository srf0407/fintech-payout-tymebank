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
import { Google as GoogleIcon } from "@mui/icons-material";
import styles from "./LoginPage.module.css";
import { useAuth } from "../auth/AuthContext";
import { useNavigate } from "react-router-dom";

const LoginPage = memo(() => {
	const { user, isLoading, error, login, clearError } = useAuth();
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
			// Set error from URL parameter
			const errorMessage = decodeURIComponent(urlError);
			// We need to set this error in the auth context
			// For now, we'll just log it and show a generic message
			console.error("OAuth error from URL:", errorMessage);
			// Clean up URL
			window.history.replaceState({}, document.title, window.location.pathname);
		}
	}, []);

	const handleGoogleLogin = useCallback(async () => {
		clearError();
		await login();
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

					{/* Error Display */}
					{error && (
						<Alert
							severity='error'
							onClose={clearError}
							sx={{ width: "100%", mb: 2 }}
						>
							{error}
						</Alert>
					)}

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
