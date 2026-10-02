import { useEffect, useState } from 'react';
import {
  Alert,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import apiClient from '../../api/client.js';

function MaintenanceFlags() {
  const [flags, setFlags] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchFlags() {
      try {
        const response = await apiClient.get('/hospitals/maintenance-flags');
        setFlags(response.data);
      } catch {
        setError('Could not load maintenance flags.');
      } finally {
        setLoading(false);
      }
    }
    fetchFlags();
  }, []);

  if (loading) return <CircularProgress />;
  if (error) return <Alert severity="error">{error}</Alert>;
  if (flags.length === 0) {
    return <Typography>No hospitals currently over the 30% maintenance threshold.</Typography>;
  }

  return (
    <TableContainer sx={{backgroundColor: 'white', borderRadius: 2}}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Hospital</TableCell>
            <TableCell align="right">Total Equipments</TableCell>
            <TableCell align="right">In Maintenance</TableCell>
            <TableCell align="right">Percentage</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {flags.map((row) => (
            <TableRow key={row.hospital_id}>
              <TableCell>{row.hospital_name}</TableCell>
              <TableCell align="right">{row.total_equipments}</TableCell>
              <TableCell align="right">{row.maintenance_count}</TableCell>
              <TableCell align="right">{row.maintenance_percentage}%</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  );
}

export default MaintenanceFlags;