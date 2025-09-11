import { useEffect, useState, memo } from "react";
import { Typography, Box, CircularProgress, Alert } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { authService } from "../apiClient/services/authService";
import { useAuth } from "../auth/AuthContext";

const AuthCallbackPage = memo(() => {
	const navigate = useNavigate();
	const { setUser } = useAuth();
	const [errorMsg, setErrorMsg] = useState<string | null>(null);
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		const handleCallback = async () => {
			try {
				const urlParams = new URLSearchParams(window.location.search);
				const error = urlParams.get("error");

				if (error) {
					setErrorMsg("Authentication failed: " + error);
					setLoading(false);
					setTimeout(
						() => navigate("/login?error=" + encodeURIComponent(error)),
						2500
					);
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
						setErrorMsg("Failed to fetch user profile after login.");
						setLoading(false);
						setTimeout(() => navigate("/login?error=profile_failed"), 2500);
					}
				}, 150);
			} catch (err) {
				setErrorMsg("Unexpected error during authentication.");
				setLoading(false);
				setTimeout(() => navigate("/login?error=unexpected"), 2500);
			}
		};
		handleCallback();
	}, [navigate]);

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
				<Alert severity='error' sx={{ mt: 2, maxWidth: 400 }} role="alert">
					{errorMsg}
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
