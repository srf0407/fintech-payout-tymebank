import React, { memo } from "react";
import { Navigate } from "react-router-dom";
import { Box, CircularProgress } from "@mui/material";
import { useAuth } from "./auth/AuthContext";

interface ProtectedRouteProps {
  children: React.ReactElement;
}

const ProtectedRoute = memo<ProtectedRouteProps>(({ children }) => {
  const { user, isLoading } = useAuth();
  
  if (isLoading) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
        aria-label="Loading authentication"
      >
        <CircularProgress size={40} />
      </Box>
    );
  }
  
  return user ? children : <Navigate to="/login" replace />;
});

ProtectedRoute.displayName = 'ProtectedRoute';

export default ProtectedRoute;
