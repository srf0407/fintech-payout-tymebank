

import React, { useEffect, useRef } from 'react';
import { Typography, Box, Paper, Divider } from '@mui/material';
import styles from './LoginPage.module.css';
import { useAuth } from '../auth/AuthContext';
import { useNavigate } from 'react-router-dom';

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID as string;

const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const googleBtnRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Load Google Identity Services script
    const scriptId = 'google-oauth';
    if (!document.getElementById(scriptId)) {
      const script = document.createElement('script');
      script.src = 'https://accounts.google.com/gsi/client';
      script.async = true;
      script.id = scriptId;
      document.body.appendChild(script);
      script.onload = renderGoogleBtn;
    } else {
      renderGoogleBtn();
    }
    function renderGoogleBtn() {
      if (window.google && googleBtnRef.current) {
        window.google.accounts.id.initialize({
          client_id: GOOGLE_CLIENT_ID,
          callback: handleCredentialResponse,
        });
        window.google.accounts.id.renderButton(googleBtnRef.current, {
          theme: 'outline',
          size: 'large',
          width: 320,
        });
      }
    }
    // eslint-disable-next-line
  }, []);

  function handleCredentialResponse(response: any) {
    // Decode JWT to get user info
    const base64Url = response.credential.split('.')[1];
    const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split('')
        .map(function (c) {
          return '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2);
        })
        .join('')
    );
    const profile = JSON.parse(jsonPayload);
    login({
      name: profile.name,
      email: profile.email,
      picture: profile.picture,
    });
    navigate('/dashboard');
  }

  return (
    <div className={styles.root}>
      <Paper elevation={3} className={styles.box}>
        <Box display="flex" flexDirection="column" alignItems="center" gap={2}>
          <img
            src="/fintech-logo.svg"
            alt="Fintech Payout Logo"
            width={56}
            height={56}
            style={{ marginBottom: 8 }}
            onError={e => (e.currentTarget.style.display = 'none')}
          />
          <Typography variant="h4" component="h1" gutterBottom>
            TymeBank Payouts
          </Typography>
          <Typography variant="body1" gutterBottom>
            Secure, fast, and reliable payouts for your business.
          </Typography>
          <Divider style={{ width: '100%', margin: '16px 0' }} />
          <div ref={googleBtnRef} style={{ width: '100%', display: 'flex', justifyContent: 'center' }} />
        </Box>
      </Paper>
    </div>
  );
};

export default LoginPage;
