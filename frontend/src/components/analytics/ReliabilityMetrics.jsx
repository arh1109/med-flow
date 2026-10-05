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
    total_work_orders: 'total_work_orders',
    completed_count: 'completed_count',
    failed_count: 'failed_count',
    completed_failed_ratio: 'completed_failed_ratio',
};


function getCompletedFailedRatio(row) {
    const completed = Number(row.completed_count);
    const failed = Number(row.failed_count);

    if (failed === 0) {
        // Treat zero failures as an infinitely strong completed:failed ratio.
        // Keeping Infinity internally also makes descending sort intuitive.
        return completed > 0 ? Infinity : 0;
    }

    return completed / failed;
}


function formatRatio(row) {
    const ratio = getCompletedFailedRatio(row);

    if (ratio === Infinity) {
        return '∞';
    }

    return ratio.toFixed(2);
}


export default function ReliabilityMetrics() {
    const [metrics, setMetrics] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const [orderBy, setOrderBy] = useState('total_work_orders');
    const [order, setOrder] = useState('desc');


    useEffect(() => {
        async function fetchMetrics() {
            try {
                setLoading(true);

                const response = await apiClient.get(
                    '/work_orders/reliability'
                );

                setMetrics(response.data);
                setError(null);
            } catch (err) {
                console.error(err);

                setError(
                    err.response?.data?.detail ||
                    'Could not load reliability metrics'
                );
            } finally {
                setLoading(false);
            }
        }

        fetchMetrics();
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


    const sortedMetrics = useMemo(() => {
        const rows = [...metrics];

        rows.sort((a, b) => {
            let aValue;
            let bValue;

            if (
                orderBy ===
                SORTABLE_COLUMNS.completed_failed_ratio
            ) {
                aValue = getCompletedFailedRatio(a);
                bValue = getCompletedFailedRatio(b);
            } else {
                aValue = Number(a[orderBy]);
                bValue = Number(b[orderBy]);
            }

            if (aValue < bValue) {
                return order === 'asc' ? -1 : 1;
            }

            if (aValue > bValue) {
                return order === 'asc' ? 1 : -1;
            }

            return 0;
        });

        return rows;
    }, [metrics, order, orderBy]);


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
                            Equipment Model
                        </TableCell>

                        <TableCell align="right">
                            <TableSortLabel
                                active={
                                    orderBy ===
                                    SORTABLE_COLUMNS.total_work_orders
                                }
                                direction={
                                    orderBy ===
                                    SORTABLE_COLUMNS.total_work_orders
                                        ? order
                                        : 'asc'
                                }
                                onClick={() =>
                                    handleSort(
                                        SORTABLE_COLUMNS.total_work_orders
                                    )
                                }
                            >
                                Total Work Orders
                            </TableSortLabel>
                        </TableCell>

                        <TableCell align="right">
                            <TableSortLabel
                                active={
                                    orderBy ===
                                    SORTABLE_COLUMNS.completed_count
                                }
                                direction={
                                    orderBy ===
                                    SORTABLE_COLUMNS.completed_count
                                        ? order
                                        : 'asc'
                                }
                                onClick={() =>
                                    handleSort(
                                        SORTABLE_COLUMNS.completed_count
                                    )
                                }
                            >
                                Completed
                            </TableSortLabel>
                        </TableCell>

                        <TableCell align="right">
                            <TableSortLabel
                                active={
                                    orderBy ===
                                    SORTABLE_COLUMNS.failed_count
                                }
                                direction={
                                    orderBy ===
                                    SORTABLE_COLUMNS.failed_count
                                        ? order
                                        : 'asc'
                                }
                                onClick={() =>
                                    handleSort(
                                        SORTABLE_COLUMNS.failed_count
                                    )
                                }
                            >
                                Failed
                            </TableSortLabel>
                        </TableCell>

                        <TableCell align="right">
                            <TableSortLabel
                                active={
                                    orderBy ===
                                    SORTABLE_COLUMNS.completed_failed_ratio
                                }
                                direction={
                                    orderBy ===
                                    SORTABLE_COLUMNS.completed_failed_ratio
                                        ? order
                                        : 'asc'
                                }
                                onClick={() =>
                                    handleSort(
                                        SORTABLE_COLUMNS.completed_failed_ratio
                                    )
                                }
                            >
                                Completed / Failed Ratio
                            </TableSortLabel>
                        </TableCell>
                    </TableRow>
                </TableHead>

                <TableBody>
                    {sortedMetrics.map((row) => (
                        <TableRow key={row.model}>
                            <TableCell>
                                {row.model}
                            </TableCell>

                            <TableCell align="right">
                                {row.total_work_orders}
                            </TableCell>

                            <TableCell align="right">
                                {row.completed_count}
                            </TableCell>

                            <TableCell align="right">
                                {row.failed_count}
                            </TableCell>

                            <TableCell align="right">
                                {formatRatio(row)}
                            </TableCell>
                        </TableRow>
                    ))}
                </TableBody>
            </Table>
        </TableContainer>
    );
}
