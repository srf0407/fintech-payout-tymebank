import { useState, useCallback, useEffect } from 'react';
import { payoutService } from '../apiClient/services/payoutService';
import type { PayoutListState, Payout } from '../types';

const initialListState: PayoutListState = {
  payouts: [],
  isLoading: false,
  error: null,
  currentPage: 1,
  totalPages: 1,
};

export const usePayoutList = () => {
  const [listState, setListState] = useState<PayoutListState>(initialListState);

  const loadPayouts = useCallback(async (page: number = listState.currentPage, perPage: number = 10) => {
    setListState((prev) => ({
      ...prev,
      isLoading: true,
      error: null,
    }));

    try {
      const response = await payoutService.getPayouts(page, perPage);
      setListState((prev) => ({
        ...prev,
        payouts: response.items,
        totalPages: Math.ceil(response.total / perPage),
        currentPage: page,
        isLoading: false,
      }));
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load payouts';
      setListState((prev) => ({
        ...prev,
        error: errorMessage,
        isLoading: false,
      }));
    }
  }, [listState.currentPage]);

  const refreshPayouts = useCallback(() => {
    loadPayouts(listState.currentPage);
  }, [loadPayouts, listState.currentPage]);

  const changePage = useCallback((page: number) => {
    setListState((prev) => ({ ...prev, currentPage: page }));
  }, []);

  const updatePayouts = useCallback((payouts: Payout[]) => {
    setListState((prev) => {
      const perPage = 10;
      const totalPages = Math.max(1, Math.ceil(payouts.length / perPage));
      let currentPage = prev.currentPage;
      if (currentPage > totalPages) {
        currentPage = totalPages;
      }
      return {
        ...prev,
        payouts,
        totalPages,
        currentPage,
      };
    });
  }, []);

  const clearError = useCallback(() => {
    setListState((prev) => ({ ...prev, error: null }));
  }, []);

  // Load payouts when page changes
  useEffect(() => {
    loadPayouts(listState.currentPage);
  }, [listState.currentPage, loadPayouts]);

  return {
    ...listState,
    loadPayouts,
    refreshPayouts,
    changePage,
    updatePayouts,
    clearError,
  };
};
