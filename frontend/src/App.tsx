import {
	BrowserRouter as Router,
	Routes,
	Route,
	Navigate,
} from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import AuthCallbackPage from "./pages/AuthCallbackPage";
import { AuthProvider, useAuth } from "./auth/AuthContext";
import type {  ReactElement } from "react";


const ProtectedRoute = ({ children }: { children: ReactElement }) => {
	const { user } = useAuth();
	return user ? children : <Navigate to='/login' replace />;
};

const App = () => {
	return (
		<AuthProvider>
			<Router>
				<Routes>
					<Route path='/login' element={<LoginPage />} />
					<Route path='/auth/callback' element={<AuthCallbackPage />} />
					<Route
						path='/dashboard'
						element={
							<ProtectedRoute>
								<DashboardPage />
							</ProtectedRoute>
						}
					/>
					<Route path='*' element={<Navigate to='/login' replace />} />
				</Routes>
			</Router>
		</AuthProvider>
	);
};

export default App;
