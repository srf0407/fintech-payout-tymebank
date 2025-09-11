import React from "react";
import { Navigate } from "react-router-dom";
import { useAuth } from "./auth/AuthContext";

const ProtectedRoute: React.FC<{ element: React.ReactElement }> = ({ element }) => {
  const { user, isLoading } = useAuth();
  if (isLoading) return <div>Loading...</div>;
  return user ? element : <Navigate to="/login" replace />;
};

export default ProtectedRoute;
