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

import apiClient from '../../api/client.js';
import { useAuth } from '../../context/AuthContext.jsx';


const columns = [
    {
        field: 'id',
        headerName: 'ID',
        width: 80,
        type: 'number',
    },
    {
        field: 'name',
        headerName: 'Name',
        width: 230,
    },
    {
        field: 'location_region',
        headerName: 'Location Region',
        width: 180,
    },
    {
        field: 'capacity',
        headerName: 'Capacity',
        width: 120,
        type: 'number',
    },
    {
        field: 'supervisor_id',
        headerName: 'Supervisor ID',
        width: 140,
        type: 'number',
    },
];


export default function HospitalDataGrid({
    onSuccess,
}) {
    const { user } = useAuth();

    const [hospitals, setHospitals] =
        useState([]);

    const [selectedHospital, setSelectedHospital] =
        useState(null);

    const [loading, setLoading] =
        useState(true);

    const [error, setError] =
        useState(null);

    const [dialogMode, setDialogMode] =
        useState(null);

    const [searchText, setSearchText] =
        useState('');

    const [searchField, setSearchField] =
        useState('name');

    const [isFiltered, setIsFiltered] =
        useState(false);

    const [formData, setFormData] =
        useState({
            name: '',
            location_region: '',
            capacity: '',
            supervisor_id: '',
        });


    const isAdmin =
        user?.role === 'Clinical Admin';


    const filteredHospitals =
        isFiltered
            ? hospitals.filter((hospital) => {
                const value =
                    hospital[searchField];

                if (
                    value === null ||
                    value === undefined
                ) {
                    return false;
                }

                return String(value)
                    .toLowerCase()
                    .includes(
                        searchText.toLowerCase()
                    );
            })
            : hospitals;


    async function fetchHospitals() {
        try {
            setLoading(true);

            const response =
                await apiClient.get(
                    '/hospitals'
                );

            setHospitals(response.data);
            setError(null);
        } catch (err) {
            console.error(err);

            setError(
                err.response?.data?.detail ||
                'Could not load hospitals'
            );
        } finally {
            setLoading(false);
        }
    }


    useEffect(() => {
        fetchHospitals();
    }, []);


    function openAddDialog() {
        setFormData({
            name: '',
            location_region: '',
            capacity: '',
            supervisor_id: '',
        });

        setDialogMode('add');
    }


    function openEditDialog() {
        if (!selectedHospital) {
            return;
        }

        setFormData({
            name: selectedHospital.name,
            location_region:
                selectedHospital.location_region,
            capacity:
                selectedHospital.capacity,
            supervisor_id:
                selectedHospital.supervisor_id,
        });

        setDialogMode('edit');
    }


    function closeDialog() {
        setDialogMode(null);
    }


    function handleSearch() {
        if (!searchText.trim()) {
            return;
        }

        setIsFiltered(true);
        setSelectedHospital(null);
    }


    function handleClearFilter() {
        setSearchText('');
        setIsFiltered(false);
        setSelectedHospital(null);
    }


    async function handleSave() {
        const payload = {
            name: formData.name.trim(),
            location_region:
                formData.location_region.trim(),
            capacity: Number(
                formData.capacity
            ),
            supervisor_id: Number(
                formData.supervisor_id
            ),
        };

        try {
            if (dialogMode === 'add') {
                await apiClient.post(
                    '/hospitals',
                    payload
                );

                onSuccess?.(
                    'Hospital created successfully'
                );
            }

            if (
                dialogMode === 'edit' &&
                selectedHospital
            ) {
                await apiClient.put(
                    `/hospitals/${selectedHospital.id}`,
                    payload
                );

                onSuccess?.(
                    'Hospital updated successfully'
                );
            }

            closeDialog();
            setSelectedHospital(null);

            await fetchHospitals();
        } catch (err) {
            console.error(err);

            setError(
                err.response?.data?.detail ||
                'Could not save hospital'
            );
        }
    }


    async function handleDelete() {
        if (!selectedHospital) {
            return;
        }

        const confirmed =
            window.confirm(
                `Delete hospital "${selectedHospital.name}"?\n\n` +
                'Its equipment and technicians will be kept, ' +
                'but their hospital assignments will be cleared.'
            );

        if (!confirmed) {
            return;
        }

        try {
            await apiClient.delete(
                `/hospitals/${selectedHospital.id}`
            );

            setSelectedHospital(null);

            onSuccess?.(
                'Hospital deleted successfully'
            );

            await fetchHospitals();
        } catch (err) {
            console.error(err);

            setError(
                err.response?.data?.detail ||
                'Could not delete hospital'
            );
        }
    }


    const saveDisabled =
        !formData.name.trim() ||
        !formData.location_region.trim() ||
        formData.capacity === '' ||
        Number(formData.capacity) < 0 ||
        formData.supervisor_id === '';


    if (loading) {
        return <CircularProgress />;
    }


    return (
        <>
            {error && (
                <Alert
                    severity="error"
                    sx={{ mb: 2 }}
                >
                    {error}
                </Alert>
            )}

            <Stack
                direction="row"
                spacing={2}
                sx={{
                    mb: 2,
                    backgroundColor: 'white',
                    alignItems: 'center',
                    flexWrap: 'wrap',
                }}
            >
                <TextField
                    size="small"
                    label="Search"
                    value={searchText}
                    onChange={(event) =>
                        setSearchText(
                            event.target.value
                        )
                    }
                    onKeyDown={(event) => {
                        if (
                            event.key === 'Enter' &&
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
                    onChange={(event) => {
                        setSearchField(
                            event.target.value
                        );
                        setIsFiltered(false);
                    }}
                    sx={{ minWidth: 180 }}
                >
                    <MenuItem value="id">
                        ID
                    </MenuItem>
                    <MenuItem value="name">
                        Name
                    </MenuItem>
                    <MenuItem value="location_region">
                        Location Region
                    </MenuItem>
                    <MenuItem value="capacity">
                        Capacity
                    </MenuItem>
                    <MenuItem value="supervisor_id">
                        Supervisor ID
                    </MenuItem>
                </TextField>

                <Button
                    variant="outlined"
                    onClick={handleSearch}
                    disabled={
                        isFiltered ||
                        !searchText.trim()
                    }
                >
                    Search
                </Button>

                <Button
                    variant="outlined"
                    onClick={handleClearFilter}
                    disabled={
                        !isFiltered &&
                        !searchText
                    }
                >
                    Clear
                </Button>

                {isAdmin && (
                    <>
                        <Button
                            variant="contained"
                            onClick={openAddDialog}
                        >
                            Add
                        </Button>

                        <Button
                            variant="outlined"
                            onClick={openEditDialog}
                            disabled={!selectedHospital}
                        >
                            Edit
                        </Button>

                        <Button
                            color="error"
                            variant="outlined"
                            onClick={handleDelete}
                            disabled={!selectedHospital}
                        >
                            Delete
                        </Button>
                    </>
                )}
            </Stack>

            <Box
                sx={{
                    width: '100%',
                    backgroundColor: 'white',
                }}
            >
                <DataGrid
                    rows={filteredHospitals}
                    columns={columns}
                    autoHeight
                    disableRowSelectionOnClick={false}
                    onRowClick={(params) =>
                        setSelectedHospital(
                            params.row
                        )
                    }
                    rowSelectionModel={{
                        type: 'include',
                        ids: new Set(
                            selectedHospital
                                ? [selectedHospital.id]
                                : []
                        ),
                    }}
                    pageSizeOptions={[
                        5,
                        10,
                        25,
                    ]}
                    initialState={{
                        pagination: {
                            paginationModel: {
                                pageSize: 5,
                            },
                        },
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
                        ? 'Add Hospital'
                        : `Edit Hospital #${selectedHospital?.id ?? ''}`}
                </DialogTitle>

                <DialogContent>
                    {dialogMode === 'edit' && (
                        <TextField
                            fullWidth
                            margin="normal"
                            label="Hospital ID"
                            value={
                                selectedHospital?.id ??
                                ''
                            }
                            disabled
                            helperText="Hospital ID cannot be changed."
                        />
                    )}

                    <TextField
                        fullWidth
                        margin="normal"
                        label="Name"
                        value={formData.name}
                        onChange={(event) =>
                            setFormData({
                                ...formData,
                                name:
                                    event.target.value,
                            })
                        }
                    />

                    <TextField
                        fullWidth
                        margin="normal"
                        label="Location Region"
                        value={
                            formData.location_region
                        }
                        onChange={(event) =>
                            setFormData({
                                ...formData,
                                location_region:
                                    event.target.value,
                            })
                        }
                    />

                    <TextField
                        fullWidth
                        margin="normal"
                        label="Capacity"
                        type="number"
                        inputProps={{
                            min: 0,
                        }}
                        value={formData.capacity}
                        onChange={(event) =>
                            setFormData({
                                ...formData,
                                capacity:
                                    event.target.value,
                            })
                        }
                    />

                    <TextField
                        fullWidth
                        margin="normal"
                        label="Supervisor ID"
                        type="number"
                        value={
                            formData.supervisor_id
                        }
                        onChange={(event) =>
                            setFormData({
                                ...formData,
                                supervisor_id:
                                    event.target.value,
                            })
                        }
                        helperText="Business identifier only; it is not linked to a User or Technician record."
                    />
                </DialogContent>

                <DialogActions>
                    <Button
                        onClick={closeDialog}
                    >
                        Cancel
                    </Button>

                    <Button
                        variant="contained"
                        onClick={handleSave}
                        disabled={saveDisabled}
                    >
                        Save
                    </Button>
                </DialogActions>
            </Dialog>
        </>
    );
}
