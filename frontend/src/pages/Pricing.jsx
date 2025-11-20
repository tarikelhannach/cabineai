import React, { useState } from 'react';
import {
    Box,
    Button,
    Card,
    CardContent,
    CardHeader,
    Container,
    Grid,
    Typography,
    List,
    ListItem,
    ListItemIcon,
    ListItemText,
    CircularProgress
} from '@mui/material';
import { Check as CheckIcon, Star as StarIcon } from '@mui/icons-material';
import { useTranslation } from 'react-i18next';
import api from '../services/api';

const Pricing = () => {
    const { t } = useTranslation();
    const [loading, setLoading] = useState(false);

    const handleSubscribe = async (plan) => {
        try {
            setLoading(true);
            const response = await api.post('/billing/create-checkout-session', { plan });
            window.location.href = response.data.url;
        } catch (error) {
            console.error('Error creating checkout session:', error);
            setLoading(false);
        }
    };

    const plans = [
        {
            id: 'basic',
            title: 'Basic',
            price: '270 MAD',
            period: '/month',
            features: [
                '5 Users',
                '100 Documents/month',
                'Basic OCR',
                'Email Support'
            ]
        },
        {
            id: 'pro',
            title: 'Pro',
            price: '500 MAD',
            period: '/month',
            subheader: 'Most Popular',
            features: [
                'Unlimited Users',
                'Unlimited Documents',
                'Advanced AI OCR (QARI)',
                'Legal AI Assistant',
                'Priority Support'
            ]
        }
    ];

    const SETUP_FEE = "5,000 MAD One-time Implementation Fee";

    return (
        <Container maxWidth="md" component="main" sx={{ pt: 8, pb: 6 }}>
            <Typography component="h1" variant="h2" align="center" color="text.primary" gutterBottom>
                {t('pricing.title', 'Simple, Transparent Pricing')}
            </Typography>
            <Typography variant="h5" align="center" color="text.secondary" component="p" sx={{ mb: 6 }}>
                {t('pricing.subtitle', 'Choose the plan that fits your firm needs.')}
            </Typography>

            <Grid container spacing={5} alignItems="flex-end">
                {plans.map((plan) => (
                    <Grid item key={plan.title} xs={12} md={6}>
                        <Card sx={{
                            display: 'flex',
                            flexDirection: 'column',
                            border: plan.id === 'pro' ? '2px solid #38bdf8' : undefined,
                            position: 'relative',
                            height: '100%',
                            transition: 'transform 0.3s ease',
                            '&:hover': {
                                transform: 'translateY(-8px)',
                                boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)'
                            }
                        }}>
                            {plan.id === 'pro' && (
                                <Box sx={{
                                    position: 'absolute',
                                    top: 12,
                                    right: 12,
                                    display: 'flex',
                                    alignItems: 'center',
                                    gap: 0.5,
                                    color: '#0f172a',
                                    bgcolor: '#38bdf8',
                                    px: 1.5,
                                    py: 0.5,
                                    borderRadius: '20px',
                                    boxShadow: '0 4px 6px -1px rgba(56, 189, 248, 0.4)'
                                }}>
                                    <StarIcon fontSize="small" />
                                    <Typography variant="caption" fontWeight="800" letterSpacing="0.05em">
                                        POPULAR
                                    </Typography>
                                </Box>
                            )}
                            <CardHeader
                                title={plan.title}
                                subheader={plan.subheader}
                                titleTypographyProps={{ align: 'center', variant: 'h4', fontWeight: 800 }}
                                subheaderTypographyProps={{ align: 'center' }}
                                sx={{
                                    backgroundColor: (theme) => theme.palette.mode === 'light' ? 'rgba(241, 245, 249, 0.5)' : 'rgba(30, 41, 59, 0.5)',
                                    pb: 0
                                }}
                            />
                            <CardContent sx={{ flexGrow: 1, pt: 4 }}>
                                <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'baseline', mb: 4 }}>
                                    <Typography component="h2" variant="h3" color="text.primary" fontWeight="800">
                                        {plan.price}
                                    </Typography>
                                    <Typography variant="h6" color="text.secondary" sx={{ ml: 1 }}>
                                        {plan.period}
                                    </Typography>
                                </Box>

                                <Box sx={{ mb: 2, p: 1, bgcolor: 'warning.light', borderRadius: 1, display: 'flex', alignItems: 'center', gap: 1 }}>
                                    <Typography variant="caption" fontWeight="bold" color="warning.contrastText">
                                        + {SETUP_FEE}
                                    </Typography>
                                </Box>

                                <List>
                                    {plan.features.map((line) => (
                                        <ListItem key={line} disableGutters>
                                            <ListItemIcon sx={{ minWidth: 30 }}>
                                                <CheckIcon color="success" />
                                            </ListItemIcon>
                                            <ListItemText primary={line} />
                                        </ListItem>
                                    ))}
                                </List>
                            </CardContent>
                            <Box sx={{ p: 2 }}>
                                <Button
                                    fullWidth
                                    variant={plan.id === 'pro' ? 'contained' : 'outlined'}
                                    onClick={() => handleSubscribe(plan.id)}
                                    disabled={loading}
                                >
                                    {loading ? <CircularProgress size={24} /> : t('pricing.subscribe', 'Subscribe Now')}
                                </Button>
                            </Box>
                        </Card>
                    </Grid>
                ))}
            </Grid>
        </Container>
    );
};

export default Pricing;
