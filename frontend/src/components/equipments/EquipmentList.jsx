import {Grid} from '@mui/material';
import EquipmentCard from './EquipmentCard.jsx';

function EquipmentList({equipments}) {
    return (
        <Grid container spacing = {2}>
            {/**
             * The map function is used to iterate over the 'equipments' array and render
             * a EquipmentCard component for each equipments
             */}
             {equipments.map((equipment)=> (
            <Grid item key={equipment.id}>
                <EquipmentCard equipment={equipment} />
            </Grid>
        ))}
        </Grid>
    );
}

export default EquipmentList;