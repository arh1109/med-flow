import { useState } from 'react';
import {
  Button,
  Menu,
  MenuItem,
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';


const MENU_ITEMS = [
  { key: 'equipment', label: 'Equipment' },
  { key: 'work-orders', label: 'Work Orders' },
  { key: 'hospitals', label: 'Hospitals' },
  { key: 'users', label: 'Users', restrictedForTechnician: true },
  { key: 'analytics', label: 'Analytics', restrictedForTechnician: true },
];


function MainMenu({
  role,
  selectedPage,
  onPageChange,
}) {
  const [anchorEl, setAnchorEl] = useState(null);

  const open = Boolean(anchorEl);

  const visibleItems = MENU_ITEMS.filter((item) => {
    if (
      role === 'Field Technician' &&
      item.restrictedForTechnician
    ) {
      return false;
    }

    return true;
  });


  function handleOpen(event) {
    setAnchorEl(event.currentTarget);
  }


  function handleClose() {
    setAnchorEl(null);
  }


  function handleSelect(pageKey) {
    onPageChange(pageKey);
    handleClose();
  }


  return (
    <>
      <Button
        id="main-menu-button"
        color="inherit"
        startIcon={<MenuIcon />}
        onClick={handleOpen}
        aria-controls={open ? 'main-menu' : undefined}
        aria-haspopup="true"
        aria-expanded={open ? 'true' : undefined}
        sx={{ mr: 2 }}
      >
        Menu
      </Button>

      <Menu
        id="main-menu"
        anchorEl={anchorEl}
        open={open}
        onClose={handleClose}
        MenuListProps={{
          'aria-labelledby': 'main-menu-button',
        }}
      >
        {visibleItems.map((item) => (
          <MenuItem
            key={item.key}
            selected={selectedPage === item.key}
            onClick={() => handleSelect(item.key)}
          >
            {item.label}
          </MenuItem>
        ))}
      </Menu>
    </>
  );
}


export default MainMenu;
