import { memo, useCallback, useEffect } from "react";
import { Box, CircularProgress, Alert } from "@mui/material";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth/AuthContext";
import { usePolling } from "../hooks/usePolling";
import { usePayoutList } from "../hooks/usePayoutList";
import { useErrorHandler } from "../hooks/useErrorHandler";
import UserProfile, {
	PollingIndicator,
} from "../components/layout/UserProfile";
import PayoutForm from "../components/forms/PayoutForm";
import PayoutList from "../components/lists/PayoutList";
import { payoutService } from "../apiClient/services/payoutService";
import type { CreatePayoutRequest } from "../types";
import styles from "./DashboardPage.module.css";

const DashboardPage = memo(() => {
	const { user, logout, isLoading: authLoading } = useAuth();
	const navigate = useNavigate();
	const { handleError, clearError, hasError, error } = useErrorHandler();

	const {
		isPolling,
		lastUpdate,
		error: pollingError,
		pollCount,
		startPolling,
		stopPolling,
		updatePayouts,
		updateCurrentPage,
		onPayoutUpdate,
	} = usePolling();

	const {
		payouts,
		isLoading: isLoadingPayouts,
		error: payoutsError,
		currentPage,
		totalPages,
		loadPayouts,
		changePage,
		clearError: clearPayoutsError,
	} = usePayoutList();

	// Start polling when payouts are loaded
	useEffect(() => {
		if (payouts && payouts.length > 0 && !isPolling) {
			startPolling(payouts);
		}
	}, [payouts, isPolling, startPolling]);

	// Update polling service when payouts change
	useEffect(() => {
		if (payouts && payouts.length > 0) {
			updatePayouts(payouts);
		}
	}, [payouts, updatePayouts]);

	// Handle real-time payout updates from polling
	useEffect(() => {
		const unsubscribe = onPayoutUpdate(() => {
			// Simply reload the current page when polling detects changes
			// The polling service now fetches the correct page, so we can trust the results
			loadPayouts(currentPage);
		});

		return unsubscribe;
	}, [onPayoutUpdate, loadPayouts, currentPage]);

	// Cleanup polling on unmount
	useEffect(() => {
		return () => {
			stopPolling();
		};
	}, [stopPolling]);

	// Load payouts when user is available
	useEffect(() => {
		if (user) {
			loadPayouts();
		}
	}, [user, loadPayouts]);

	const handleCreatePayout = useCallback(
		async (payoutData: CreatePayoutRequest) => {
			try {
				await payoutService.createPayout(payoutData);
				await loadPayouts();
			} catch (error) {
				handleError(error as Error, "payout-creation");
			}
		},
		[loadPayouts, handleError]
	);

	const handleLogout = useCallback(async () => {
		try {
			await logout();
			navigate("/login");
		} catch (error) {
			handleError(error as Error, "logout");
		}
	}, [logout, navigate, handleError]);

	const handlePageChange = useCallback(
		(page: number) => {
			changePage(page);
			loadPayouts(page);
			updateCurrentPage(page, 10);
		},
		[changePage, loadPayouts, updateCurrentPage]
	);

	const handlePayoutErrorChange = useCallback(
		(error: string | null) => {
			if (error) {
				handleError(error, "payout-list");
			} else {
				clearPayoutsError();
			}
		},
		[handleError, clearPayoutsError]
	);

	if (authLoading) {
		return (
			<Box
				display='flex'
				justifyContent='center'
				alignItems='center'
				minHeight='100vh'
				aria-label='Loading dashboard'
			>
				<CircularProgress size={40} />
			</Box>
		);
	}

	if (!user) {
		return null; // This should not happen due to ProtectedRoute
	}

	return (
		<div className={styles.dashboardRoot}>
			<div className={styles.dashboardContainer}>
				{/* Global Error Display */}
				{hasError && (
					<Alert
						severity='error'
						sx={{ mb: 2 }}
						onClose={clearError}
						role='alert'
						aria-live='polite'
					>
						{error?.error}
					</Alert>
				)}

				{/* Polling Status Alerts */}
				{!isPolling && payouts && payouts.length > 0 && (
					<Alert severity='info' sx={{ mb: 2, maxWidth: "400px" }}>
						Live updates paused. Status changes will appear on next refresh.
					</Alert>
				)}
				{pollingError && (
					<Alert severity='warning' sx={{ mb: 2, maxWidth: "400px" }}>
						Update error: {typeof pollingError === 'string' ? pollingError : String(pollingError)}
					</Alert>
				)}

				{/* User Profile Header */}
				<UserProfile
					user={user}
					onLogout={handleLogout}
					isLoading={authLoading}
				/>

				{/* Polling Indicator */}
				{/* PollingIndicator will be injected into PayoutList header */}
				{(() => {
					(window as any).pollingIndicator = (
						<PollingIndicator
							isPolling={isPolling}
							lastUpdate={lastUpdate}
							error={pollingError}
							pollCount={pollCount}
						/>
					);
					return null;
				})()}

				{/* Payout Form */}
				<PayoutForm
					onSubmit={handleCreatePayout}
					isLoading={authLoading}
					error={hasError ? error?.error : null}
					onErrorChange={(error) => handleError(error ?? "", "payout-form")}
				/>

				{/* Payout List */}
				<PayoutList
					payouts={payouts}
					isLoading={isLoadingPayouts}
					error={payoutsError}
					currentPage={currentPage}
					totalPages={totalPages}
					onPageChange={handlePageChange}
					onErrorChange={handlePayoutErrorChange}
				/>
			</div>
		</div>
	);
});

DashboardPage.displayName = "DashboardPage";

export default DashboardPage;
