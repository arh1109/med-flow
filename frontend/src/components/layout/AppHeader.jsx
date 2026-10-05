import {
  AppBar,
  Toolbar,
  Typography,
  Box,
  Button,
} from '@mui/material';

import PrecisionManufacturingIcon from '@mui/icons-material/PrecisionManufacturing';
import MainMenu from '../menus/MainMenu.jsx';

{/* Every React component must return a single element. In this case, 
we are returning an AppBar component from Material-UI, which is a
top-level navigation bar that typically contains the application
title and other navigation elements. The AppBar is wrapped in a
Toolbar component, which provides padding and alignment for the
child elements. Inside the Toolbar, we have a PrecisionManufacturingIcon
component, which is an icon from Material-UI's icon library, 
and a Typography component, which is used to display the application title as a heading. */}

function AppHeader({
  username,
  role,
  onLogout,
  selectedPage,
  onPageChange,
}) {
  return (
    <AppBar position="static">
      <Toolbar>
        <MainMenu
          role={role}
          selectedPage={selectedPage}
          onPageChange={onPageChange}
        />

        <PrecisionManufacturingIcon sx={{ mr: 2 }} />

        <Typography
          variant="h6"
          component="h1"
          sx={{ flexGrow: 1 }}
        >
          MedFlow Clinical Equipment Command Center
        </Typography>

        {username && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              gap: 2,
            }}
          >
            <Typography variant="body2">
              {username} ({role})
            </Typography>

            <Button
              color="inherit"
              onClick={onLogout}
            >
              Log Out
            </Button>
          </Box>
        )}
      </Toolbar>
    </AppBar>
  );
}


export default AppHeader;



