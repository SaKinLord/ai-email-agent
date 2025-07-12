import React, { ReactNode } from 'react';
import { motion } from 'framer-motion';
import { AlertCircle, Info, Plus, X } from 'lucide-react';

// Base form group component
interface FormGroupProps {
  label: string;
  description?: string;
  error?: string;
  required?: boolean;
  children: ReactNode;
  className?: string;
}

export const FormGroup: React.FC<FormGroupProps> = ({
  label,
  description,
  error,
  required = false,
  children,
  className = ''
}) => {
  return (
    <div className={`space-y-2 ${className}`}>
      <label className="block text-sm font-medium text-gray-700 dark:text-gray-300">
        {label}
        {required && <span className="text-red-500 ml-1">*</span>}
      </label>
      
      {description && (
        <p className="text-xs text-gray-600 dark:text-gray-400 flex items-start space-x-1">
          <Info className="h-3 w-3 mt-0.5 flex-shrink-0 text-blue-500 dark:text-blue-400" />
          <span>{description}</span>
        </p>
      )}
      
      {children}
      
      {error && (
        <motion.div
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex items-center space-x-1 text-red-600 dark:text-red-400"
        >
          <AlertCircle className="h-3 w-3" />
          <p className="text-xs">{error}</p>
        </motion.div>
      )}
    </div>
  );
};

// Text input component
interface TextInputProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  type?: 'text' | 'email' | 'password' | 'url';
  disabled?: boolean;
  className?: string;
}

export const TextInput: React.FC<TextInputProps> = ({
  value,
  onChange,
  placeholder,
  type = 'text',
  disabled = false,
  className = ''
}) => {
  return (
    <input
      type={type}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm placeholder-gray-400 dark:placeholder-gray-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
    />
  );
};

// Number input component
interface NumberInputProps {
  value: number;
  onChange: (value: number) => void;
  min?: number;
  max?: number;
  step?: number;
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export const NumberInput: React.FC<NumberInputProps> = ({
  value,
  onChange,
  min,
  max,
  step = 1,
  placeholder,
  disabled = false,
  className = ''
}) => {
  return (
    <input
      type="number"
      value={value}
      onChange={(e) => onChange(Number(e.target.value))}
      min={min}
      max={max}
      step={step}
      placeholder={placeholder}
      disabled={disabled}
      className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm placeholder-gray-400 dark:placeholder-gray-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
    />
  );
};

// Select component
interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
}

interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: SelectOption[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export const Select: React.FC<SelectProps> = ({
  value,
  onChange,
  options,
  placeholder,
  disabled = false,
  className = ''
}) => {
  return (
    <select
      value={value}
      onChange={(e) => onChange(e.target.value)}
      disabled={disabled}
      className={`w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed ${className}`}
    >
      {placeholder && (
        <option value="" disabled>
          {placeholder}
        </option>
      )}
      {options.map((option) => (
        <option
          key={option.value}
          value={option.value}
          disabled={option.disabled}
        >
          {option.label}
        </option>
      ))}
    </select>
  );
};

// Switch/Toggle component
interface SwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
  disabled?: boolean;
  size?: 'sm' | 'md' | 'lg';
  className?: string;
}

export const Switch: React.FC<SwitchProps> = ({
  checked,
  onChange,
  disabled = false,
  size = 'md',
  className = ''
}) => {
  const sizeClasses = {
    sm: 'h-4 w-7',
    md: 'h-5 w-9',
    lg: 'h-6 w-11'
  };
  
  const thumbSizeClasses = {
    sm: 'h-3 w-3',
    md: 'h-4 w-4',
    lg: 'h-5 w-5'
  };
  
  return (
    <button
      type="button"
      onClick={() => onChange(!checked)}
      disabled={disabled}
      className={`${sizeClasses[size]} relative inline-flex items-center rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed border ${
        checked
          ? 'bg-blue-600 border-blue-600'
          : 'bg-gray-200 dark:bg-gray-600 border-gray-300 dark:border-gray-600'
      } ${className}`}
    >
      <motion.span
        animate={{
          x: checked ? (size === 'sm' ? 12 : size === 'md' ? 16 : 20) : 2
        }}
        transition={{ duration: 0.2, ease: 'easeInOut' }}
        className={`${thumbSizeClasses[size]} absolute bg-white rounded-full shadow-lg`}
      />
    </button>
  );
};

// Slider component
interface SliderProps {
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  disabled?: boolean;
  showValue?: boolean;
  formatValue?: (value: number) => string;
  className?: string;
}

