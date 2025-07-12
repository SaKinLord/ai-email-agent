import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Mail, Brain, Zap } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { apiService } from '../../services/api';
import LoadingSpinner from '../common/LoadingSpinner';

const LoginPage: React.FC = () => {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const { login } = useAuthStore();

  const handleGoogleSignIn = async () => {
    setIsLoading(true);
    setError(null);

    try {
      // Start Google OAuth flow
      const { authorization_url, state } = await apiService.googleSignIn();
      
      // Store state for verification
      sessionStorage.setItem('oauth_state', state);
      
      // Redirect to Google OAuth
      window.location.href = authorization_url;
      
    } catch (err: any) {
      setError(err.message || 'Authentication failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-blue-50 to-indigo-100 dark:from-gray-900 dark:to-gray-800 px-4">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-md w-full space-y-8"
      >
        <div className="text-center">
          <motion.div
            initial={{ scale: 0.5 }}
            animate={{ scale: 1 }}
            transition={{ duration: 0.5, delay: 0.2 }}
            className="mx-auto h-16 w-16 bg-primary-600 rounded-full flex items-center justify-center mb-4"
          >
            <Mail className="h-8 w-8 text-white" />
          </motion.div>
          
          <motion.h2
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.3 }}
            className="text-3xl font-bold text-gray-900 dark:text-white"
          >
            Welcome to Maia
          </motion.h2>
          
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.4 }}
            className="mt-2 text-sm text-gray-600 dark:text-gray-400"
          >
            Your intelligent email assistant
          </motion.p>
        </div>

        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.5 }}
          className="card space-y-6"
        >
          {/* Features */}
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <Brain className="h-5 w-5 text-primary-600" />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                AI-powered email analysis and prioritization
              </span>
            </div>
            
            <div className="flex items-center space-x-3">
              <Zap className="h-5 w-5 text-primary-600" />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Real-time processing and autonomous actions
              </span>
            </div>
            
            <div className="flex items-center space-x-3">
              <Mail className="h-5 w-5 text-primary-600" />
              <span className="text-sm text-gray-700 dark:text-gray-300">
                Smart suggestions and workflow automation
              </span>
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-md p-3"
            >
              <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
            </motion.div>
          )}

          {/* Sign In Button */}
          <button
            onClick={handleGoogleSignIn}
            disabled={isLoading}
            className="w-full btn-primary flex items-center justify-center space-x-2 py-3"
          >
            {isLoading ? (
              <>
                <LoadingSpinner size="sm" />
                <span>Connecting...</span>
              </>
            ) : (
              <>
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path
                    fill="currentColor"
                    d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
                  />
                  <path
                    fill="currentColor"
                    d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
                  />
                  <path
                    fill="currentColor"
                    d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
                  />
                </svg>
                <span>Sign in with Google</span>
              </>
            )}
          </button>

          <div className="text-center">
            <p className="text-xs text-gray-500 dark:text-gray-400">
              By signing in, you agree to our terms of service and privacy policy
            </p>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
};

export default LoginPage;