import { createTheme } from "@mui/material/styles";

const theme = createTheme({
	palette: {
		primary: {
			main: "#1976d2", // Default MUI primary color
		},
		secondary: {
			main: "#dc004e", // Default MUI secondary color
		},
	},
	typography: {
		fontFamily: '"Roboto", "Helvetica", "Arial", sans-serif', // MUI's default font
	},
});

export default theme;
