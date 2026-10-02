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
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'serial_number', headerName: 'Serial Number', width: 150 },
    { field: 'model', headerName: 'Model', width: 160 },
    {
        field: 'battery_level',
        headerName: 'Battery %',
        width: 120,
        type: 'number',

        renderCell: (params) => {
            const isLowBattery = Number(params.value) < 20;

            return (
                <span
                    style={{
                        color: isLowBattery ? 'red' : 'inherit',
                        fontWeight: isLowBattery ? 'bold' : 'normal',
                    }}
                >
                    {params.value}
                </span>
            );
        },
    },
    { field: 'status', headerName: 'Status', width: 130 },
    { field: 'hospital_id', headerName: 'Branch ID', width: 110, type: 'number' },
];

function EquipmentDataGrid({ onSuccess }) {
    const { user } = useAuth();

    const [equipments, setEquipments] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [selectedEquipment, setSelectedEquipment] = useState(null);
    const [dialogMode, setDialogMode] = useState(null);

    const [searchText, setSearchText] = useState('');
const [searchField, setSearchField] = useState('serial_number');
const [isFiltered, setIsFiltered] = useState(false);

    const [formData, setFormData] = useState({
        serial_number: '',
        model: '',
        battery_level: '',
        status: 'Operational',
        hospital_id: '',
    });

    const isAdmin = user?.role === 'Operations Admin';

    const filteredEquipments = isFiltered
    ? equipments.filter((equipment) => {
        const value = equipment[searchField];

        if (value === null || value === undefined) {
            return false;
        }

        return String(value)
            .toLowerCase()
            .includes(searchText.toLowerCase());
    })
    : equipments;

    async function fetchEquipments() {
        try {
            setLoading(true);

            const response = await apiClient.get('/equipments');

            setEquipments(response.data);
            setError(null);
        } catch {
            setError('Could not load fleet data');
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        fetchEquipments();
    }, []);

    function handleSearch() {
    if (!searchText.trim()) return;

    setIsFiltered(true);
    setSelectedEquipment(null);
}

function handleClearFilter() {
    setSearchText('');
    setIsFiltered(false);
    setSelectedEquipment(null);
}

    function openAddDialog() {
        setFormData({
            serial_number: '',
            model: '',
            battery_level: '',
            status: 'Operational',
            hospital_id: '',
        });

        setDialogMode('add');
    }

    function openEditDialog() {
        if (!selectedEquipment) return;

        setFormData({
            serial_number: selectedEquipment.serial_number,
            model: selectedEquipment.model,
            battery_level: selectedEquipment.battery_level,
            status: selectedEquipment.status,
            hospital_id: selectedEquipment.hospital_id,
        });

        setDialogMode('edit');
    }

    function closeDialog() {
        setDialogMode(null);
    }

    async function handleSave() {
        const payload = {
            serial_number: formData.serial_number,
            model: formData.model,
            battery_level: Number(formData.battery_level),
            status: formData.status,
            hospital_id: Number(formData.hospital_id),
        };

        try {
            if (dialogMode === 'add') {
                await apiClient.post('/equipments', payload);

                onSuccess?.('Equipment created successfully');
            }

            if (dialogMode === 'edit') {
                /*
                 * IMPORTANT:
                 * Change this to .put(...) if your backend uses PUT.
                 */
                await apiClient.put(
                    `/equipments/${selectedEquipment.id}`,
                    payload
                );

                onSuccess?.('Equipment updated successfully');
            }

            closeDialog();
            await fetchEquipments();
        } catch (err) {
            console.error(err);
            console.error('Backend response:', err.response?.data);

            setError(
                err.response?.data?.detail ||
                'Could not save Equipment'
            );
        }
    }

    async function handleDelete() {
        if (!selectedEquipment) return;

        const confirmed = window.confirm(
            `Delete Equipment ${selectedEquipment.serial_number}?`
        );

        if (!confirmed) return;

        try {
            await apiClient.delete(`/equipments/${selectedEquipment.id}`);

            setSelectedEquipment(null);

            onSuccess?.('Equipment deleted successfully');

            await fetchEquipments();
        } catch (err) {
            console.error(err);
            setError('Could not delete Equipment');
        }
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
    sx={{ mb: 2, backgroundColor: 'white', }}
    alignItems="center"
>
    <TextField
        size="small"
        label="Search"
        value={searchText}
        onChange={(e) => setSearchText(e.target.value)}
        onKeyDown={(e) => {
            if (
                e.key === 'Enter' &&
                !isFiltered &&
                searchText.trim()
            ) {
                handleSearch();
            }
        }}
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
        <MenuItem value="serial_number">Serial Number</MenuItem>
        <MenuItem value="model">Model</MenuItem>
        <MenuItem value="battery_level">Battery Level</MenuItem>
        <MenuItem value="status">Status</MenuItem>
        <MenuItem value="hospital_id">Hospital ID</MenuItem>
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

    {isAdmin && (
        <>
            <Button
                variant="contained"
                onClick={openAddDialog}
            >
                Add Equipment
            </Button>

            <Button
                variant="outlined"
                disabled={!selectedEquipment}
                onClick={openEditDialog}
            >
                Edit Equipment
            </Button>

            <Button
                variant="outlined"
                color="error"
                disabled={!selectedEquipment}
                onClick={handleDelete}
            >
                Delete Equipment
            </Button>
        </>
    )}
</Stack>

            <Box sx={{ height: 400, width: '100%' }}>
                <DataGrid
                    rows={filteredEquipments}
                    columns={columns}
                    getRowId={(row) => row.id}

                    onRowClick={(params) => {
                        setSelectedEquipment(params.row);
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
                        ? 'Add Equipment'
                        : 'Edit Equipment'}
                </DialogTitle>

                <DialogContent>
                    <Stack
                        spacing={2}
                        sx={{ mt: 1 }}
                    >
                        <TextField
                            label="Serial Number"
                            value={formData.serial_number}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    serial_number: e.target.value,
                                })
                            }
                        />

                        <TextField
                            label="Model"
                            value={formData.model}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    model: e.target.value,
                                })
                            }
                        />

                        <TextField
                            label="Battery Level"
                            type="number"
                            value={formData.battery_level}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    battery_level: e.target.value,
                                })
                            }
                        />

                        <TextField
                            select
                            label="Status"
                            value={formData.status}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    status: e.target.value,
                                })
                            }
                        >
                            <MenuItem value="Operational">
                                Operational
                            </MenuItem>

                            <MenuItem value="Low-Battery">
                                Low-Battery
                            </MenuItem>

                            <MenuItem value="Maintenance">
                                Maintenance
                            </MenuItem>

                            <MenuItem value="Offline">
                                Offline
                            </MenuItem>
                        </TextField>

                        <TextField
                            label="Hospital ID"
                            type="number"
                            value={formData.hospital_id}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    hospital_id: e.target.value,
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

export default EquipmentDataGrid;