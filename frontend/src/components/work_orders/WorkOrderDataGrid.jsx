import {
    useEffect,
    useRef,
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
    FormControl,
    InputLabel,
    MenuItem,
    Select,
    Stack,
    TextField,
} from '@mui/material';

import apiClient from '../../api/client';
import { useAuth } from '../../context/AuthContext.jsx';


function getDiagnosticFilename(fileUrl) {
    if (!fileUrl) return '';

    const storedFilename =
        fileUrl.split('/').pop() || '';

    return storedFilename.replace(
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-/i,
        ''
    );
}


const columns = [
    {
        field: 'id',
        headerName: 'ID',
        width: 70,
    },
    {
        field: 'title',
        headerName: 'Title',
        width: 230,
    },
    {
        field: 'priority',
        headerName: 'Priority',
        width: 120,
    },
    {
        field: 'status',
        headerName: 'Status',
        width: 130,
    },
    {
        field: 'equipment_id',
        headerName: 'Equipment ID',
        width: 115,
        type: 'number',
    },
    {
        field: 'technician_id',
        headerName: 'Technician ID',
        width: 130,
        type: 'number',
    },
    {
        field: 'report_filename',
        headerName: 'Report Filename',
        width: 240,
        sortable: false,
    },
];


const ALLOWED_FILE_EXTENSIONS = [
    '.txt',
    '.pdf',
    '.png',
    '.jpg',
    '.jpeg',
    '.gif',
    '.webp',
];

const MAX_FILE_SIZE =
    10 * 1024 * 1024;


