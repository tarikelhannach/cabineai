import React from 'react';
import { Box, Typography, Paper, Container } from '@mui/material';

export default function Settings() {
    return (
        <Container maxWidth="lg">
            <Box sx={{ py: 4 }}>
                <Typography variant="h4" gutterBottom>
                    Settings
                </Typography>
                <Paper sx={{ p: 3, mt: 2 }}>
                    <Typography variant="body1">
                        Settings page coming soon...
                    </Typography>
                </Paper>
            </Box>
        </Container>
    );
}
