import React, { memo, useCallback } from 'react';
import {
  Typography,
  Box,
  Button,
  TextField,
  MenuItem,
  Alert,
  CircularProgress,
} from '@mui/material';
import { usePayoutForm } from '../../hooks/usePayoutForm';
import { payoutCurrencies } from '../../utils/payoutUtils';
import type { PayoutFormProps } from '../../types';
import styles from './PayoutForm.module.css';

const PayoutForm = memo<PayoutFormProps>(({ 
  onSubmit, 
  isLoading = false, 
  error, 
  onErrorChange 
}) => {
  const {
    formState,
    updateAmount,
    updateCurrency,
    setError,
    canSubmit,
    handleSubmit,
  } = usePayoutForm();

  const handleAmountChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const rawValue = e.target.value.replace(',', '.');
    const newAmount = Number(rawValue);

    if (!isNaN(newAmount)) {
      updateAmount(newAmount);
    }
  }, [updateAmount]);

  const handleCurrencyChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    updateCurrency(e.target.value as any);
  }, [updateCurrency]);

  const handleFormSubmit = handleSubmit(onSubmit);

  const handleErrorClose = useCallback(() => {
    setError(null);
    onErrorChange?.(null);
  }, [setError, onErrorChange]);

  const displayError = error || formState.error;

  return (
    <div className={styles.payoutForm}>
      <Typography variant="h6" fontWeight={600} gutterBottom>
        Create a Payout
      </Typography>

      {displayError && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          onClose={handleErrorClose}
          role="alert"
          aria-live="polite"
        >
          {displayError}
        </Alert>
      )}

      <Box
        component="form"
        display="flex"
        gap={2}
        onSubmit={handleFormSubmit}
        aria-label="Payout creation form"
      >
        <TextField
          label="Amount"
          type="number"
          fullWidth
          size="small"
          value={formState.amount}
          onChange={handleAmountChange}
          inputProps={{
            min: 0.01,
            max: 1000000,
            step: 0.01,
            disabled: formState.isSubmitting || isLoading,
            'aria-describedby': displayError ? 'payout-error' : undefined,
          }}
          disabled={formState.isSubmitting || isLoading}
          helperText="Maximum amount: 1,000,000 (2 decimal places)"
          error={!!displayError}
          aria-required="true"
        />
        <TextField
          label="Currency"
          select
          fullWidth
          size="small"
          value={formState.currency}
          onChange={handleCurrencyChange}
          disabled={formState.isSubmitting || isLoading}
          aria-required="true"
        >
          {payoutCurrencies.map((currency) => (
            <MenuItem key={currency.code} value={currency.code}>
              {currency.label}
            </MenuItem>
          ))}
        </TextField>
        <Button
          variant="contained"
          color="primary"
          size="large"
          sx={{ minWidth: 140 }}
          type="submit"
          disabled={!canSubmit || isLoading}
          aria-label="Submit payout request"
        >
          {formState.isSubmitting || isLoading ? (
            <CircularProgress size={20} />
          ) : (
            'Send Payout'
          )}
        </Button>
      </Box>
    </div>
  );
});

PayoutForm.displayName = 'PayoutForm';

export default PayoutForm;
