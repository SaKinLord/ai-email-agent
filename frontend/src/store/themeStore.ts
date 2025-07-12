import { create } from 'zustand';
import { persist } from 'zustand/middleware';

type Theme = 'light' | 'dark' | 'system';

interface ThemeState {
  theme: Theme;
  actualTheme: 'light' | 'dark';
  setTheme: (theme: Theme) => void;
  updateActualTheme: () => void;
}

const getSystemTheme = (): 'light' | 'dark' => {
  if (typeof window !== 'undefined') {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
  }
  return 'light';
};

const applyTheme = (theme: 'light' | 'dark') => {
  if (typeof document !== 'undefined') {
    if (theme === 'dark') {
      document.documentElement.classList.add('dark');
      document.body.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
      document.body.classList.remove('dark');
    }
  }
};

export const useThemeStore = create<ThemeState>()(
  persist(
    (set, get) => ({
      theme: 'light',
      actualTheme: 'light',
      
      setTheme: (theme: Theme) => {
        set({ theme });
        
        const actualTheme = theme === 'system' ? getSystemTheme() : theme;
        set({ actualTheme });
        applyTheme(actualTheme);
      },
      
      updateActualTheme: () => {
        const { theme } = get();
        const actualTheme = theme === 'system' ? getSystemTheme() : theme;
        set({ actualTheme });
        applyTheme(actualTheme);
      },
    }),
    {
      name: 'theme-storage',
      partialize: (state) => ({ theme: state.theme }),
    }
  )
);

// Initialize theme on store creation
const initializeTheme = () => {
  const { updateActualTheme } = useThemeStore.getState();
  updateActualTheme();
};

// Listen for system theme changes
if (typeof window !== 'undefined') {
  // Initialize theme immediately
  setTimeout(initializeTheme, 0);
  
  // Listen for system theme changes
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    const { theme, updateActualTheme } = useThemeStore.getState();
    if (theme === 'system') {
      updateActualTheme();
    }
  });
}