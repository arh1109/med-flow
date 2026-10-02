import { useEffect, useRef, useState } from 'react';
import { DataGrid } from '@mui/x-data-grid';
import {
    Alert,
    Box,
    Button,
    Chip,
    CircularProgress,
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


const columns = [
    { field: 'id', headerName: 'ID', width: 70 },
    { field: 'title', headerName: 'Title', width: 230 },
    { field: 'priority', headerName: 'Priority', width: 120 },
    { field: 'status', headerName: 'Status', width: 130 },
    { field: 'equipment_id', headerName: 'Equipment ID', width: 100, type: 'number' },
    {
        field: 'technician_id',
        headerName: 'Technician ID',
        width: 130,
        type: 'number',
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

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB


function getDiagnosticFilename(fileUrl) {
    if (!fileUrl) return '';

    const storedFilename = fileUrl.split('/').pop() || '';

    // Uploaded files are stored as <uuid>-<original-filename>.
    return storedFilename.replace(
        /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-/i,
        ''
    );
}


function WorkOrderDataGrid({ onSuccess }) {
    const { user } = useAuth();

    const [workOrders, setWorkOrders] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [selectedWorkOrder, setSelectedWorkOrder] = useState(null);
    const [dialogMode, setDialogMode] = useState(null);

    const [searchText, setSearchText] = useState('');
    const [searchField, setSearchField] = useState('title');
    const [isFiltered, setIsFiltered] = useState(false);

    const fileInputRef = useRef(null);
    const [uploadedLog, setUploadedLog] = useState(null);
    const [uploadingFile, setUploadingFile] = useState(false);

    const [statusSelection, setStatusSelection] = useState('');
    const [savingStatus, setSavingStatus] = useState(false);

    const [formData, setFormData] = useState({
        title: '',
        priority: 'Medium',
        status: 'Pending',
        equipment_id: '',
        technician_id: '',
    });

    const filteredWorkOrders = isFiltered
        ? workOrders.filter((workOrder) => {
            const value = workOrder[searchField];

            if (value === null || value === undefined) {
                return false;
            }

            return String(value)
                .toLowerCase()
                .includes(searchText.toLowerCase());
        })
        : workOrders;

    const canManageWorkOrders =
        user?.role === 'Clinical Admin';
    
    const canChangeWorkOrderStatus = user?.role === 'Field Technician';

    const canUploadDiagnostic =
    user?.role === 'Clinical Admin' ||
    user?.role === 'Field Technician';

    async function fetchWorkOrders() {
        try {
            setLoading(true);

            const response = await apiClient.get('/work_orders');

            setWorkOrders(response.data);
            setError(null);
        } catch (err) {
            console.error(err);
            setError(
                err.response?.data?.detail ||
                'Could not load work orders'
            );
        } finally {
            setLoading(false);
        }
    }


    async function fetchDiagnosticForWorkOrder(workOrderId) {
        try {
            const response = await apiClient.get('/diagnostic_logs');

            // /diagnostic_logs is ordered newest-first by the backend, so
            // find() gives us the most recent report for this work order.
            const diagnosticLog = response.data.find(
                (log) => log.work_order_id === workOrderId
            );

            setUploadedLog(diagnosticLog || null);
        } catch (err) {
            console.error(err);
            setUploadedLog(null);
            setError(
                err.response?.data?.detail ||
                'Could not load diagnostic report'
            );
        }
    }


    useEffect(() => {
        fetchWorkOrders();
    }, []);


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
            title: selectedWorkOrder.title,
            priority: selectedWorkOrder.priority,
            status: selectedWorkOrder.status,
            equipment_id: selectedWorkOrder.equipment_id,
            technician_id: selectedWorkOrder.technician_id,
        });

        setDialogMode('edit');
    }


    function closeDialog() {
        setDialogMode(null);
    }


    function handleSearch() {
        if (!searchText.trim()) return;

        setIsFiltered(true);
        setSelectedWorkOrder(null);
        setUploadedLog(null);
        setStatusSelection('');
    }


    function handleClearFilter() {
        setSearchText('');
        setIsFiltered(false);
        setSelectedWorkOrder(null);
        setUploadedLog(null);
        setStatusSelection('');
    }


    async function handleStatusSave() {
        if (
            !canChangeWorkOrderStatus ||
            !selectedWorkOrder ||
            !statusSelection
        ) {
            return;
        }

        try {
            setSavingStatus(true);
            setError(null);

            const response = await apiClient.patch(
                `/work_orders/${selectedWorkOrder.id}/status`,
                { status: statusSelection }
            );

            const updatedWorkOrder = response.data;

            setWorkOrders((current) =>
                current.map((workOrder) =>
                    workOrder.id === updatedWorkOrder.id
                        ? updatedWorkOrder
                        : workOrder
                )
            );

            setSelectedWorkOrder(updatedWorkOrder);
            setStatusSelection(updatedWorkOrder.status);

            onSuccess?.('Work order status updated successfully');
        } catch (err) {
            console.error(err);
            console.error('Backend response:', err.response?.data);

            setError(
                err.response?.data?.detail ||
                'Could not update work order status'
            );
        } finally {
            setSavingStatus(false);
        }
    }


    async function handleSave() {
        const payload = {
            title: formData.title,
            priority: formData.priority,
            status: formData.status,
            equipment_id: Number(formData.equipment_id),
            technician_id: Number(formData.technician_id),
        };

        try {
            if (dialogMode === 'add') {
                await apiClient.post('/work_orders', payload);
                onSuccess?.('Work order created successfully');
            }

            if (dialogMode === 'edit') {
                await apiClient.put(
                    `/work_orders/${selectedWorkOrder.id}`,
                    payload
                );
                onSuccess?.('Work order updated successfully');
            }

            closeDialog();
            setSelectedWorkOrder(null);
            setUploadedLog(null);
            setStatusSelection('');

            await fetchWorkOrders();
        } catch (err) {
            console.error(err);
            console.error('Backend response:', err.response?.data);

            setError(
                err.response?.data?.detail ||
                'Could not save work order'
            );
        }
    }


    async function handleDelete() {
        if (!selectedWorkOrder) return;

        const confirmed = window.confirm(
            `Delete work order "${selectedWorkOrder.title}"?`
        );

        if (!confirmed) return;

        try {
            await apiClient.delete(
                `/work_orders/${selectedWorkOrder.id}`
            );

            setSelectedWorkOrder(null);
            setUploadedLog(null);
            setStatusSelection('');

            onSuccess?.('Work order deleted successfully');

            await fetchWorkOrders();
        } catch (err) {
            console.error(err);
            console.error('Backend response:', err.response?.data);

            setError(
                err.response?.data?.detail ||
                'Could not delete work order'
            );
        }
    }


    async function handleDiagnosticFileSelected(event) {
        const file = event.target.files?.[0];

        // This lets the user pick the same file again after a failed upload.
        event.target.value = '';

        if (!file || !selectedWorkOrder) return;

        setError(null);

        const dotIndex = file.name.lastIndexOf('.');
        const extension = dotIndex >= 0
            ? file.name.slice(dotIndex).toLowerCase()
            : '';

        if (!ALLOWED_FILE_EXTENSIONS.includes(extension)) {
            setError(
                'Unsupported file type. Allowed: txt, pdf, png, jpg, jpeg, gif, webp.'
            );
            return;
        }

        if (file.size > MAX_FILE_SIZE) {
            setError('Diagnostic report cannot exceed 10 MB.');
            return;
        }

        const uploadData = new FormData();
        uploadData.append('work_order_id', String(selectedWorkOrder.id));
        uploadData.append('file', file);

        try {
            setUploadingFile(true);

            const response = await apiClient.post(
                '/diagnostic_logs',
                uploadData
            );

            setUploadedLog(response.data);
            onSuccess?.('Diagnostic report uploaded successfully');
        } catch (err) {
            console.error(err);
            console.error('Backend response:', err.response?.data);

            setError(
                err.response?.data?.detail ||
                'Could not upload diagnostic report'
            );
        } finally {
            setUploadingFile(false);
        }
    }


    function handleClearDiagnostic() {
        // The current backend has no DELETE /diagnostic_logs/{id} endpoint.
        // This only clears the attachment from the current UI selection.
        setUploadedLog(null);
    }


    async function handleDownloadDiagnostic() {
        if (!uploadedLog) return;

        try {
            const response = await apiClient.get(
                `/diagnostic_logs/${uploadedLog.id}/download`,
                { responseType: 'blob' }
            );

            const downloadUrl = window.URL.createObjectURL(response.data);
            const link = document.createElement('a');

            link.href = downloadUrl;
            link.download = getDiagnosticFilename(uploadedLog.file_url);
            document.body.appendChild(link);
            link.click();
            link.remove();
            window.URL.revokeObjectURL(downloadUrl);
        } catch (err) {
            console.error(err);

            setError(
                err.response?.data?.detail ||
                'Could not download diagnostic report'
            );
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
                    <MenuItem value="title">Title</MenuItem>
                    <MenuItem value="priority">Priority</MenuItem>
                    <MenuItem value="status">Status</MenuItem>
                    <MenuItem value="equipment_id">Equipment ID</MenuItem>
                    <MenuItem value="technician_id">Technician ID</MenuItem>
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

                {canManageWorkOrders && (
                    <>
                        <Button
                            variant="contained"
                            onClick={openAddDialog}
                        >
                            Add Work Order
                        </Button>

                        <Button
                            variant="outlined"
                            disabled={!selectedWorkOrder}
                            onClick={openEditDialog}
                        >
                            Edit Work Order
                        </Button>

                        <Button
                            variant="outlined"
                            color="error"
                            disabled={!selectedWorkOrder}
                            onClick={handleDelete}
                        >
                            Delete Work Order
                        </Button>
                    </>
                )}

                <input
                    ref={fileInputRef}
                    type="file"
                    hidden
                    accept=".txt,.pdf,.png,.jpg,.jpeg,.gif,.webp,image/*"
                    onChange={handleDiagnosticFileSelected}
                />

                {canUploadDiagnostic && selectedWorkOrder && (
                    <Button
                        variant="outlined"
                        disabled={uploadingFile}
                        onClick={() => fileInputRef.current?.click()}
                    >
                        {uploadingFile
                            ? 'Uploading...'
                            : 'Upload Report'}
                    </Button>
                )}
            </Stack>

            {selectedWorkOrder && uploadedLog && (
                <Box
                    sx={{
                        mb: 2,
                        display: 'flex',
                        alignItems: 'center',
                    }}
                >
                    <Chip
                        label={getDiagnosticFilename(uploadedLog.file_url)}
                        title={getDiagnosticFilename(uploadedLog.file_url)}
                        onClick={handleDownloadDiagnostic}
                        onDelete={handleClearDiagnostic}
                        clickable
                        sx={{
                            maxWidth: 360,
                            backgroundColor: 'white',
                            '& .MuiChip-label': {
                                display: 'block',
                                overflow: 'hidden',
                                textOverflow: 'ellipsis',
                                whiteSpace: 'nowrap',
                            },
                        }}
                    />
                </Box>
            )}


            {canChangeWorkOrderStatus && selectedWorkOrder && (
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
                    <FormControl size="small" sx={{ minWidth: 220 }}>
                        <InputLabel id="work-order-status-label">
                            Work Order Status
                        </InputLabel>

                        <Select
                            labelId="work-order-status-label"
                            id="work-order-status-select"
                            value={statusSelection}
                            label="Work Order Status"
                            onChange={(event) =>
                                setStatusSelection(event.target.value)
                            }
                        >
                            <MenuItem value="Pending">PENDING</MenuItem>
                            <MenuItem value="In-Progress">IN_PROGRESS</MenuItem>
                            <MenuItem value="Completed">COMPLETED</MenuItem>
                            <MenuItem value="Failed">FAILED</MenuItem>
                        </Select>
                    </FormControl>

                    <Button
                        variant="contained"
                        onClick={handleStatusSave}
                        disabled={
                            savingStatus ||
                            !statusSelection ||
                            statusSelection === selectedWorkOrder.status
                        }
                    >
                        {savingStatus ? 'Saving...' : 'Save Status'}
                    </Button>
                </Stack>
            )}

            <Box sx={{ height: 400, width: '100%', backgroundColor: 'white' }}>
                <DataGrid
                    rows={filteredWorkOrders}
                    columns={columns}
                    getRowId={(row) => row.id}
                    onRowClick={(params) => {
                        setSelectedWorkOrder(params.row);
                        setStatusSelection(params.row.status);
                        setUploadedLog(null);
                        setError(null);
                        fetchDiagnosticForWorkOrder(params.row.id);
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
                        ? 'Add Work Order'
                        : 'Edit Work Order'}
                </DialogTitle>

                <DialogContent>
                    <Stack spacing={2} sx={{ mt: 1 }}>
                        <TextField
                            label="Title"
                            value={formData.title}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    title: e.target.value,
                                })
                            }
                        />

                        <TextField
                            select
                            label="Priority"
                            value={formData.priority}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    priority: e.target.value,
                                })
                            }
                        >
                            <MenuItem value="Low">Low</MenuItem>
                            <MenuItem value="Medium">Medium</MenuItem>
                            <MenuItem value="Critical">Critical</MenuItem>
                        </TextField>

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
                            <MenuItem value="Pending">Pending</MenuItem>
                            <MenuItem value="In-Progress">In-Progress</MenuItem>
                            <MenuItem value="Completed">Completed</MenuItem>
                            <MenuItem value="Failed">Failed</MenuItem>
                        </TextField>

                        <TextField
                            label="Equipment ID"
                            type="number"
                            value={formData.equipment_id}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    equipment_id: e.target.value,
                                })
                            }
                        />

                        <TextField
                            label="Technician ID"
                            type="number"
                            value={formData.technician_id}
                            onChange={(e) =>
                                setFormData({
                                    ...formData,
                                    technician_id: e.target.value,
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


export default WorkOrderDataGrid;