function WorkOrderDataGrid({
    onSuccess,
}) {
    const { user } = useAuth();

    const [rows, setRows] = useState([]);
    const [rowCount, setRowCount] =
        useState(0);
    const [loading, setLoading] =
        useState(false);
    const [error, setError] =
        useState(null);

    const [
        selectedWorkOrder,
        setSelectedWorkOrder,
    ] = useState(null);

    const [dialogMode, setDialogMode] =
        useState(null);

    const [paginationModel, setPaginationModel] =
        useState({
            page: 0,
            pageSize: 25,
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

    const [
        debouncedSearch,
        setDebouncedSearch,
    ] = useState('');

    const [statusFilter, setStatusFilter] =
        useState('');

    const [
        hospitalFilter,
        setHospitalFilter,
    ] = useState('');

    const fileInputRef = useRef(null);
    const [
        uploadingFile,
        setUploadingFile,
    ] = useState(false);

    const [
        statusSelection,
        setStatusSelection,
    ] = useState('');

    const [
        savingStatus,
        setSavingStatus,
    ] = useState(false);

    const [formData, setFormData] =
        useState({
            title: '',
            priority: 'Medium',
            status: 'Pending',
            equipment_id: '',
            technician_id: '',
        });

    const canManage =
        user?.role === 'Clinical Admin';

    const canChangeStatus =
        user?.role === 'Field Technician';

    const canDownload =
        user?.role === 'Clinical Admin'
        || user?.role === 'Auditor';


    function resetToFirstPage() {
        setPaginationModel(
            (current) => ({
                ...current,
                page: 0,
            })
        );
    }


    useEffect(() => {
        const timer = window.setTimeout(
            () => {
                setDebouncedSearch(
                    searchText.trim()
                );
                resetToFirstPage();
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
                        Number(
                            hospitalFilter
                        );
                }

                const response =
                    await apiClient.get(
                        '/work_orders',
                        { params }
                    );

                if (cancelled) return;

                const pageRows =
                    response.data.items.map(
                        (workOrder) => ({
                            ...workOrder,
                            report_filename:
                                getDiagnosticFilename(
                                    workOrder
                                        .diagnostic_file_url
                                ),
                        })
                    );

                setRows(pageRows);
                setRowCount(
                    response.data.total
                );

                setSelectedWorkOrder(
                    (current) => {
                        if (!current) {
                            return null;
                        }

                        return (
                            pageRows.find(
                                (row) =>
                                    row.id
                                    === current.id
                            ) || null
                        );
                    }
                );

                setError(null);
            } catch (err) {
                if (cancelled) return;

                console.error(err);

                setError(
                    err.response?.data?.detail
                    || 'Could not load work orders'
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


    function openAddDialog() {
        setFormData({
            title: '',
            priority: 'Medium',
            status: 'Pending',
            equipment_id: '',
            technician_id: '',
        });

        setDialogMode('add');
    }


    function openEditDialog() {
        if (!selectedWorkOrder) return;

        setFormData({
            title:
                selectedWorkOrder.title,
            priority:
                selectedWorkOrder.priority,
            status:
                selectedWorkOrder.status,
            equipment_id:
                selectedWorkOrder.equipment_id,
            technician_id:
                selectedWorkOrder.technician_id,
        });

        setDialogMode('edit');
    }


    function triggerReload() {
        setPaginationModel(
            (current) => ({
                ...current,
            })
        );
    }


    async function handleSave() {
        const payload = {
            title:
                formData.title,
            priority:
                formData.priority,
            status:
                formData.status,
            equipment_id:
                Number(
                    formData.equipment_id
                ),
            technician_id:
                Number(
                    formData.technician_id
                ),
        };

        try {
            if (dialogMode === 'add') {
                await apiClient.post(
                    '/work_orders',
                    payload
                );

                onSuccess?.(
                    'Work order created successfully'
                );
            } else {
                await apiClient.put(
                    `/work_orders/${selectedWorkOrder.id}`,
                    payload
                );

                onSuccess?.(
                    'Work order updated successfully'
                );
            }

            setDialogMode(null);
            setSelectedWorkOrder(null);
            triggerReload();
        } catch (err) {
            console.error(err);

            setError(
                err.response?.data?.detail
                || 'Could not save work order'
            );
        }
    }


    async function handleDelete() {
        if (!selectedWorkOrder) return;

        if (
            !window.confirm(
                `Delete work order "${selectedWorkOrder.title}"?`
            )
        ) {
            return;
        }

        try {
            await apiClient.delete(
                `/work_orders/${selectedWorkOrder.id}`
            );

            setSelectedWorkOrder(null);

            onSuccess?.(
                'Work order deleted successfully'
            );

            resetToFirstPage();
        } catch (err) {
            console.error(err);

            setError(
                err.response?.data?.detail
                || 'Could not delete work order'
            );
        }
    }


    async function handleStatusSave() {
        if (
            !canChangeStatus
            || !selectedWorkOrder
            || !statusSelection
        ) {
            return;
        }

        try {
            setSavingStatus(true);

            await apiClient.patch(
                `/work_orders/${selectedWorkOrder.id}/status`,
                {
                    status:
                        statusSelection,
                }
            );

            onSuccess?.(
                'Work order status updated successfully'
            );

            triggerReload();
        } catch (err) {
            console.error(err);

            setError(
                err.response?.data?.detail
                || 'Could not update work order status'
            );
        } finally {
            setSavingStatus(false);
        }
    }


    async function handleDiagnosticFileSelected(
        event
    ) {
        const file =
            event.target.files?.[0];

        event.target.value = '';

        if (
            !file
            || !selectedWorkOrder
        ) {
            return;
        }

        const dotIndex =
            file.name.lastIndexOf('.');

        const extension =
            dotIndex >= 0
                ? file.name
                    .slice(dotIndex)
                    .toLowerCase()
                : '';

        if (
            !ALLOWED_FILE_EXTENSIONS.includes(
                extension
            )
        ) {
            setError(
                'Unsupported file type. Allowed: txt, pdf, png, jpg, jpeg, gif, webp.'
            );
            return;
        }

        if (
            file.size
            > MAX_FILE_SIZE
        ) {
            setError(
                'Diagnostic report cannot exceed 10 MB.'
            );
            return;
        }

        const uploadData =
            new FormData();

        uploadData.append(
            'work_order_id',
            String(
                selectedWorkOrder.id
            )
        );

        uploadData.append(
            'file',
            file
        );

        try {
            setUploadingFile(true);

            await apiClient.post(
                '/diagnostic_logs',
                uploadData
            );

            onSuccess?.(
                'Diagnostic report uploaded successfully'
            );

            triggerReload();
        } catch (err) {
            console.error(err);

            setError(
                err.response?.data?.detail
                || 'Could not upload diagnostic report'
            );
        } finally {
            setUploadingFile(false);
        }
    }


    async function handleDownloadDiagnostic() {
        if (
            !selectedWorkOrder
                ?.diagnostic_log_id
        ) {
            return;
        }

        try {
            const response =
                await apiClient.get(
                    `/diagnostic_logs/${selectedWorkOrder.diagnostic_log_id}/download`,
                    {
                        responseType:
                            'blob',
                    }
                );

            const url =
                window.URL.createObjectURL(
                    response.data
                );

            const link =
                document.createElement(
                    'a'
                );

            link.href = url;
            link.download =
                selectedWorkOrder
                    .report_filename
                || 'diagnostic-report';

            document.body.appendChild(
                link
            );

            link.click();
            link.remove();

            window.URL.revokeObjectURL(
                url
            );
        } catch (err) {
            console.error(err);

            setError(
                err.response?.data?.detail
                || 'Could not download diagnostic report'
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
                    label="Search title, model, or serial"
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
                    <MenuItem value="Pending">
                        Pending
                    </MenuItem>
                    <MenuItem value="In-Progress">
                        In-Progress
                    </MenuItem>
                    <MenuItem value="Completed">
                        Completed
                    </MenuItem>
                    <MenuItem value="Failed">
                        Failed
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
                            Add Work Order
                        </Button>

                        <Button
                            variant="outlined"
                            disabled={
                                !selectedWorkOrder
                            }
                            onClick={
                                openEditDialog
                            }
                        >
                            Edit Work Order
                        </Button>

                        <Button
                            variant="outlined"
                            color="error"
                            disabled={
                                !selectedWorkOrder
                            }
                            onClick={
                                handleDelete
                            }
                        >
                            Delete Work Order
                        </Button>

                        <input
                            ref={fileInputRef}
                            type="file"
                            hidden
                            accept=".txt,.pdf,.png,.jpg,.jpeg,.gif,.webp,image/*"
                            onChange={
                                handleDiagnosticFileSelected
                            }
                        />

                        {selectedWorkOrder && (
                            <Button
                                variant="outlined"
                                disabled={
                                    uploadingFile
                                }
                                onClick={() =>
                                    fileInputRef
                                        .current
                                        ?.click()
                                }
                            >
                                {uploadingFile
                                    ? 'Uploading...'
                                    : 'Upload Report'}
                            </Button>
                        )}
                    </>
                )}

                {canDownload
                    && selectedWorkOrder
                        ?.diagnostic_log_id && (
                    <Button
                        variant="outlined"
                        onClick={
                            handleDownloadDiagnostic
                        }
                    >
                        Download Report
                    </Button>
                )}
            </Stack>

            {canChangeStatus
                && selectedWorkOrder && (
                <Stack
                    direction="row"
                    spacing={2}
                    alignItems="center"
                    sx={{
                        mb: 2,
                        p: 2,
                        backgroundColor: 'white',
                        borderRadius: 1,
                    }}
                >
                    <FormControl
                        size="small"
                        sx={{
                            minWidth: 220,
                        }}
                    >
                        <InputLabel>
                            Work Order Status
                        </InputLabel>

                        <Select
                            value={
                                statusSelection
                            }
                            label="Work Order Status"
                            onChange={(event) =>
                                setStatusSelection(
                                    event.target.value
                                )
                            }
                        >
                            <MenuItem value="Pending">
                                PENDING
                            </MenuItem>
                            <MenuItem value="In-Progress">
                                IN_PROGRESS
                            </MenuItem>
                            <MenuItem value="Completed">
                                COMPLETED
                            </MenuItem>
                            <MenuItem value="Failed">
                                FAILED
                            </MenuItem>
                        </Select>
                    </FormControl>

                    <Button
                        variant="contained"
                        onClick={
                            handleStatusSave
                        }
                        disabled={
                            savingStatus
                            || !statusSelection
                            || statusSelection
                                === selectedWorkOrder
                                    .status
                        }
                    >
                        {savingStatus
                            ? 'Saving...'
                            : 'Save Status'}
                    </Button>
                </Stack>
            )}

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
                    onRowClick={(params) => {
                        setSelectedWorkOrder(
                            params.row
                        );

                        setStatusSelection(
                            params.row.status
                        );

                        setError(null);
                    }}
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
                        ? 'Add Work Order'
                        : 'Edit Work Order'}
                </DialogTitle>

                <DialogContent>
                    <Stack
                        spacing={2}
                        sx={{ mt: 1 }}
                    >
                        <TextField
                            label="Title"
                            value={formData.title}
                            onChange={(event) =>
                                setFormData({
                                    ...formData,
                                    title:
                                        event.target.value,
                                })
                            }
                        />

                        <TextField
                            select
                            label="Priority"
                            value={
                                formData.priority
                            }
                            onChange={(event) =>
                                setFormData({
                                    ...formData,
                                    priority:
                                        event.target.value,
                                })
                            }
                        >
                            <MenuItem value="Low">
                                Low
                            </MenuItem>
                            <MenuItem value="Medium">
                                Medium
                            </MenuItem>
                            <MenuItem value="Critical">
                                Critical
                            </MenuItem>
                        </TextField>

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
                            <MenuItem value="Pending">
                                Pending
                            </MenuItem>
                            <MenuItem value="In-Progress">
                                In-Progress
                            </MenuItem>
                            <MenuItem value="Completed">
                                Completed
                            </MenuItem>
                            <MenuItem value="Failed">
                                Failed
                            </MenuItem>
                        </TextField>

                        <TextField
                            label="Equipment ID"
                            type="number"
                            value={
                                formData.equipment_id
                            }
                            onChange={(event) =>
                                setFormData({
                                    ...formData,
                                    equipment_id:
                                        event.target.value,
                                })
                            }
                        />

                        <TextField
                            label="Technician ID"
                            type="number"
                            value={
                                formData.technician_id
                            }
                            onChange={(event) =>
                                setFormData({
                                    ...formData,
                                    technician_id:
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


export default WorkOrderDataGrid;
