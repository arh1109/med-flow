import {
  Alert,
  Box,
  Container,
  Snackbar,
  Typography,
} from '@mui/material';

import {
  useEffect,
  useState,
} from 'react';

import AppHeader from './components/layout/AppHeader.jsx';

import ReliabilityMetrics from './components/analytics/ReliabilityMetrics.jsx';
import MaintenanceFlags from './components/analytics/MaintenanceFlags.jsx';
import ReportingLines from './components/analytics/ReportingLines.jsx';

import LoginForm from './components/auth/LoginForm.jsx';
import EquipmentDataGrid from './components/equipments/EquipmentDataGrid.jsx';
import WorkOrderDataGrid from './components/work_orders/WorkOrderDataGrid.jsx';
import HospitalDataGrid from './components/hospitals/HospitalDataGrid.jsx';
import DiscrepancyDataGrid from './components/work_orders/DiscrepancyDataGrid.jsx';
import UserDataGrid from './components/users/UserDataGrid.jsx';

import {
  AuthProvider,
  useAuth,
} from './context/AuthContext.jsx';


const PAGE_TITLES = {
  equipment: 'Equipment',
  'work-orders': 'Work Orders',
  hospitals: 'Hospitals',
  users: 'Users',
  analytics: 'Analytics',
};


function Dashboard() {
  const { user, logout } = useAuth();

  const [notification, setNotification] =
    useState(null);

  // Equipment is the default page after login.
  const [selectedPage, setSelectedPage] =
    useState('equipment');


  // Reset navigation whenever a different user logs in.
  useEffect(() => {
    setSelectedPage('equipment');
  }, [user?.sub]);


  // Defensive guard in case the role changes while a restricted page
  // happens to be selected.
  useEffect(() => {
    if (
      user?.role === 'Field Technician' &&
      (
        selectedPage === 'users' ||
        selectedPage === 'analytics'
      )
    ) {
      setSelectedPage('equipment');
    }
  }, [selectedPage, user?.role]);


  function renderPage() {
    switch (selectedPage) {
      case 'equipment':
        return (
          <EquipmentDataGrid
            onSuccess={setNotification}
          />
        );

      case 'work-orders':
        return (
          <>
            <WorkOrderDataGrid
              onSuccess={setNotification}
            />
          </>
        );

      case 'hospitals':
        return (
          <HospitalDataGrid
            onSuccess={setNotification}
          />
        );

      case 'users':
        return (
          <UserDataGrid
            onSuccess={setNotification}
          />
        );

      case 'analytics':
        return (
          <>

            <Typography
              variant="h6"
              component="h3"
              gutterBottom
            >
              Co-Location Discrepancies
            </Typography>

            <DiscrepancyDataGrid />

            <Typography
              variant="h6"
              component="h3"
              gutterBottom
            >
              Reliability Metrics
            </Typography>

            <Box sx={{ mb: 4 }}>
              <ReliabilityMetrics />
            </Box>

            <Typography
              variant="h6"
              component="h3"
              gutterBottom
            >
              Maintenance Flags
            </Typography>

            <Box sx={{ mb: 4 }}>
              <MaintenanceFlags />
            </Box>

            <Typography
              variant="h6"
              component="h3"
              gutterBottom
            >
              Reporting Lines
            </Typography>

            <Box sx={{ mb: 4 }}>
              <ReportingLines />
            </Box>
          </>
        );

      default:
        return null;
    }
  }


  return (
    <>
      <AppHeader
        username={user?.sub}
        role={user?.role}
        onLogout={logout}
        selectedPage={selectedPage}
        onPageChange={setSelectedPage}
      />

      <Container
        maxWidth="lg"
        sx={{ mt: 4, mb: 4 }}
      >
        <Typography
          variant="h5"
          component="h2"
          gutterBottom
        >
          {PAGE_TITLES[selectedPage]}
        </Typography>

        <Box sx={{ mb: 4 }}>
          {renderPage()}
        </Box>
      </Container>

      <Snackbar
        open={Boolean(notification)}
        autoHideDuration={4000}
        onClose={() => setNotification(null)}
      >
        <Alert
          severity="success"
          onClose={() => setNotification(null)}
        >
          {notification}
        </Alert>
      </Snackbar>
    </>
  );
}


function AppContent() {
  const { isAuthenticated } = useAuth();

  return isAuthenticated
    ? <Dashboard />
    : <LoginForm />;
}


export default function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}
