import React from 'react';
import { motion } from 'framer-motion';
import { Menu, Sun, Moon, Monitor, LogOut, User } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { useThemeStore } from '../../store/themeStore';
import { useActivityStore } from '../../store/activityStore';

interface HeaderProps {
  onMenuClick: () => void;
}

const Header: React.FC<HeaderProps> = ({ onMenuClick }) => {
  const { user, logout } = useAuthStore();
  const { theme, setTheme } = useThemeStore();
  const { isConnected, systemStatus } = useActivityStore();

  const handleLogout = async () => {
    try {
      await logout();
    } catch (error) {
      console.error('Logout error:', error);
    }
  };

  const getThemeIcon = () => {
    switch (theme) {
      case 'light':
        return <Sun className="h-4 w-4" />;
      case 'dark':
        return <Moon className="h-4 w-4" />;
      default:
        return <Monitor className="h-4 w-4" />;
    }
  };

  const cycleTheme = () => {
    const themes: Array<'light' | 'dark' | 'system'> = ['light', 'dark', 'system'];
    const currentIndex = themes.indexOf(theme);
    const nextIndex = (currentIndex + 1) % themes.length;
    setTheme(themes[nextIndex]);
  };

  return (
    <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 h-16">
      <div className="flex items-center justify-between h-full px-6">
        {/* Left Side */}
        <div className="flex items-center space-x-4">
          <button
            onClick={onMenuClick}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors lg:hidden"
          >
            <Menu className="h-5 w-5" />
          </button>

          <div className="flex items-center space-x-3">
            <div className="h-8 w-8 bg-primary-600 rounded-lg flex items-center justify-center">
              <span className="text-white font-bold text-sm">M</span>
            </div>
            <h1 className="text-xl font-semibold text-gray-900 dark:text-white hidden sm:block">
              Maia
            </h1>
          </div>
        </div>

        {/* Center - Status Indicator */}
        <div className="hidden md:flex items-center space-x-2">
          <motion.div
            animate={{
              scale: isConnected ? [1, 1.2, 1] : 1,
            }}
            transition={{
              duration: 2,
              repeat: isConnected ? Infinity : 0,
            }}
            className={`h-2 w-2 rounded-full ${
              isConnected ? 'bg-green-500' : 'bg-red-500'
            }`}
          />
          <span className="text-sm text-gray-600 dark:text-gray-400">
            {isConnected ? 'Connected' : 'Disconnected'}
          </span>
          
          {systemStatus?.is_processing && (
            <motion.div
              animate={{ opacity: [0.5, 1, 0.5] }}
              transition={{ duration: 1.5, repeat: Infinity }}
              className="ml-4 flex items-center space-x-2"
            >
              <div className="h-2 w-2 bg-blue-500 rounded-full" />
              <span className="text-sm text-blue-600 dark:text-blue-400">
                Processing
              </span>
            </motion.div>
          )}
        </div>

        {/* Right Side */}
        <div className="flex items-center space-x-2">
          {/* Theme Toggle */}
          <button
            onClick={cycleTheme}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
            title={`Current theme: ${theme}`}
          >
            {getThemeIcon()}
          </button>

          {/* User Menu */}
          <div className="flex items-center space-x-3 ml-4">
            <div className="hidden sm:block text-right">
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {user?.name || 'User'}
              </p>
              <p className="text-xs text-gray-500 dark:text-gray-400">
                {user?.email}
              </p>
            </div>

            <div className="h-8 w-8 bg-gray-300 dark:bg-gray-600 rounded-full flex items-center justify-center">
              <User className="h-4 w-4 text-gray-600 dark:text-gray-300" />
            </div>

            <button
              onClick={handleLogout}
              className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
              title="Logout"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>
    </header>
  );
};

export default Header;