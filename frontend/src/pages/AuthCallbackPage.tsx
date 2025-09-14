import { useEffect, useState, memo } from "react";
import { Typography, Box, CircularProgress } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { authService } from "../apiClient/services/authService";
import { useAuth } from "../auth/AuthContext";
import { isBackendDownError } from "../utils/retryService";

const AuthCallbackPage = memo(() => {
	const navigate = useNavigate();
	const { setUser } = useAuth();
	const [loading, setLoading] = useState(true);


	useEffect(() => {
		const handleCallback = async () => {
			try {
				const urlParams = new URLSearchParams(window.location.search);
				const error = urlParams.get("error");

				if (error) {
					// Redirect to login page with error information
					// Don't show error messages here - let login page handle them
					setLoading(false);
					navigate(`/login?error=${encodeURIComponent(error)}`);
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
							setLoading(false);
							navigate("/login?error=server_error");
						} else {
							setLoading(false);
							navigate("/login?error=profile_failed");
						}
					}
				}, 150);
			} catch (err) {
				setLoading(false);
				navigate("/login?error=unexpected");
			}
		};
		handleCallback();
	}, [navigate, setUser]);


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
			{loading && <CircularProgress size={40} aria-label="Processing authentication" />}
			<Typography variant='h6' color='text.secondary'>
				Completing authentication...
			</Typography>
			<Typography variant='body2' color='text.secondary' textAlign='center'>
				Please wait while we complete your login.
			</Typography>
		</Box>
	);
});

AuthCallbackPage.displayName = 'AuthCallbackPage';

export default AuthCallbackPage;
