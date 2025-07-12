import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { useAuthStore } from './store/authStore';
import { useThemeStore } from './store/themeStore';
import { websocketService } from './services/websocket';

// Components
import LoginPage from './components/auth/LoginPage';
import OAuthCallback from './components/auth/OAuthCallback';
import Dashboard from './components/dashboard/Dashboard';
import ToastContainer from './components/common/ToastContainer';

function App() {
  const { isAuthenticated, token } = useAuthStore();
  const { updateActualTheme } = useThemeStore();

  useEffect(() => {
    // Initialize theme
    updateActualTheme();
  }, [updateActualTheme]);

  // Cleanup WebSocket only on actual app unmount (not Strict Mode fake unmount)
  useEffect(() => {
    return () => {
      // This only runs when the App component actually unmounts (page navigation away)
      websocketService.disconnect();
    };
  }, []); // Empty dependency array - runs only on mount/unmount

  useEffect(() => {
    // Initialize WebSocket connection if user is already authenticated
    if (isAuthenticated && token) {
      // Add small delay to ensure state is fully synchronized after OAuth callback
      const connectTimer = setTimeout(() => {
        websocketService.connect();
        console.log('WebSocket connection initiated for authenticated user');
      }, 100); // Small delay to prevent race conditions during OAuth callback

      return () => clearTimeout(connectTimer);
    } else if (!isAuthenticated) {
      // Ensure WebSocket is disconnected when not authenticated
      websocketService.disconnect();
    }

    // No cleanup function for disconnect - let the singleton service manage its own lifecycle
    // This prevents React Strict Mode from prematurely disconnecting the socket
  }, [isAuthenticated, token]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 transition-colors duration-300">
      <Router>
        <Routes>
          <Route 
            path="/login" 
            element={
              isAuthenticated ? <Navigate to="/dashboard" replace /> : <LoginPage />
            } 
          />
          <Route 
            path="/auth/callback" 
            element={<OAuthCallback />} 
          />
          <Route 
            path="/dashboard/*" 
            element={
              isAuthenticated ? <Dashboard /> : <Navigate to="/login" replace />
            } 
          />
          <Route 
            path="/" 
            element={<Navigate to={isAuthenticated ? "/dashboard" : "/login"} replace />} 
          />
        </Routes>
      </Router>
      
      {/* Toast Notifications */}
      <ToastContainer />
    </div>
  );
}

export default App;