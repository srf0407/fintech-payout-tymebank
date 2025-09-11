import React, { useState, useEffect, useCallback } from "react";
import {
	Typography,
	Box,
	Button,
	TextField,
	MenuItem,
	Divider,
	Table,
	TableBody,
	TableCell,
	TableContainer,
	TableHead,
	TableRow,
	Paper,
	Chip,
	Alert,
	CircularProgress,
	Pagination,
	IconButton,
	Tooltip,
} from "@mui/material";
import { Wifi, WifiOff, Sync, SyncProblem } from "@mui/icons-material";
import { useNavigate } from "react-router-dom";
import styles from "./DashboardPage.module.css";
import { useAuth } from "../auth/AuthContext";
import {
	payoutService,
	type Payout,
} from "../apiClient/services/payoutService";
import { usePolling } from "../hooks/usePolling";
import {
	statusColor,
	formatDate,
	payoutCurrencies,
} from "../utils/payoutUtils";

type PayoutFormState = {
	amount: number;
	currency: string;
	isSubmitting: boolean;
	payoutError: string | null;
};

type PayoutListState = {
	payouts: Payout[];
	isLoadingPayouts: boolean;
	payoutsError: string | null;
	currentPage: number;
	totalPages: number;
};

const DashboardPage: React.FC = () => {
	const { user, logout, isLoading: authLoading } = useAuth();
	const navigate = useNavigate();
	const {
		isPolling,
		lastUpdate,
		error: pollingError,
		pollCount,
		startPolling,
		stopPolling,
		updatePayouts,
		onPayoutUpdate,
	} = usePolling();

	const [formState, setFormState] = useState<PayoutFormState>({
		amount: 0,
		currency: "ZAR",
		isSubmitting: false,
		payoutError: null,
	});

	const [listState, setListState] = useState<PayoutListState>({
		payouts: [],
		isLoadingPayouts: false,
		payoutsError: null,
		currentPage: 1,
		totalPages: 1,
	});

	// Load payouts when component mounts or page changes
	const loadPayouts = useCallback(async () => {
		setListState((prev) => ({
			...prev,
			isLoadingPayouts: true,
			payoutsError: null,
		}));
		try {
			const response = await payoutService.getPayouts(
				listState.currentPage,
				10
			);
			setListState((prev) => ({
				...prev,
				payouts: response.items,
				totalPages: Math.ceil(response.total / 10), // Calculate total pages from total and page_size
				isLoadingPayouts: false,
			}));
		} catch (error) {
			const errorMessage =
				error instanceof Error ? error.message : "Failed to load payouts";
			setListState((prev) => ({
				...prev,
				payoutsError: errorMessage,
				isLoadingPayouts: false,
			}));
		}
	}, [listState.currentPage]);

	// Start polling when payouts are loaded
	useEffect(() => {
		if (listState.payouts && listState.payouts.length > 0 && !isPolling) {
			startPolling(listState.payouts);
		}
	}, [listState.payouts, isPolling, startPolling]);

	// Update polling service when payouts change
	useEffect(() => {
		if (listState.payouts && listState.payouts.length > 0) {
			updatePayouts(listState.payouts);
		}
	}, [listState.payouts, updatePayouts]);

	// Handle real-time payout updates from polling
	useEffect(() => {
		const unsubscribe = onPayoutUpdate((updatedPayouts: Payout[]) => {
			if (updatedPayouts && Array.isArray(updatedPayouts)) {
				setListState((prev) => ({
					...prev,
					payouts: updatedPayouts,
				}));
			}
		});

		return unsubscribe;
	}, [onPayoutUpdate]);

	// Cleanup polling on unmount
	useEffect(() => {
		return () => {
			stopPolling();
		};
	}, [stopPolling]);

	useEffect(() => {
		if (user) {
			loadPayouts();
		}
	}, [user, loadPayouts]);

	const validateForm = (
		amount: number,
		currency: string
	): { isValid: boolean; error?: string } => {
		const validation = payoutService.validatePayoutData(amount, currency);
		return validation;
	};

	const handleCreatePayout = async (e: React.FormEvent) => {
		e.preventDefault();

		const validation = validateForm(formState.amount, formState.currency);
		if (!validation.isValid) {
			setFormState((prev) => ({
				...prev,
				payoutError: validation.error || "Invalid payout data",
			}));
			return;
		}

		setFormState((prev) => ({
			...prev,
			isSubmitting: true,
			payoutError: null,
		}));

		try {
			const idempotencyKey = payoutService.generateIdempotencyKey();
			await payoutService.createPayout({
				amount: formState.amount,
				currency: formState.currency,
				idempotency_key: idempotencyKey,
			});

			setFormState({
				amount: 0,
				currency: "ZAR",
				isSubmitting: false,
				payoutError: null,
			});

			await loadPayouts();
		} catch (error) {
			let errorMessage = "Failed to create payout";

			if (error instanceof Error) {
				// Enhanced error handling for different error types
				if (
					error.message.includes("rate_limit") ||
					error.message.includes("429")
				) {
					errorMessage =
						"Too many requests. Please wait a moment before trying again.";
				} else if (
					error.message.includes("validation") ||
					error.message.includes("400")
				) {
					errorMessage = "Please check your input and try again.";
				} else if (
					error.message.includes("unauthorized") ||
					error.message.includes("401")
				) {
					errorMessage = "Please log in again to continue.";
				} else {
					errorMessage = error.message;
				}
			}

			setFormState((prev) => ({
				...prev,
				payoutError: errorMessage,
				isSubmitting: false,
			}));
		}
	};

	const handleLogout = async () => {
		await logout();
		navigate("/login");
	};

	const handlePageChange = (_: React.ChangeEvent<unknown>, page: number) => {
		setListState((prev) => ({ ...prev, currentPage: page }));
	};

	const getPollingIcon = () => {
		if (isPolling) {
			return <Sync className='animate-spin' color='success' />;
		} else if (pollingError) {
			return <SyncProblem color='error' />;
		} else {
			return <WifiOff color='disabled' />;
		}
	};

	const getPollingTooltip = () => {
		if (isPolling) {
			const lastUpdateText = lastUpdate
				? `Last update: ${lastUpdate.toLocaleTimeString()}`
				: "No updates yet";
			return `Polling active (${pollCount} checks) - ${lastUpdateText}`;
		} else if (pollingError) {
			return `Polling error: ${pollingError}`;
		} else {
			return "Polling stopped";
		}
	};

	if (authLoading) {
		return (
			<Box
				display='flex'
				justifyContent='center'
				alignItems='center'
				minHeight='100vh'
			>
				<CircularProgress size={40} />
			</Box>
		);
	}

	return (
		<div className={styles.dashboardRoot}>
			<div className={styles.dashboardContainer}>
				{/* Header: User Profile */}
				<div className={styles.dashboardHeader}>
					<img
						src={
							user?.picture_url
								? user.picture_url
								: "../../assets/default-avatar.jpg"
						}
						alt={user?.name || "User"}
						className={styles.profilePic}
					/>
					<div className={styles.profileInfo}>
						<Typography variant='h5' fontWeight={700}>
							{user?.name || "User"}
						</Typography>
						<Typography variant='body2' color='text.secondary'>
							{user?.email}
						</Typography>
					</div>
					<div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
						<Tooltip title={getPollingTooltip()}>
							<IconButton size='small'>{getPollingIcon()}</IconButton>
						</Tooltip>
						<Button
							variant='outlined'
							color='primary'
							onClick={handleLogout}
							disabled={authLoading}
						>
							Log out
						</Button>
					</div>
				</div>
				{/* Payout Form (UI only, no integration) */}
				<div className={styles.payoutSection}>
					<Typography variant='h6' fontWeight={600} gutterBottom>
						Create a Payout
					</Typography>

					{formState.payoutError && (
						<Alert
							severity='error'
							sx={{ mb: 2 }}
							onClose={() =>
								setFormState((prev) => ({ ...prev, payoutError: null }))
							}
						>
							{formState.payoutError}
						</Alert>
					)}

					<Box
						component='form'
						display='flex'
						gap={2}
						onSubmit={handleCreatePayout}
					>
						<TextField
							label='Amount'
							type='number'
							fullWidth
							size='small'
							value={formState.amount}
							onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
								const rawValue = e.target.value.replace(",", ".");
								const newAmount = Number(rawValue);

								if (!isNaN(newAmount)) {
									setFormState((prev: PayoutFormState) => {
										const newState = {
											...prev,
											amount: newAmount,
										};

										const validation = validateForm(newAmount, prev.currency);
										if (!validation.isValid) {
											newState.payoutError =
												validation.error || "Invalid amount";
										} else {
											newState.payoutError = null;
										}

										return newState;
									});
								}
							}}
							inputProps={{
								min: 0.01,
								max: 1000000,
								step: 0.01,
								disabled: formState.isSubmitting,
							}}
							disabled={formState.isSubmitting}
							helperText='Maximum amount: 1,000,000 (2 decimal places)'
						/>
						<TextField
							label='Currency'
							select
							fullWidth
							size='small'
							value={formState.currency}
							onChange={(e: React.ChangeEvent<HTMLInputElement>) => {
								const newCurrency = e.target.value;
								setFormState((prev: PayoutFormState) => {
									const newState = {
										...prev,
										currency: newCurrency,
									};

									// Real-time validation
									const validation = validateForm(prev.amount, newCurrency);
									if (!validation.isValid) {
										newState.payoutError =
											validation.error || "Invalid currency";
									} else {
										newState.payoutError = null;
									}

									return newState;
								});
							}}
							disabled={formState.isSubmitting}
						>
							{payoutCurrencies.map((c) => (
								<MenuItem key={c.code} value={c.code}>
									{c.label}
								</MenuItem>
							))}
						</TextField>
						<Button
							variant='contained'
							color='primary'
							size='large'
							sx={{ minWidth: 140 }}
							type='submit'
							disabled={formState.amount <= 0 || formState.isSubmitting}
						>
							{formState.isSubmitting ? (
								<CircularProgress size={20} />
							) : (
								"Send Payout"
							)}
						</Button>
					</Box>
				</div>
				{/* Payout List */}
				<div className={styles.payoutListSection}>
					<div
						style={{
							display: "flex",
							justifyContent: "space-between",
							alignItems: "center",
							marginBottom: "16px",
						}}
					>
						<Typography variant='h6' fontWeight={600}>
							Recent Payouts
						</Typography>
						{!isPolling &&
							listState.payouts &&
							listState.payouts.length > 0 && (
								<Alert severity='info' sx={{ maxWidth: "400px" }}>
									Live updates paused. Status changes will appear on next
									refresh.
								</Alert>
							)}
						{pollingError && (
							<Alert severity='warning' sx={{ maxWidth: "400px" }}>
								Update error: {pollingError}
							</Alert>
						)}
					</div>
					<Divider sx={{ mb: 2 }} />

					{listState.payoutsError && (
						<Alert
							severity='error'
							sx={{ mb: 2 }}
							onClose={() =>
								setListState((prev) => ({ ...prev, payoutsError: null }))
							}
						>
							{listState.payoutsError}
						</Alert>
					)}

					{listState.isLoadingPayouts ? (
						<Box display='flex' justifyContent='center' py={4}>
							<CircularProgress />
						</Box>
					) : (
						<>
							<TableContainer component={Paper}>
								<Table>
									<TableHead>
										<TableRow>
											<TableCell>Date</TableCell>
											<TableCell>Amount</TableCell>
											<TableCell>Currency</TableCell>
											<TableCell>Status</TableCell>
										</TableRow>
									</TableHead>
									<TableBody>
										{!listState.payouts || listState.payouts.length === 0 ? (
											<TableRow>
												<TableCell colSpan={4} align='center'>
													<Typography variant='body2' color='text.secondary'>
														No payouts found
													</Typography>
												</TableCell>
											</TableRow>
										) : (
											listState.payouts.map((payout) => (
												<TableRow key={payout.id}>
													<TableCell>{formatDate(payout.created_at)}</TableCell>
													<TableCell>
														{Number(payout.amount).toFixed(2)}
													</TableCell>
													<TableCell>{payout.currency}</TableCell>
													<TableCell>
														<Chip
															label={
																payout.status.charAt(0).toUpperCase() +
																payout.status.slice(1)
															}
															color={statusColor(payout.status)}
															size='small'
														/>
													</TableCell>
												</TableRow>
											))
										)}
									</TableBody>
								</Table>
							</TableContainer>

							{listState.totalPages > 1 && (
								<Box display='flex' justifyContent='center' mt={2}>
									<Pagination
										count={listState.totalPages}
										page={listState.currentPage}
										onChange={handlePageChange}
										color='primary'
									/>
								</Box>
							)}
						</>
					)}
				</div>
			</div>
		</div>
	);
};

export default DashboardPage;
