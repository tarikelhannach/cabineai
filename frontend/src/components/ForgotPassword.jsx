import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  InputAdornment,
  Link,
} from '@mui/material';
import { Email, ArrowBack } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { authAPI } from '../services/api';
import LanguageSelector from './LanguageSelector';

const ForgotPassword = () => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);
  const [resetToken, setResetToken] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    
    if (!email) {
      setError(t('auth.emailRequired'));
      return;
    }

    setLoading(true);
    setError('');

    try {
      const response = await authAPI.requestPasswordReset(email);
      setSuccess(true);
      if (response.token) {
        setResetToken(response.token);
      }
    } catch (error) {
      setError(error.response?.data?.detail || t('errors.generic'));
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <Box
        sx={{
          minHeight: '100vh',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
          p: 2,
          position: 'relative',
        }}
      >
        <Box
          sx={{
            position: 'absolute',
            top: 16,
            right: 16,
            zIndex: 1000,
          }}
        >
          <LanguageSelector />
        </Box>

        <Card sx={{ maxWidth: 500, width: '100%' }}>
          <CardContent sx={{ p: 4 }}>
            <Typography variant="h5" gutterBottom align="center" color="primary">
              {t('auth.checkEmail')}
            </Typography>
            
            <Alert severity="success" sx={{ mt: 2 }}>
              {t('auth.resetEmailSent')}
            </Alert>

            {resetToken && (
              <Alert severity="info" sx={{ mt: 2 }}>
                <Typography variant="body2" gutterBottom>
                  <strong>{t('auth.resetToken')}:</strong>
                </Typography>
                <Typography 
                  variant="body2" 
                  sx={{ 
                    fontFamily: 'monospace', 
                    wordBreak: 'break-all',
                    fontSize: '0.85rem'
                  }}
                >
                  {resetToken}
                </Typography>
                <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                  {t('auth.resetTokenNote')}
                </Typography>
              </Alert>
            )}

            <Button
              fullWidth
              variant="contained"
              onClick={() => navigate('/reset-password')}
              sx={{ mt: 3 }}
            >
              {t('auth.continueReset')}
            </Button>

            <Box sx={{ mt: 2, textAlign: 'center' }}>
              <Link
                component="button"
                variant="body2"
                onClick={() => navigate('/login')}
                sx={{ cursor: 'pointer' }}
              >
                {t('auth.backToLogin')}
              </Link>
            </Box>
          </CardContent>
        </Card>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
        p: 2,
        position: 'relative',
      }}
    >
      <Box
        sx={{
          position: 'absolute',
          top: 16,
          right: 16,
          zIndex: 1000,
        }}
      >
        <LanguageSelector />
      </Box>

      <Card sx={{ maxWidth: 500, width: '100%' }}>
        <CardContent sx={{ p: 4 }}>
          <Typography variant="h4" gutterBottom align="center">
            {t('auth.forgotPassword')}
          </Typography>
          <Typography variant="body2" color="textSecondary" align="center" sx={{ mb: 3 }}>
            {t('auth.forgotPasswordHelp')}
          </Typography>

          <form onSubmit={handleSubmit}>
            <TextField
              fullWidth
              label={t('auth.email')}
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              margin="normal"
              required
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <Email />
                  </InputAdornment>
                ),
              }}
            />

            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {error}
              </Alert>
            )}

            <Button
              fullWidth
              variant="contained"
              size="large"
              type="submit"
              disabled={loading}
              sx={{ mt: 3 }}
            >
              {loading ? t('common.loading') : t('auth.sendResetLink')}
            </Button>

            <Box sx={{ mt: 2, textAlign: 'center' }}>
              <Link
                component="button"
                variant="body2"
                onClick={() => navigate('/login')}
                sx={{ 
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 0.5
                }}
              >
                <ArrowBack fontSize="small" />
                {t('auth.backToLogin')}
              </Link>
            </Box>
          </form>
        </CardContent>
      </Card>
    </Box>
  );
};

export default ForgotPassword;
