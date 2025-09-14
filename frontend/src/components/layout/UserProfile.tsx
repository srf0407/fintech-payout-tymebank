import { memo } from 'react';
import {
  Typography,
  Button,
  Tooltip,
} from '@mui/material';
import { WifiOff, Sync, SyncProblem } from '@mui/icons-material';
import type { UserProfileProps, PollingIndicatorProps } from '../../types';
import styles from './UserProfile.module.css';

const PollingIndicator = memo<PollingIndicatorProps>(({ 
  isPolling, 
  lastUpdate, 
  error, 
  pollCount 
}) => {
  const getPollingIcon = () => {
    if (isPolling) {
      return <Sync className="animate-spin" color="success" />;
    } else if (error) {
      return <SyncProblem color="error" />;
    } else {
      return <WifiOff color="disabled" />;
    }
  };

  const getPollingTooltip = () => {
    if (isPolling) {
      const lastUpdateText = lastUpdate
        ? `Last update: ${lastUpdate.toLocaleTimeString()}`
        : 'No updates yet';
      return `Polling active (${pollCount} checks) - ${lastUpdateText}`;
    } else if (error) {
      return `Polling error: ${typeof error === 'string' ? error : "Unable to fetch updates"}`;
    } else {
      return 'Polling stopped';
    }
  };

  return (
    <Tooltip title={<span style={{ whiteSpace: 'pre-line', fontSize: 14 }}>{getPollingTooltip()}</span>} arrow>
      <span
        style={{
          display: 'inline-flex',
          alignItems: 'center',
          padding: '4px 8px',
          borderRadius: 16,
          background: '#f5f5f5',
          color: '#333',
          fontWeight: 500,
          fontSize: 15,
          cursor: 'default',
          userSelect: 'none',
        }}
        aria-label="Polling status info"
        tabIndex={-1}
      >
        {getPollingIcon()}
        <span style={{ marginLeft: 8 }}>
          {isPolling ? 'Polling Status: Active' : error ? 'Polling Status: Error' : 'Polling Status: Stopped'}
        </span>
      </span>
    </Tooltip>
  );
});

PollingIndicator.displayName = 'PollingIndicator';

const UserProfile = memo<UserProfileProps>(({ 
  user, 
  onLogout, 
  isLoading = false 
}) => {
  const handleLogout = async () => {
    try {
      await onLogout();
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  return (
    <div className={styles.userProfile}>
      <img
        src={
          user?.picture_url
            ? user.picture_url
            : "/assets/default-avatar.jpg"
        }
        alt={user?.name || 'User'}
        className={styles.profilePic}
      />
      <div className={styles.profileInfo}>
        <Typography variant="h5" fontWeight={700}>
          {user?.name || 'User'}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {user?.email}
        </Typography>
      </div>
      <div className={styles.actions}>
        <Button
          variant="outlined"
          color="primary"
          onClick={handleLogout}
          disabled={isLoading}
          aria-label="Log out of the application"
        >
          Log out
        </Button>
      </div>
    </div>
  );
});

UserProfile.displayName = 'UserProfile';

export default UserProfile;
export { PollingIndicator };
