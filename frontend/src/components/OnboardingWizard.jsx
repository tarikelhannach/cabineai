import React, { useState } from 'react';
import {
    Dialog,
    DialogContent,
    DialogActions,
    Button,
    Typography,
    Box,
    Stepper,
    Step,
    StepLabel,
    TextField,
    FormControl,
    InputLabel,
    Select,
    MenuItem,
    FormControlLabel,
    Checkbox,
    CircularProgress,
    Alert
} from '@mui/material';
import { useTranslation } from 'react-i18next';
import { useAuth } from '../context/AuthContext';
import api from '../services/api';

const steps = ['welcome', 'firmDetails', 'preferences', 'finish'];

const OnboardingWizard = ({ open, onClose, onComplete }) => {
    const { t, i18n } = useTranslation();
    const { user, refreshUser } = useAuth();
    const [activeStep, setActiveStep] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const [formData, setFormData] = useState({
        firmName: user?.firm?.name || '',
        firmAddress: '',
        language: i18n.language || 'fr',
        generateSampleData: true
    });

    const handleNext = async () => {
        if (activeStep === steps.length - 1) {
            await handleSubmit();
        } else {
            setActiveStep((prev) => prev + 1);
        }
    };

    const handleBack = () => {
        setActiveStep((prev) => prev - 1);
    };

    const handleSubmit = async () => {
        setLoading(true);
        setError(null);
        try {
            await api.post('/onboarding/complete', {
                firm_name: formData.firmName,
                firm_address: formData.firmAddress,
                language: formData.language,
                generate_sample_data: formData.generateSampleData
            });

            // Update language immediately
            i18n.changeLanguage(formData.language);

            // Refresh user context to get updated firm details
            if (refreshUser) await refreshUser();

            onComplete();
            onClose();
        } catch (err) {
            console.error('Onboarding error:', err);
            setError(t('errors.generic'));
        } finally {
            setLoading(false);
        }
    };

    const renderStepContent = (step) => {
        switch (step) {
            case 0:
                return (
                    <Box textAlign="center" py={4}>
                        <Typography variant="h4" gutterBottom>
                            {t('onboarding.welcomeTitle', { name: user?.name })}
                        </Typography>
                        <Typography variant="body1" color="text.secondary">
                            {t('onboarding.welcomeSubtitle')}
                        </Typography>
                    </Box>
                );
            case 1:
                return (
                    <Box py={2}>
                        <Typography variant="h6" gutterBottom>
                            {t('onboarding.firmDetails')}
                        </Typography>
                        <TextField
                            fullWidth
                            label={t('onboarding.firmName')}
                            value={formData.firmName}
                            onChange={(e) => setFormData({ ...formData, firmName: e.target.value })}
                            margin="normal"
                            required
                        />
                        <TextField
                            fullWidth
                            label={t('onboarding.firmAddress')}
                            value={formData.firmAddress}
                            onChange={(e) => setFormData({ ...formData, firmAddress: e.target.value })}
                            margin="normal"
                            multiline
                            rows={3}
                        />
                    </Box>
                );
            case 2:
                return (
                    <Box py={2}>
                        <Typography variant="h6" gutterBottom>
                            {t('onboarding.preferences')}
                        </Typography>
                        <FormControl fullWidth margin="normal">
                            <InputLabel>{t('onboarding.language')}</InputLabel>
                            <Select
                                value={formData.language}
                                label={t('onboarding.language')}
                                onChange={(e) => setFormData({ ...formData, language: e.target.value })}
                            >
                                <MenuItem value="fr">Français</MenuItem>
                                <MenuItem value="ar">العربية</MenuItem>
                                <MenuItem value="en">English</MenuItem>
                            </Select>
                        </FormControl>
                    </Box>
                );
            case 3:
                return (
                    <Box py={2}>
                        <Typography variant="h6" gutterBottom>
                            {t('onboarding.setupComplete')}
                        </Typography>
                        <Typography variant="body1" paragraph>
                            {t('onboarding.readyToStart')}
                        </Typography>
                        <FormControlLabel
                            control={
                                <Checkbox
                                    checked={formData.generateSampleData}
                                    onChange={(e) => setFormData({ ...formData, generateSampleData: e.target.checked })}
                                    color="primary"
                                />
                            }
                            label={t('onboarding.generateSampleData')}
                        />
                        <Typography variant="caption" display="block" color="text.secondary" sx={{ ml: 4 }}>
                            {t('onboarding.sampleDataDesc')}
                        </Typography>
                    </Box>
                );
            default:
                return null;
        }
    };

    return (
        <Dialog open={open} maxWidth="sm" fullWidth>
            <DialogContent>
                <Stepper activeStep={activeStep} alternativeLabel>
                    {steps.map((label) => (
                        <Step key={label}>
                            <StepLabel>{t(`onboarding.steps.${label}`)}</StepLabel>
                        </Step>
                    ))}
                </Stepper>

                {error && (
                    <Box mt={2}>
                        <Alert severity="error">{error}</Alert>
                    </Box>
                )}

                <Box mt={4}>
                    {renderStepContent(activeStep)}
                </Box>
            </DialogContent>
            <DialogActions sx={{ p: 3 }}>
                <Button
                    disabled={activeStep === 0 || loading}
                    onClick={handleBack}
                >
                    {t('common.back')}
                </Button>
                <Button
                    variant="contained"
                    onClick={handleNext}
                    disabled={loading || (activeStep === 1 && !formData.firmName)}
                >
                    {loading ? <CircularProgress size={24} /> : (activeStep === steps.length - 1 ? t('common.finish') : t('common.next'))}
                </Button>
            </DialogActions>
        </Dialog>
    );
};

export default OnboardingWizard;
