import React, { ReactNode } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight } from 'lucide-react';

interface CollapsibleCardProps {
  title: string;
  subtitle?: string;
  icon?: ReactNode;
  isExpanded: boolean;
  onToggle: () => void;
  children: ReactNode;
  className?: string;
  disabled?: boolean;
  badge?: string | number;
  variant?: 'default' | 'warning' | 'success' | 'danger';
}

const variantStyles = {
  default: 'border-gray-200 dark:border-gray-700',
  warning: 'border-yellow-200 dark:border-yellow-700 bg-yellow-50/50 dark:bg-yellow-900/10',
  success: 'border-green-200 dark:border-green-700 bg-green-50/50 dark:bg-green-900/10',
  danger: 'border-red-200 dark:border-red-700 bg-red-50/50 dark:bg-red-900/10'
};

const CollapsibleCard: React.FC<CollapsibleCardProps> = ({
  title,
  subtitle,
  icon,
  isExpanded,
  onToggle,
  children,
  className = '',
  disabled = false,
  badge,
  variant = 'default'
}) => {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`border rounded-lg overflow-hidden ${variantStyles[variant]} ${className}`}
    >
      {/* Header */}
      <motion.button
        onClick={onToggle}
        disabled={disabled}
        className={`w-full px-4 py-3 text-left flex items-center justify-between hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors ${
          disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'
        }`}
        whileHover={disabled ? {} : { backgroundColor: 'rgba(0, 0, 0, 0.02)' }}
        whileTap={disabled ? {} : { scale: 0.995 }}
      >
        <div className="flex items-center space-x-3 flex-1">
          {icon && (
            <motion.div
              animate={{ rotate: isExpanded ? 360 : 0 }}
              transition={{ duration: 0.3 }}
              className="text-gray-600 dark:text-gray-400"
            >
              {icon}
            </motion.div>
          )}
          
          <div className="flex-1">
            <div className="flex items-center space-x-2">
              <h3 className="font-medium text-gray-900 dark:text-white">
                {title}
              </h3>
              {badge && (
                <motion.span
                  initial={{ scale: 0 }}
                  animate={{ scale: 1 }}
                  className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400"
                >
                  {badge}
                </motion.span>
              )}
            </div>
            {subtitle && (
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                {subtitle}
              </p>
            )}
          </div>
        </div>
        
        <motion.div
          animate={{ rotate: isExpanded ? 90 : 0 }}
          transition={{ duration: 0.2, ease: 'easeInOut' }}
          className="text-gray-400 dark:text-gray-500"
        >
          <ChevronRight className="h-4 w-4" />
        </motion.div>
      </motion.button>
      
      {/* Content */}
      <AnimatePresence initial={false}>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{
              height: { duration: 0.3, ease: 'easeInOut' },
              opacity: { duration: 0.2, ease: 'easeInOut' }
            }}
            className="overflow-hidden"
          >
            <div className="px-4 pb-4 border-t border-gray-100 dark:border-gray-700/50">
              <motion.div
                initial={{ y: -10, opacity: 0 }}
                animate={{ y: 0, opacity: 1 }}
                exit={{ y: -10, opacity: 0 }}
                transition={{ delay: 0.1, duration: 0.2 }}
                className="pt-4"
              >
                {children}
              </motion.div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
};

export default CollapsibleCard;