import React, { useEffect, useState, useRef } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { motion } from 'framer-motion';
import { CheckCircle, AlertCircle, Mail } from 'lucide-react';
import { useAuthStore } from '../../store/authStore';
import { apiService } from '../../services/api';
import LoadingSpinner from '../common/LoadingSpinner';

const OAuthCallback: React.FC = () => {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { login } = useAuthStore();
  const [status, setStatus] = useState<'loading' | 'success' | 'error'>('loading');
  const [message, setMessage] = useState('Processing authentication...');
  const hasProcessed = useRef(false);

  useEffect(() => {
    // Prevent double execution in React StrictMode
    if (hasProcessed.current) {
      return;
    }
    hasProcessed.current = true;
    const handleCallback = async () => {
      try {
        const code = searchParams.get('code');
        const state = searchParams.get('state');
        const error = searchParams.get('error');

        // Check for OAuth errors
        if (error) {
          setStatus('error');
          setMessage(`Authentication failed: ${error}`);
          return;
        }

        if (!code || !state) {
          setStatus('error');
          setMessage('Missing authentication parameters');
          return;
        }

        // Verify state matches what we stored
        const storedState = sessionStorage.getItem('oauth_state');
        if (state !== storedState) {
          setStatus('error');
          setMessage('Invalid authentication state');
          return;
        }

        // Exchange code for tokens
        setMessage('Exchanging authorization code...');
        const { token, user } = await apiService.authCallback(code, state);

        // Store authentication
        login(token, user);

        // Clean up
        sessionStorage.removeItem('oauth_state');

        setStatus('success');
        setMessage('Authentication successful! Redirecting...');

        // Redirect to dashboard after a brief delay
        setTimeout(() => {
          navigate('/dashboard');
        }, 1500);

      } catch (error: any) {
        console.error('OAuth callback error:', error);
        setStatus('error');
        setMessage(error.message || 'Authentication failed');
        
        // Redirect to login after error
        setTimeout(() => {
          navigate('/login');
        }, 3000);
      }
    };

    handleCallback();
  }, [searchParams, navigate, login]);

  const getIcon = () => {
    switch (status) {
      case 'success':
        return <CheckCircle className="h-12 w-12 text-green-500" />;
      case 'error':
        return <AlertCircle className="h-12 w-12 text-red-500" />;
      default:
        return <Mail className="h-12 w-12 text-blue-500" />;
    }
  };

  const getColors = () => {
    switch (status) {
      case 'success':
        return 'from-green-50 to-emerald-100 dark:from-green-900 dark:to-emerald-800';
      case 'error':
        return 'from-red-50 to-rose-100 dark:from-red-900 dark:to-rose-800';
      default:
        return 'from-blue-50 to-indigo-100 dark:from-blue-900 dark:to-indigo-800';
    }
  };

  return (
    <div className={`min-h-screen flex items-center justify-center bg-gradient-to-br ${getColors()} px-4`}>
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.5 }}
        className="max-w-md w-full text-center"
      >
        <div className="card space-y-6">
          <motion.div
            animate={status === 'loading' ? { scale: [1, 1.1, 1] } : {}}
            transition={{ duration: 2, repeat: status === 'loading' ? Infinity : 0 }}
            className="flex justify-center"
          >
            {getIcon()}
          </motion.div>

          <div className="space-y-2">
            <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
              {status === 'loading' && 'Authenticating...'}
              {status === 'success' && 'Welcome to Maia!'}
              {status === 'error' && 'Authentication Failed'}
            </h2>
            
            <p className="text-gray-600 dark:text-gray-400">
              {message}
            </p>
          </div>

          {status === 'loading' && (
            <div className="flex justify-center">
              <LoadingSpinner size="md" />
            </div>
          )}

          {status === 'error' && (
            <motion.button
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 1 }}
              onClick={() => navigate('/login')}
              className="btn-primary"
            >
              Return to Login
            </motion.button>
          )}
        </div>
      </motion.div>
    </div>
  );
};

export default OAuthCallback;