import React, { memo, useCallback, useMemo } from 'react';
import {
  Typography,
  Box,
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
} from '@mui/material';
import { statusColor, formatDate } from '../../utils/payoutUtils';
import type { PayoutListProps, Payout, StatusColor } from '../../types';
import styles from './PayoutList.module.css';

const PayoutRow = memo<{ payout: Payout }>(({ payout }) => {
  const chipColor = useMemo(() => statusColor(payout.status), [payout.status]);
  
  const statusLabel = useMemo(() => 
    payout.status.charAt(0).toUpperCase() + payout.status.slice(1),
    [payout.status]
  );

  return (
    <TableRow key={payout.id}>
      <TableCell>{formatDate(payout.created_at)}</TableCell>
      <TableCell>
        {Number(payout.amount).toFixed(2)}
      </TableCell>
      <TableCell>{payout.currency}</TableCell>
      <TableCell>
        <Chip
          label={statusLabel}
          color={chipColor as StatusColor}
          size="small"
          aria-label={`Payout status: ${statusLabel}`}
        />
      </TableCell>
    </TableRow>
  );
});

PayoutRow.displayName = 'PayoutRow';

const EmptyState = memo(() => (
  <TableRow>
    <TableCell colSpan={4} align="center">
      <Typography variant="body2" color="text.secondary">
        No payouts found
      </Typography>
    </TableCell>
  </TableRow>
));

EmptyState.displayName = 'EmptyState';

const PayoutList = memo<PayoutListProps>(({ 
  payouts, 
  isLoading = false, 
  error, 
  currentPage, 
  totalPages, 
  onPageChange, 
  onErrorChange 
}) => {
  const handlePageChange = useCallback((_: React.ChangeEvent<unknown>, page: number) => {
    onPageChange(page);
  }, [onPageChange]);

  const handleErrorClose = useCallback(() => {
    onErrorChange?.(null);
  }, [onErrorChange]);

  const hasPayouts = payouts && payouts.length > 0;

  return (
    <div className={styles.payoutList}>
      <div className={styles.header}>
        <Typography variant="h6" fontWeight={600}>
          Recent Payouts
        </Typography>
      </div>

      {error && (
        <Alert
          severity="error"
          sx={{ mb: 2 }}
          onClose={handleErrorClose}
          role="alert"
          aria-live="polite"
        >
          {error}
        </Alert>
      )}

      {isLoading ? (
        <Box display="flex" justifyContent="center" py={4}>
          <CircularProgress aria-label="Loading payouts" />
        </Box>
      ) : (
        <>
          <TableContainer component={Paper} aria-label="Payouts table">
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
                {!hasPayouts ? (
                  <EmptyState />
                ) : (
                  payouts.map((payout) => (
                    <PayoutRow key={payout.id} payout={payout} />
                  ))
                )}
              </TableBody>
            </Table>
          </TableContainer>

          {totalPages > 1 && (
            <Box display="flex" justifyContent="center" mt={2}>
              <Pagination
                count={totalPages}
                page={currentPage}
                onChange={handlePageChange}
                color="primary"
                aria-label="Payouts pagination"
              />
            </Box>
          )}
        </>
      )}
    </div>
  );
});

PayoutList.displayName = 'PayoutList';

export default PayoutList;