export const Slider: React.FC<SliderProps> = ({
  value,
  onChange,
  min,
  max,
  step = 1,
  disabled = false,
  showValue = true,
  formatValue = (val) => val.toString(),
  className = ''
}) => {
  return (
    <div className={`space-y-2 ${className}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-600 dark:text-gray-400">{min}</span>
        {showValue && (
          <span className="text-sm font-medium text-gray-800 dark:text-gray-300">
            {formatValue(value)}
          </span>
        )}
        <span className="text-xs text-gray-600 dark:text-gray-400">{max}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        disabled={disabled}
        className="w-full h-2 bg-gray-200 dark:bg-gray-600 rounded-lg appearance-none cursor-pointer slider [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-blue-600 [&::-webkit-slider-thumb]:cursor-pointer [&::-webkit-slider-thumb]:shadow-lg [&::-moz-range-thumb]:h-4 [&::-moz-range-thumb]:w-4 [&::-moz-range-thumb]:rounded-full [&::-moz-range-thumb]:bg-blue-600 [&::-moz-range-thumb]:cursor-pointer [&::-moz-range-thumb]:border-none [&::-moz-range-thumb]:shadow-lg"
        style={{
          background: `linear-gradient(to right, #3B82F6 0%, #3B82F6 ${((value - min) / (max - min)) * 100}%, #E5E7EB ${((value - min) / (max - min)) * 100}%, #E5E7EB 100%)`
        }}
      />
    </div>
  );
};

// Array input component (for lists of strings)
interface ArrayInputProps {
  values: string[];
  onChange: (values: string[]) => void;
  placeholder?: string;
  addButtonText?: string;
  disabled?: boolean;
  maxItems?: number;
  className?: string;
}

export const ArrayInput: React.FC<ArrayInputProps> = ({
  values,
  onChange,
  placeholder = "Enter value...",
  addButtonText = "Add",
  disabled = false,
  maxItems,
  className = ''
}) => {
  const [inputValue, setInputValue] = React.useState('');
  
  const addItem = () => {
    if (inputValue.trim() && (!maxItems || values.length < maxItems)) {
      onChange([...values, inputValue.trim()]);
      setInputValue('');
    }
  };
  
  const removeItem = (index: number) => {
    onChange(values.filter((_, i) => i !== index));
  };
  
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      addItem();
    }
  };
  
  return (
    <div className={`space-y-3 ${className}`}>
      {/* Input section */}
      <div className="flex space-x-2">
        <input
          type="text"
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder={placeholder}
          disabled={disabled || (maxItems ? values.length >= maxItems : false)}
          className="flex-1 px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm text-sm placeholder-gray-400 dark:placeholder-gray-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        />
        <button
          type="button"
          onClick={addItem}
          disabled={!inputValue.trim() || disabled || (maxItems ? values.length >= maxItems : false)}
          className="px-3 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed flex items-center space-x-1"
        >
          <Plus className="h-4 w-4" />
          <span className="text-sm">{addButtonText}</span>
        </button>
      </div>
      
      {/* Items list */}
      {values.length > 0 && (
        <div className="space-y-2">
          {values.map((value, index) => (
            <motion.div
              key={index}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="flex items-center justify-between p-2 bg-gray-50 dark:bg-gray-700/50 rounded-md"
            >
              <span className="text-sm text-gray-800 dark:text-gray-300 flex-1 mr-2">
                {value}
              </span>
              <button
                type="button"
                onClick={() => removeItem(index)}
                disabled={disabled}
                className="p-1 text-gray-500 hover:text-red-600 dark:text-gray-400 dark:hover:text-red-400 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <X className="h-3 w-3" />
              </button>
            </motion.div>
          ))}
        </div>
      )}
      
      {maxItems && (
        <p className="text-xs text-gray-600 dark:text-gray-400">
          {values.length} / {maxItems} items
        </p>
      )}
    </div>
  );
};

// Confidence threshold component (specialized for confidence values)
interface ConfidenceInputProps {
  value: number;
  onChange: (value: number) => void;
  disabled?: boolean;
  className?: string;
}

export const ConfidenceInput: React.FC<ConfidenceInputProps> = ({
  value,
  onChange,
  disabled = false,
  className = ''
}) => {
  return (
    <Slider
      value={value}
      onChange={onChange}
      min={0}
      max={100}
      step={1}
      disabled={disabled}
      formatValue={(val) => `${val}%`}
      className={className}
    />
  );
};