import { useEffect, useMemo, useState } from 'react';

import {
    Alert,
    CircularProgress,
    Paper,
    Table,
    TableBody,
    TableCell,
    TableContainer,
    TableHead,
    TableRow,
    TableSortLabel,
} from '@mui/material';

import apiClient from '../../api/client';


const SORTABLE_COLUMNS = {
    total_equipments: 'total_equipments',
    maintenance_count: 'maintenance_count',
    maintenance_percentage: 'maintenance_percentage',
};


export default function MaintenanceFlags() {
    const [flags, setFlags] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [orderBy, setOrderBy] =
        useState('maintenance_percentage');

    const [order, setOrder] =
        useState('desc');


    useEffect(() => {
        async function fetchFlags() {
            try {
                setLoading(true);

                const response = await apiClient.get(
                    '/hospitals/maintenance-flags'
                );

                setFlags(response.data);
                setError(null);
            } catch (err) {
                console.error(err);

                setError(
                    err.response?.data?.detail ||
                    'Could not load maintenance flags'
                );
            } finally {
                setLoading(false);
            }
        }

        fetchFlags();
    }, []);


    function handleSort(column) {
        if (orderBy === column) {
            setOrder((currentOrder) =>
                currentOrder === 'asc'
                    ? 'desc'
                    : 'asc'
            );
        } else {
            setOrderBy(column);
            setOrder('asc');
        }
    }


    const sortedFlags = useMemo(() => {
        const rows = [...flags];

        rows.sort((a, b) => {
            const aValue = Number(a[orderBy]);
            const bValue = Number(b[orderBy]);

            if (aValue < bValue) {
                return order === 'asc' ? -1 : 1;
            }

            if (aValue > bValue) {
                return order === 'asc' ? 1 : -1;
            }

            return 0;
        });

        return rows;
    }, [flags, order, orderBy]);


    if (loading) {
        return <CircularProgress />;
    }


    if (error) {
        return (
            <Alert severity="error">
                {error}
            </Alert>
        );
    }


    return (
        <TableContainer
            component={Paper}
            sx={{ backgroundColor: 'white' }}
        >
            <Table>
                <TableHead>
                    <TableRow>
                        <TableCell>
                            Hospital ID
                        </TableCell>

                        <TableCell>
                            Hospital
                        </TableCell>

                        <TableCell align="right">
                            <TableSortLabel
                                active={
                                    orderBy ===
                                    SORTABLE_COLUMNS.total_equipments
                                }
                                direction={
                                    orderBy ===
                                    SORTABLE_COLUMNS.total_equipments
                                        ? order
                                        : 'asc'
                                }
                                onClick={() =>
                                    handleSort(
                                        SORTABLE_COLUMNS.total_equipments
                                    )
                                }
                            >
                                Total Equipments
                            </TableSortLabel>
                        </TableCell>

                        <TableCell align="right">
                            <TableSortLabel
                                active={
                                    orderBy ===
                                    SORTABLE_COLUMNS.maintenance_count
                                }
                                direction={
                                    orderBy ===
                                    SORTABLE_COLUMNS.maintenance_count
                                        ? order
                                        : 'asc'
                                }
                                onClick={() =>
                                    handleSort(
                                        SORTABLE_COLUMNS.maintenance_count
                                    )
                                }
                            >
                                In Maintenance
                            </TableSortLabel>
                        </TableCell>

                        <TableCell align="right">
                            <TableSortLabel
                                active={
                                    orderBy ===
                                    SORTABLE_COLUMNS.maintenance_percentage
                                }
                                direction={
                                    orderBy ===
                                    SORTABLE_COLUMNS.maintenance_percentage
                                        ? order
                                        : 'asc'
                                }
                                onClick={() =>
                                    handleSort(
                                        SORTABLE_COLUMNS.maintenance_percentage
                                    )
                                }
                            >
                                Percentage
                            </TableSortLabel>
                        </TableCell>
                    </TableRow>
                </TableHead>

                <TableBody>
                    {sortedFlags.map((row) => (
                        <TableRow key={row.hospital_id}>
                            <TableCell>
                                {row.hospital_id}
                            </TableCell>

                            <TableCell>
                                {row.hospital_name}
                            </TableCell>

                            <TableCell align="right">
                                {row.total_equipments}
                            </TableCell>

                            <TableCell align="right">
                                {row.maintenance_count}
                            </TableCell>

                            <TableCell align="right">
                                {Number(
                                    row.maintenance_percentage
                                ).toFixed(2)}%
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
}
