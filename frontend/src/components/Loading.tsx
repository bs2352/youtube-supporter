// import { styled } from '@mui/material/styles'
import { CircularProgress, Box } from '@mui/material';

// const SpinCircle = styled(
//     () => {
//         return (
//             <div
//                 style={{
//                     display: 'inline-block', width: '30px', height: '30px',
//                     margin: '30px', verticalAlign: 'middle',
//                     border: '5px solid', borderRadius: '50%', borderColor: 'red blue green orange',
//                     animation: 'spin-circle 1s infinite linear',
//                 }}
//             />
//         );
//     }
// )({
//     '@keyframes spin-circle': {
//         from: {
//             transform: "rotate(0deg);",
//         },
//         to: {
//             transform: 'rotate(360deg);',
//         }
//     }
// });

interface LoadingProps {
    size?: number | string;
    margin?: number | string;
}

interface circularProgressSxType {
    margin: number | string;
}

const circularProgressSx: circularProgressSxType = {
    margin: "30px",
};

export function Loading(props: LoadingProps) {
    const { size, margin } = props;

    if (margin !== undefined) {
        circularProgressSx.margin = margin;
    } else {
        circularProgressSx.margin = "30px"; // デフォルト
    }

    return (
        // <SpinCircle />
        <Box sx={{ color: 'grey.500' }} >
            <CircularProgress sx={circularProgressSx} color="inherit" size={size} />
        </Box>
    )
}