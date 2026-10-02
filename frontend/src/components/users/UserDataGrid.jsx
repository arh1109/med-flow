import { useEffect, useState } from 'react';
import { DataGrid } from '@mui/x-data-grid';

import {
    Alert,
    Box,
    Button,
    CircularProgress,
    Dialog,
    DialogActions,
    DialogContent,
    DialogTitle,
    MenuItem,
    Stack,
    TextField,
} from '@mui/material';

import apiClient from '../../api/client';
import { useAuth } from '../../context/AuthContext.jsx';


const columns = [
    { field: 'id', headerName: 'ID', width: 80 },
    { field: 'username', headerName: 'Username', width: 200 },
    { field: 'role', headerName: 'Role', width: 200 },
];


export default function UserDataGrid({ onSuccess }) {
    const { user } = useAuth();

    const [users, setUsers] = useState([]);
    const [selectedUser, setSelectedUser] = useState(null);

    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [dialogMode, setDialogMode] = useState(null);

    const [searchText, setSearchText] = useState('');
const [searchField, setSearchField] = useState('username');
const [isFiltered, setIsFiltered] = useState(false);

    const [formData, setFormData] = useState({
        username: '',
        role: 'Auditor',
        password: '',
    });

    const isAdmin = user?.role === 'Clinical Admin';

    const filteredUsers = isFiltered
    ? users.filter((account) => {
        const value = account[searchField];

        if (value === null || value === undefined) {
            return false;
        }

        return String(value)
            .toLowerCase()
            .includes(searchText.toLowerCase());
    })
    : users;

    async function fetchUsers() {
        try {
            setLoading(true);

            const response = await apiClient.get('/users');

            setUsers(response.data);
            setError(null);
        } catch (err) {
            console.error(err);

            setError(
                err.response?.data?.detail ||
                'Could not load users'
            );
        } finally {
            setLoading(false);
        }
    }


    useEffect(() => {
        if (isAdmin) {
            fetchUsers();
        }
    }, [isAdmin]);


    function openAddDialog() {
        setFormData({
            username: '',
            role: 'Auditor',
            password: '',
        });

        setDialogMode('add');
    }


    function openEditDialog() {
        if (!selectedUser) return;

        setFormData({
            username: selectedUser.username,
            role: selectedUser.role,

            // Never load an existing password into the UI.
            password: '',
        });

        setDialogMode('edit');
    }


    function closeDialog() {
        setDialogMode(null);
    }

    function handleSearch() {
    if (!searchText.trim()) return;

    setIsFiltered(true);
    setSelectedUser(null);
}


function handleClearFilter() {
    setSearchText('');
    setIsFiltered(false);
    setSelectedUser(null);
}

    async function handleSave() {
        try {
            if (dialogMode === 'add') {
                await apiClient.post('/users', {
                    username: formData.username,
                    role: formData.role,
                    password: formData.password,
                });

                onSuccess?.('User account created successfully');
            }

            if (dialogMode === 'edit') {
                const payload = {
                    username: formData.username,
                    role: formData.role,
                };

                // Blank means don't change the password.
                if (formData.password) {
                    payload.password = formData.password;
                }

                await apiClient.put(
                    `/users/${selectedUser.id}`,
                    payload
                );

                onSuccess?.('User account updated successfully');
            }

            closeDialog();
            setSelectedUser(null);

            await fetchUsers();

        } catch (err) {
            console.error(err);
            console.error('Backend response:', err.response?.data);

            setError(
                err.response?.data?.detail ||
                'Could not save user account'
            );
        }
    }


    async function handleDelete() {
    if (!selectedUser) return;

    if (selectedUser.username === user?.sub) {
        setError('You cannot delete your own user account');
        return;
    }

    const confirmed = window.confirm(
        `Delete user "${selectedUser.username}"?`
    );

    if (!confirmed) return;

    try {
        await apiClient.delete(`/users/${selectedUser.id}`);

        setSelectedUser(null);

        onSuccess?.('User account deleted successfully');

        await fetchUsers();

    } catch (err) {
        console.error(err);

        setError(
            err.response?.data?.detail ||
            'Could not delete user account'
        );
    }
}


    // This component should not expose anything to non-admin users.
    if (!isAdmin) {
        return null;
    }

    if (loading) {
        return <CircularProgress />;
    }


    return (
        <>
            {error && (
                <Alert severity="error" sx={{ mb: 2 }}>
                    {error}
                </Alert>
            )}

            <Stack
            direction="row"
            spacing={2}
            sx={{ mb: 2, backgroundColor: 'white' }}
            alignItems="center"
        >
            <TextField
                size="small"
                label="Search"
                value={searchText}
                onChange={(e) => setSearchText(e.target.value)}
            />

            <TextField
                select
                size="small"
                label="Search Criteria"
                value={searchField}
                onChange={(e) => {
                    setSearchField(e.target.value);
                    setIsFiltered(false);
                }}
                sx={{ minWidth: 170 }}
            >
                <MenuItem value="id">ID</MenuItem>
                <MenuItem value="username">Username</MenuItem>
                <MenuItem value="role">Role</MenuItem>
            </TextField>

            <Button
                variant="outlined"
                onClick={handleSearch}
                disabled={isFiltered || !searchText.trim()}
            >
                Search
            </Button>

            <Button
                variant="outlined"
                onClick={handleClearFilter}
                disabled={!isFiltered}
            >
                Clear Filter
            </Button>

            <Button
                variant="contained"
                onClick={openAddDialog}
            >
                Add User
            </Button>

            <Button
                variant="outlined"
                disabled={!selectedUser}
                onClick={openEditDialog}
            >
                Edit User
            </Button>

            <Button
                variant="outlined"
                color="error"
                disabled={
                    !selectedUser ||
                    selectedUser.username === user?.sub
                }
                onClick={handleDelete}
            >
                Delete User
            </Button>
        </Stack>

            <Box sx={{ height: 350, width: '100%' }}>
                <DataGrid
                    rows={filteredUsers}
                    columns={columns}
                    getRowId={(row) => row.id}
                    onRowClick={(params) => {
                        setSelectedUser(params.row);
                    }}
                />
            </Box>

            <Dialog
                open={dialogMode !== null}
                onClose={closeDialog}
                fullWidth
                maxWidth="sm"
            >
                <DialogTitle>
                    {dialogMode === 'add'
                        ? 'Add User Account'
                        : 'Edit User Account'}
                </DialogTitle>

                <DialogContent>
                    <Stack spacing={2} sx={{ mt: 1 }}>
                        <TextField
                            label="Username"
                            value={formData.username}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    username: e.target.value,
                                })
                            }
                        />

                        <TextField
                            select
                            label="Role"
                            value={formData.role}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    role: e.target.value,
                                })
                            }
                        >
                            <MenuItem value="Clinical Admin">
                                Operations Admin
                            </MenuItem>

                            <MenuItem value="Field Technician">
                                Field Technician
                            </MenuItem>

                            <MenuItem value="Auditor">
                                Auditor
                            </MenuItem>
                        </TextField>

                        <TextField
                            label={
                                dialogMode === 'add'
                                    ? 'Password'
                                    : 'New Password (leave blank to keep current)'
                            }
                            type="password"
                            value={formData.password}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    password: e.target.value,
                                })
                            }
                        />
                    </Stack>
                </DialogContent>

                <DialogActions>
                    <Button onClick={closeDialog}>
                        Cancel
                    </Button>

                    <Button
                        variant="contained"
                        onClick={handleSave}
                    >
                        Save
                    </Button>
                </DialogActions>
            </Dialog>
        </>
    );
}