import { useState, useCallback, useMemo } from 'react';
import { payoutService } from '../apiClient/services/payoutService';
import type { PayoutFormState, CreatePayoutRequest, Currency, ValidationResult } from '../types';

const initialFormState: PayoutFormState = {
  amount: 0,
  currency: 'ZAR',
  isSubmitting: false,
  error: null,
};

export const usePayoutForm = () => {
  const [formState, setFormState] = useState<PayoutFormState>(initialFormState);

  const validateForm = useCallback((amount: number, currency: Currency): ValidationResult => {
    return payoutService.validatePayoutData(amount, currency);
  }, []);

  const updateAmount = useCallback((amount: number) => {
    setFormState((prev) => {
      const newState = { ...prev, amount };
      
      // Real-time validation
      const validation = validateForm(amount, prev.currency);
      if (!validation.isValid) {
        newState.error = validation.error || 'Invalid amount';
      } else {
        newState.error = null;
      }

      return newState;
    });
  }, [validateForm]);

  const updateCurrency = useCallback((currency: Currency) => {
    setFormState((prev) => {
      const newState = { ...prev, currency };
      
      // Real-time validation
      const validation = validateForm(prev.amount, currency);
      if (!validation.isValid) {
        newState.error = validation.error || 'Invalid currency';
      } else {
        newState.error = null;
      }

      return newState;
    });
  }, [validateForm]);

  const setSubmitting = useCallback((isSubmitting: boolean) => {
    setFormState((prev) => ({ ...prev, isSubmitting }));
  }, []);

  const setError = useCallback((error: string | null) => {
    setFormState((prev) => ({ ...prev, error }));
  }, []);

  const resetForm = useCallback(() => {
    setFormState(initialFormState);
  }, []);

  const isFormValid = useMemo(() => {
    const validation = validateForm(formState.amount, formState.currency);
    return validation.isValid && formState.amount > 0;
  }, [formState.amount, formState.currency, validateForm]);

  const canSubmit = useMemo(() => {
    return isFormValid && !formState.isSubmitting;
  }, [isFormValid, formState.isSubmitting]);


  const handleSubmit = useCallback(
    (onSubmit: (data: CreatePayoutRequest) => Promise<void>) =>
      async (e?: React.FormEvent) => {
        if (e && typeof e.preventDefault === 'function') e.preventDefault();
        if (!canSubmit) return;

        const validation = validateForm(formState.amount, formState.currency);
        if (!validation.isValid) {
          setError(validation.error || 'Invalid payout data');
          return;
        }

        setSubmitting(true);
        setError(null);

        try {
          const idempotencyKey = payoutService.generateIdempotencyKey();
          const payoutData: CreatePayoutRequest = {
            amount: formState.amount,
            currency: formState.currency,
            idempotency_key: idempotencyKey,
          };

          await onSubmit(payoutData);
          resetForm();
        } catch (error) {
          let errorMessage = 'Failed to create payout';

          if (error instanceof Error) {
            if (error.message.includes('rate_limit') || error.message.includes('429')) {
              errorMessage = 'Too many requests. Please wait a moment before trying again.';
            } else if (error.message.includes('validation') || error.message.includes('400')) {
              errorMessage = 'Please check your input and try again.';
            } else if (error.message.includes('unauthorized') || error.message.includes('401')) {
              errorMessage = 'Please log in again to continue.';
            } else {
              errorMessage = error.message;
            }
          }

          setError(errorMessage);
        } finally {
          setSubmitting(false);
        }
      },
    [formState.amount, formState.currency, canSubmit, validateForm, setSubmitting, setError, resetForm]
  );

  return {
    formState,
    updateAmount,
    updateCurrency,
    setError,
    resetForm,
    isFormValid,
    canSubmit,
    handleSubmit,
  };
};
