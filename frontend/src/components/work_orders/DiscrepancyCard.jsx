import {Alert, Card, CardContent, Typography, Stack} from '@mui/material';

function DiscrepancyCard({discrepancy}){
    return (
        <Card variant="outlined" sx={{ minWidth: 280 }}>
            <CardContent>
                <Typography variant="h6" component="div">
                    {discrepancy.title}
                </Typography>
                <Typography color="text.secondary" gutterBottom>
                    Work Order #{discrepancy.workOrderId}
                </Typography>
                <Stack spacing={0.5} sx={{ mb: 1.5}}>
                    <Typography variant="body2">
                        Equipment Hospital: {discrepancy.equipmentHospitalId}
                    </Typography>
                    <Typography variant="body2">
                        Technician Equipment: {discrepancy.technicianHospitalId}
                    </Typography>
                </Stack>
                <Alert severity="warning">Branch Mismatch Detected</Alert>
            </CardContent>
        </Card>
    )
}

export default DiscrepancyCard;