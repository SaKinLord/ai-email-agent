import React, { useEffect, useState, useCallback } from 'react';
import { Routes, Route } from 'react-router-dom';
import { motion } from 'framer-motion';

// Components
import Header from './Header';
import Sidebar from './Sidebar';
import { 
  MemoizedDashboardHome,
  MemoizedActivityFeed,
  MemoizedEmailList,
  MemoizedSettings,
  MemoizedAutonomous,
  MemoizedChat
} from './MemoizedComponents';

// Store
import { useEmailStore } from '../../store/emailStore';
import { useActivityStore } from '../../store/activityStore';
import { apiService } from '../../services/api';

const Dashboard: React.FC = () => {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const { setDashboardData, setLoading, setError } = useEmailStore();
  const { isConnected } = useActivityStore();

  const loadDashboardData = useCallback(async () => {
    try {
      setLoading(true);
      const data = await apiService.getDashboardOverview();
      setDashboardData(data);
      setError(null); // Clear any previous errors
    } catch (error: any) {
      console.error('Dashboard: Failed to load data:', error.message);
      setError(error.message);
      // Don't auto-logout on dashboard data fetch failures
      // The API service handles auth failures appropriately for critical endpoints
    } finally {
      setLoading(false);
    }
  }, [setDashboardData, setLoading, setError]);

  useEffect(() => {
    // Load initial dashboard data
    loadDashboardData();
  }, [loadDashboardData]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* Header */}
      <Header onMenuClick={() => setSidebarOpen(!sidebarOpen)} />

      <div className="flex h-[calc(100vh-4rem)]">
        {/* Sidebar */}
        <Sidebar isOpen={sidebarOpen} onClose={() => setSidebarOpen(false)} />

        {/* Main Content */}
        <main className="flex-1 overflow-auto">
          <div className="p-6">
            {/* Connection Status */}
            {!isConnected && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                className="mb-4 bg-warning-50 dark:bg-warning-900/20 border border-warning-200 dark:border-warning-800 rounded-lg p-3"
              >
                <p className="text-sm text-warning-700 dark:text-warning-300">
                  Real-time connection lost. Attempting to reconnect...
                </p>
              </motion.div>
            )}

            {/* Routes */}
            <Routes>
              <Route path="/" element={<MemoizedDashboardHome />} />
              <Route path="/activity" element={<MemoizedActivityFeed />} />
              <Route path="/emails" element={<MemoizedEmailList />} />
              <Route path="/chat" element={<MemoizedChat />} />
              <Route path="/autonomous" element={<MemoizedAutonomous />} />
              <Route path="/settings" element={<MemoizedSettings />} />
            </Routes>
          </div>
        </main>
      </div>
    </div>
  );
};

export default Dashboard;