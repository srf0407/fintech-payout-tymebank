import React from 'react';
import { Typography, Box, Button, TextField, MenuItem, Divider, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, Paper, Chip } from '@mui/material';
import styles from './DashboardPage.module.css';
import { useAuth } from '../auth/AuthContext';

const payoutCurrencies = [
  { code: 'USD', label: 'US Dollar' },
  { code: 'ZAR', label: 'South African Rand' },
  { code: 'EUR', label: 'Euro' },
];

const mockPayouts = [
  { id: 1, amount: 100, currency: 'USD', status: 'Completed', created: '2025-09-10 10:00' },
  { id: 2, amount: 250, currency: 'ZAR', status: 'Pending', created: '2025-09-10 09:30' },
  { id: 3, amount: 75, currency: 'EUR', status: 'Failed', created: '2025-09-09 16:20' },
];

const statusColor = (status: string) => {
  switch (status) {
    case 'Completed': return 'success';
    case 'Pending': return 'warning';
    case 'Failed': return 'error';
    default: return 'default';
  }
};

const DashboardPage: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <div className={styles.dashboardRoot}>
      <div className={styles.dashboardContainer}>
        {/* Header: User Profile */}
        <div className={styles.dashboardHeader}>
          <img src={user?.picture} alt={user?.name} className={styles.profilePic} />
          <div className={styles.profileInfo}>
            <Typography variant="h5" fontWeight={700}>{user?.name}</Typography>
            <Typography variant="body2" color="text.secondary">{user?.email}</Typography>
          </div>
          <Button variant="outlined" color="primary" onClick={logout}>
            Log out
          </Button>
        </div>

        {/* Payout Form */}
        <div className={styles.payoutSection}>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            Create a Payout
          </Typography>
          <Box display="flex" gap={2}>
            <TextField label="Amount" type="number" fullWidth size="small" inputProps={{ min: 1 }} />
            <TextField label="Currency" select fullWidth size="small" defaultValue={payoutCurrencies[0].code}>
              {payoutCurrencies.map((c) => (
                <MenuItem key={c.code} value={c.code}>{c.label}</MenuItem>
              ))}
            </TextField>
            <Button variant="contained" color="primary" size="large" sx={{ minWidth: 140 }}>
              Send Payout
            </Button>
          </Box>
        </div>

        {/* Payout List */}
        <div className={styles.payoutListSection}>
          <Typography variant="h6" fontWeight={600} gutterBottom>
            Recent Payouts
          </Typography>
          <Divider sx={{ mb: 2 }} />
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
                {mockPayouts.map((payout) => (
                  <TableRow key={payout.id}>
                    <TableCell>{payout.created}</TableCell>
                    <TableCell>{payout.amount}</TableCell>
                    <TableCell>{payout.currency}</TableCell>
                    <TableCell>
                      <Chip label={payout.status} color={statusColor(payout.status)} size="small" />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        </div>
      </div>
    </div>
  );
};

export default DashboardPage;
