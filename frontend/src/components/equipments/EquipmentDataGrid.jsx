import {
    useEffect,
    useState,
} from 'react';

import {
    DataGrid,
} from '@mui/x-data-grid';

import {
    Alert,
    Box,
    Button,
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
    {
        field: 'id',
        headerName: 'ID',
        width: 70,
    },
    {
        field: 'serial_number',
        headerName: 'Serial Number',
        width: 150,
    },
    {
        field: 'model',
        headerName: 'Model',
        width: 190,
    },
    {
        field: 'status',
        headerName: 'Status',
        width: 140,
    },
    {
        field: 'battery_level',
        headerName: 'Battery %',
        type: 'number',
        width: 110,
    },
    {
        field: 'hospital_id',
        headerName: 'Hospital ID',
        type: 'number',
        width: 115,
    },
    {
        field: 'work_order_ids',
        headerName: 'Work Orders',
        width: 160,
        sortable: false,
        valueFormatter: (value) =>
            Array.isArray(value)
                ? value.join(', ')
                : '',
    },
    {
        field: 'technician_ids',
        headerName: 'Technicians',
        width: 150,
        sortable: false,
        valueFormatter: (value) =>
            Array.isArray(value)
                ? value.join(', ')
                : '',
    },
];


function EquipmentDataGrid({
    onSuccess,
}) {
    const { user } = useAuth();

    const [rows, setRows] = useState([]);
    const [rowCount, setRowCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const [selectedEquipment, setSelectedEquipment] =
        useState(null);

    const [dialogMode, setDialogMode] =
        useState(null);

    const [paginationModel, setPaginationModel] =
        useState({
            page: 0,
            pageSize: 5,
        });

    const [sortModel, setSortModel] =
        useState([
            {
                field: 'id',
                sort: 'asc',
            },
        ]);

    const [searchText, setSearchText] =
        useState('');

    const [debouncedSearch, setDebouncedSearch] =
        useState('');

    const [statusFilter, setStatusFilter] =
        useState('');

    const [hospitalFilter, setHospitalFilter] =
        useState('');

    const [formData, setFormData] = useState({
        serial_number: '',
        model: '',
        status: 'Available',
        battery_level: '',
        hospital_id: '',
    });

    const canManage =
        user?.role === 'Clinical Admin';


    useEffect(() => {
        const timer = window.setTimeout(
            () => {
                setDebouncedSearch(
                    searchText.trim()
                );

                setPaginationModel(
                    (current) => ({
                        ...current,
                        page: 0,
                    })
                );
            },
            350
        );

        return () =>
            window.clearTimeout(timer);
    }, [searchText]);


    useEffect(() => {
        let cancelled = false;

        async function fetchPage() {
            try {
                setLoading(true);

                const sort =
                    sortModel[0] || {
                        field: 'id',
                        sort: 'asc',
                    };

                const params = {
                    page:
                        paginationModel.page + 1,
                    size:
                        paginationModel.pageSize,
                    sort_by: sort.field,
                    sort_dir:
                        sort.sort || 'asc',
                };

                if (debouncedSearch) {
                    params.search =
                        debouncedSearch;
                }

                if (statusFilter) {
                    params.status =
                        statusFilter;
                }

                if (hospitalFilter) {
                    params.hospital_id =
                        Number(hospitalFilter);
                }

                const response =
                    await apiClient.get(
                        '/equipments',
                        { params }
                    );

                if (cancelled) return;

                setRows(
                    response.data.items
                );
                setRowCount(
                    response.data.total
                );
                setError(null);

                setSelectedEquipment(
                    (current) => {
                        if (!current) {
                            return null;
                        }

                        return (
                            response.data.items.find(
                                (row) =>
                                    row.id
                                    === current.id
                            ) || null
                        );
                    }
                );
            } catch (err) {
                if (cancelled) return;

                console.error(err);

                setError(
                    err.response?.data?.detail
                    || 'Could not load equipment'
                );
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        }

        fetchPage();

        return () => {
            cancelled = true;
        };
    }, [
        paginationModel,
        sortModel,
        debouncedSearch,
        statusFilter,
        hospitalFilter,
    ]);


    function resetToFirstPage() {
        setPaginationModel(
            (current) => ({
                ...current,
                page: 0,
            })
        );
    }


    function openAddDialog() {
        setFormData({
            serial_number: '',
            model: '',
            status: 'Available',
            battery_level: '',
            hospital_id: '',
        });

        setDialogMode('add');
    }


    function openEditDialog() {
        if (!selectedEquipment) return;

        setFormData({
            serial_number:
                selectedEquipment.serial_number,
            model:
                selectedEquipment.model,
            status:
                selectedEquipment.status,
            battery_level:
                selectedEquipment.battery_level,
            hospital_id:
                selectedEquipment.hospital_id ?? '',
        });

        setDialogMode('edit');
    }


    async function reloadCurrentPage() {
        // Toggling page through a functional update guarantees
        // a new fetch even when page number itself does not change.
        setPaginationModel(
            (current) => ({
                ...current,
            })
        );
    }


    async function handleSave() {
        const payload = {
            serial_number:
                formData.serial_number,
            model:
                formData.model,
            status:
                formData.status,
            battery_level:
                Number(formData.battery_level),
            hospital_id:
                formData.hospital_id === ''
                    ? null
                    : Number(
                        formData.hospital_id
                    ),
        };

        try {
            if (dialogMode === 'add') {
                await apiClient.post(
                    '/equipments',
                    payload
                );

                onSuccess?.(
                    'Equipment created successfully'
                );
            } else {
                await apiClient.put(
                    `/equipments/${selectedEquipment.id}`,
                    payload
                );

                onSuccess?.(
                    'Equipment updated successfully'
                );
            }

            setDialogMode(null);
            setSelectedEquipment(null);
            await reloadCurrentPage();
        } catch (err) {
            console.error(err);

            setError(
                err.response?.data?.detail
                || 'Could not save equipment'
            );
        }
    }


    async function handleDelete() {
        if (!selectedEquipment) return;

        if (
            !window.confirm(
                `Delete equipment "${selectedEquipment.serial_number}"?`
            )
        ) {
            return;
        }

        try {
            await apiClient.delete(
                `/equipments/${selectedEquipment.id}`
            );

            setSelectedEquipment(null);

            onSuccess?.(
                'Equipment deleted successfully'
            );

            resetToFirstPage();
        } catch (err) {
            console.error(err);

            setError(
                err.response?.data?.detail
                || 'Could not delete equipment'
            );
        }
    }


    return (
        <>
            {error && (
                <Alert
                    severity="error"
                    sx={{ mb: 2 }}
                >
                    {String(error)}
                </Alert>
            )}

            <Stack
                direction="row"
                spacing={2}
                alignItems="center"
                sx={{
                    mb: 2,
                    p: 2,
                    backgroundColor: 'white',
                    borderRadius: 1,
                    flexWrap: 'wrap',
                    rowGap: 2,
                }}
            >
                <TextField
                    size="small"
                    label="Search model or serial"
                    value={searchText}
                    onChange={(event) =>
                        setSearchText(
                            event.target.value
                        )
                    }
                />

                <TextField
                    select
                    size="small"
                    label="Status"
                    value={statusFilter}
                    onChange={(event) => {
                        setStatusFilter(
                            event.target.value
                        );
                        resetToFirstPage();
                    }}
                    sx={{ minWidth: 150 }}
                >
                    <MenuItem value="">
                        All
                    </MenuItem>
                    <MenuItem value="Available">
                        Available
                    </MenuItem>
                    <MenuItem value="In-Use">
                        In-Use
                    </MenuItem>
                    <MenuItem value="Maintenance">
                        Maintenance
                    </MenuItem>
                </TextField>

                <TextField
                    size="small"
                    label="Hospital ID"
                    type="number"
                    value={hospitalFilter}
                    onChange={(event) => {
                        setHospitalFilter(
                            event.target.value
                        );
                        resetToFirstPage();
                    }}
                    sx={{ width: 130 }}
                />

                <Button
                    variant="outlined"
                    onClick={() => {
                        setSearchText('');
                        setDebouncedSearch('');
                        setStatusFilter('');
                        setHospitalFilter('');
                        resetToFirstPage();
                    }}
                >
                    Clear Filters
                </Button>

                {canManage && (
                    <>
                        <Button
                            variant="contained"
                            onClick={openAddDialog}
                        >
                            Add Equipment
                        </Button>

                        <Button
                            variant="outlined"
                            disabled={
                                !selectedEquipment
                            }
                            onClick={openEditDialog}
                        >
                            Edit Equipment
                        </Button>

                        <Button
                            variant="outlined"
                            color="error"
                            disabled={
                                !selectedEquipment
                            }
                            onClick={handleDelete}
                        >
                            Delete Equipment
                        </Button>
                    </>
                )}
            </Stack>

            <Box
                sx={{
                    height: 520,
                    width: '100%',
                    backgroundColor: 'white',
                }}
            >
                <DataGrid
                    rows={rows}
                    columns={columns}
                    loading={loading}
                    rowCount={rowCount}
                    paginationMode="server"
                    sortingMode="server"
                    filterMode="server"
                    paginationModel={
                        paginationModel
                    }
                    onPaginationModelChange={
                        setPaginationModel
                    }
                    pageSizeOptions={[
                        10,
                        25,
                        50,
                        100,
                    ]}
                    sortModel={sortModel}
                    onSortModelChange={(
                        model
                    ) => {
                        setSortModel(model);
                        resetToFirstPage();
                    }}
                    disableRowSelectionOnClick
                    onRowClick={(params) =>
                        setSelectedEquipment(
                            params.row
                        )
                    }
                />
            </Box>

            <Dialog
                open={dialogMode !== null}
                onClose={() =>
                    setDialogMode(null)
                }
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
                            value={
                                formData.serial_number
                            }
                            onChange={(event) =>
                                setFormData({
                                    ...formData,
                                    serial_number:
                                        event.target.value,
                                })
                            }
                        />

                        <TextField
                            label="Model"
                            value={formData.model}
                            onChange={(event) =>
                                setFormData({
                                    ...formData,
                                    model:
                                        event.target.value,
                                })
                            }
                        />

                        <TextField
                            select
                            label="Status"
                            value={formData.status}
                            onChange={(event) =>
                                setFormData({
                                    ...formData,
                                    status:
                                        event.target.value,
                                })
                            }
                        >
                            <MenuItem value="Available">
                                Available
                            </MenuItem>
                            <MenuItem value="In-Use">
                                In-Use
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
                            label="Battery Level"
                            type="number"
                            value={
                                formData.battery_level
                            }
                            onChange={(event) =>
                                setFormData({
                                    ...formData,
                                    battery_level:
                                        event.target.value,
                                })
                            }
                        />

                        <TextField
                            label="Hospital ID"
                            type="number"
                            value={
                                formData.hospital_id
                            }
                            onChange={(event) =>
                                setFormData({
                                    ...formData,
                                    hospital_id:
                                        event.target.value,
                                })
                            }
                        />
                    </Stack>
                </DialogContent>

                <DialogActions>
                    <Button
                        onClick={() =>
                            setDialogMode(null)
                        }
                    >
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
