// frontend/src/components/Login.js - Componente de Login con 2FA

import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  TextField,
  Button,
  Typography,
  Alert,
  Stepper,
  Step,
  StepLabel,
  Paper,
  Divider,
  InputAdornment,
  IconButton,
  Link,
  CircularProgress
} from '@mui/material';
import {
  Visibility,
  VisibilityOff,
  Security,
  QrCode,
  Email,
} from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import LanguageSelector from './LanguageSelector';

const Login = () => {
  const { login } = useAuth();
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [step, setStep] = useState(0);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    twoFactorCode: '',
  });
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const steps = [
    t('auth.email'),
    t('auth.2faCode'),
  ];

  const handleInputChange = (field) => (event) => {
    setFormData({
      ...formData,
      [field]: event.target.value,
    });
    setError('');
  };

  const handleLogin = async () => {
    if (!formData.email || !formData.password) {
      setError(t('auth.emailRequired'));
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await login(formData.email, formData.password);

      if (result.success) {
        // Login exitoso
        return;
      } else if (result.requires2FA || result.error?.includes('2FA')) {
        // Requiere 2FA
        setStep(1);
        if (result.error && !result.error.includes('2FA')) {
          setError(result.error);
        }
      } else {
        setError(result.error);
      }
    } catch (error) {
      setError('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const handle2FA = async () => {
    if (!formData.twoFactorCode) {
      setError(t('auth.2faHelper'));
      return;
    }

    setLoading(true);
    setError('');

    try {
      const result = await login(
        formData.email,
        formData.password,
        formData.twoFactorCode
      );

      if (!result.success) {
        setError(result.error);
      }
    } catch (error) {
      setError('Error de conexión');
    } finally {
      setLoading(false);
    }
  };

  const handleBack = () => {
    setStep(0);
    setFormData({
      ...formData,
      twoFactorCode: '',
    });
    setError('');
  };

  const renderStepContent = () => {
    switch (step) {
      case 0:
        return (
          <Box>
            <Typography variant="h4" gutterBottom align="center">
              🏛️ {t('dashboard.subtitle').replace(' 🇲🇦', '')}
            </Typography>
            <Typography variant="h6" gutterBottom align="center" color="textSecondary">
              🇲🇦 Reino de Marruecos
            </Typography>

            <Box sx={{ mt: 3 }}>
              <TextField
                fullWidth
                label={t('auth.email')}
                type="email"
                value={formData.email}
                onChange={handleInputChange('email')}
                margin="normal"
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Email />
                    </InputAdornment>
                  ),
                }}
              />

              <TextField
                fullWidth
                label={t('auth.password')}
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={handleInputChange('password')}
                margin="normal"
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Security />
                    </InputAdornment>
                  ),
                  endAdornment: (
                    <InputAdornment position="end">
                      <IconButton
                        onClick={() => setShowPassword(!showPassword)}
                        edge="end"
                      >
                        {showPassword ? <VisibilityOff /> : <Visibility />}
                      </IconButton>
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
                onClick={handleLogin}
                disabled={loading}
                sx={{
                  mt: 3,
                  py: 1.5,
                  fontWeight: 600,
                  '&.Mui-disabled': {
                    backgroundColor: 'rgba(0, 0, 0, 0.12)',
                    color: 'rgba(0, 0, 0, 0.7)'
                  }
                }}
              >
                {loading ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CircularProgress size={20} color="inherit" />
                    {t('common.loading')}
                  </Box>
                ) : t('auth.loginButton')}
              </Button>
            </Box>
          </Box>
        );

      case 1:
        return (
          <Box>
            <Typography variant="h5" gutterBottom align="center">
              {t('auth.2faCode')}
            </Typography>

            <Paper sx={{ p: 2, mt: 2, mb: 2 }}>
              <Typography variant="body2" color="textSecondary">
                {t('auth.2faHelper')}
              </Typography>
            </Paper>

            <TextField
              fullWidth
              label={t('auth.2faCode')}
              value={formData.twoFactorCode}
              onChange={handleInputChange('twoFactorCode')}
              margin="normal"
              placeholder="123456"
              inputProps={{ maxLength: 6 }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <QrCode />
                  </InputAdornment>
                ),
              }}
            />

            <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
              <Button
                variant="outlined"
                onClick={handleBack}
                disabled={loading}
                sx={{ flex: 1 }}
              >
                {t('common.cancel')}
              </Button>
              <Button
                variant="contained"
                onClick={handle2FA}
                disabled={loading || !formData.twoFactorCode}
                sx={{
                  flex: 1,
                  '&.Mui-disabled': {
                    backgroundColor: 'rgba(0, 0, 0, 0.12)',
                    color: 'rgba(0, 0, 0, 0.7)'
                  }
                }}
              >
                {loading ? (
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <CircularProgress size={20} color="inherit" />
                    {t('common.loading')}
                  </Box>
                ) : t('auth.loginButton')}
              </Button>
            </Box>

            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {error}
              </Alert>
            )}
          </Box>
        );

      default:
        return null;
    }
  };

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
      {/* Selector de idioma en la esquina superior derecha */}
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
          <Stepper activeStep={step} sx={{ mb: 3 }}>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>

          <Divider sx={{ mb: 3 }} />

          {renderStepContent()}

          <Box sx={{ mt: 4, textAlign: 'center' }}>
            <Link
              component="button"
              variant="body2"
              onClick={() => navigate('/forgot-password')}
              sx={{ cursor: 'pointer' }}
            >
              {t('auth.forgotPassword')}
            </Link>
          </Box>
        </CardContent>
      </Card>
    </Box>
  );
};

export default Login;
