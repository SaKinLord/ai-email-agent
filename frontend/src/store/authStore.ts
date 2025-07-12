import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { websocketService } from '../services/websocket';

interface User {
  id: string;
  email: string;
  name: string;
}

interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  login: (token: string, user: User) => void;
  logout: () => void;
  updateToken: (token: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,
      user: null,
      token: null,
      
      login: (token: string, user: User) => {
        set({
          isAuthenticated: true,
          user,
          token,
        });
        
        // Note: WebSocket connection is now managed centrally by App.tsx useEffect
        // This prevents race conditions during OAuth callback flow
      },
      
      logout: () => {
        // Disconnect WebSocket before logout
        websocketService.disconnect();
        
        // Clear localStorage by resetting state
        set({
          isAuthenticated: false,
          user: null,
          token: null,
        });
        
        // Force clear localStorage (in case persist middleware has any issues)
        localStorage.removeItem('auth-storage');
      },
      
      updateToken: (token: string) => {
        set({ token });
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        user: state.user,
        token: state.token,
      }),
    }
  )
);