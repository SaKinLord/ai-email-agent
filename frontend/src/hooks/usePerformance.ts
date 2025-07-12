import { useCallback, useEffect, useRef, useMemo } from 'react';

/**
 * Custom hook for throttling functions to improve performance
 */
export const useThrottle = <T extends (...args: any[]) => any>(
  func: T,
  delay: number
): T => {
  const lastExecution = useRef<number>(0);
  const timeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

  return useCallback(
    ((...args: Parameters<T>) => {
      const now = Date.now();
      
      if (now - lastExecution.current >= delay) {
        func(...args);
        lastExecution.current = now;
      } else {
        if (timeoutRef.current) {
          clearTimeout(timeoutRef.current);
        }
        
        timeoutRef.current = setTimeout(() => {
          func(...args);
          lastExecution.current = Date.now();
        }, delay - (now - lastExecution.current));
      }
    }) as T,
    [func, delay]
  );
};

/**
 * Custom hook for debouncing functions to reduce unnecessary calls
 */
export const useDebounce = <T extends (...args: any[]) => any>(
  func: T,
  delay: number
): T => {
  const timeoutRef = useRef<NodeJS.Timeout | undefined>(undefined);

  return useCallback(
    ((...args: Parameters<T>) => {
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      
      timeoutRef.current = setTimeout(() => {
        func(...args);
      }, delay);
    }) as T,
    [func, delay]
  );
};

/**
 * Custom hook for animation frame throttling for smooth animations
 */
export const useAnimationFrame = <T extends (...args: any[]) => any>(
  func: T
): T => {
  const requestRef = useRef<number | undefined>(undefined);

  return useCallback(
    ((...args: Parameters<T>) => {
      if (requestRef.current) {
        cancelAnimationFrame(requestRef.current);
      }
      
      requestRef.current = requestAnimationFrame(() => {
        func(...args);
      });
    }) as T,
    [func]
  );
};

/**
 * Custom hook for memoizing expensive computations with dependencies
 */
export const useExpensiveMemo = <T>(
  computeValue: () => T,
  deps: React.DependencyList,
  shouldUpdate?: (newDeps: React.DependencyList, oldDeps: React.DependencyList) => boolean
): T => {
  const oldDepsRef = useRef<React.DependencyList | undefined>(undefined);
  
  return useMemo(() => {
    if (shouldUpdate && oldDepsRef.current) {
      const shouldRecompute = shouldUpdate(deps, oldDepsRef.current);
      oldDepsRef.current = deps;
      if (!shouldRecompute) {
        return computeValue();
      }
    }
    
    oldDepsRef.current = deps;
    return computeValue();
  }, [computeValue, shouldUpdate, ...deps]);
};

/**
 * Custom hook for intersection observer to optimize rendering of off-screen elements
 */
export const useIntersectionObserver = (
  elementRef: React.RefObject<Element>,
  options: IntersectionObserverInit = { rootMargin: '50px' }
) => {
  const isIntersecting = useRef<boolean>(false);
  const observerRef = useRef<IntersectionObserver | undefined>(undefined);

  useEffect(() => {
    const element = elementRef.current;
    if (!element) return;

    observerRef.current = new IntersectionObserver(([entry]) => {
      isIntersecting.current = entry.isIntersecting;
    }, options);

    observerRef.current.observe(element);

    return () => {
      if (observerRef.current) {
        observerRef.current.disconnect();
      }
    };
  }, [options]); // Removed elementRef from deps as it's a ref

  return isIntersecting.current;
};

/**
 * Custom hook for throttled resize events
 */
export const useThrottledResize = (callback: () => void, delay: number = 100) => {
  const throttledCallback = useThrottle(callback, delay);

  useEffect(() => {
    window.addEventListener('resize', throttledCallback);
    return () => window.removeEventListener('resize', throttledCallback);
  }, [throttledCallback]);
};

/**
 * Custom hook for optimized scroll events
 */
export const useOptimizedScroll = (
  callback: (scrollY: number) => void,
  delay: number = 16 // ~60fps
) => {
  const throttledCallback = useAnimationFrame(
    useThrottle(() => {
      callback(window.scrollY);
    }, delay)
  );

  useEffect(() => {
    window.addEventListener('scroll', throttledCallback, { passive: true });
    return () => window.removeEventListener('scroll', throttledCallback);
  }, [throttledCallback]);
};