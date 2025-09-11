import {
	BrowserRouter as Router,
	Routes,
	Route,
	Navigate,
} from "react-router-dom";
import LoginPage from "./pages/LoginPage";
import DashboardPage from "./pages/DashboardPage";
import AuthCallbackPage from "./pages/AuthCallbackPage";
import { AuthProvider } from "./auth/AuthContext";
import ProtectedRoute from "./ProtectedRoute";
import ErrorBoundary from "./components/common/ErrorBoundary";

const App = () => {
	return (
		<ErrorBoundary>
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
		</ErrorBoundary>
	);
};

export default App;
