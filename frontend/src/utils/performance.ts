/**
 * Performance monitoring utilities for the frontend application
 */

// Performance metrics tracking
export class PerformanceTracker {
  private static instance: PerformanceTracker;
  private metrics: Map<string, number[]> = new Map();
  private renderCounts: Map<string, number> = new Map();

  static getInstance(): PerformanceTracker {
    if (!PerformanceTracker.instance) {
      PerformanceTracker.instance = new PerformanceTracker();
    }
    return PerformanceTracker.instance;
  }

  // Track component render performance
  trackRender(componentName: string): void {
    const current = this.renderCounts.get(componentName) || 0;
    this.renderCounts.set(componentName, current + 1);
  }

  // Track timing metrics
  startTiming(operationName: string): () => void {
    const startTime = performance.now();
    
    return () => {
      const endTime = performance.now();
      const duration = endTime - startTime;
      
      const existing = this.metrics.get(operationName) || [];
      existing.push(duration);
      
      // Keep only last 100 measurements
      if (existing.length > 100) {
        existing.shift();
      }
      
      this.metrics.set(operationName, existing);
    };
  }

  // Get performance statistics
  getStats(operationName: string): {
    avg: number;
    min: number;
    max: number;
    count: number;
  } | null {
    const measurements = this.metrics.get(operationName);
    if (!measurements || measurements.length === 0) return null;

    const avg = measurements.reduce((a, b) => a + b, 0) / measurements.length;
    const min = Math.min(...measurements);
    const max = Math.max(...measurements);

    return { avg, min, max, count: measurements.length };
  }

  // Get render counts
  getRenderCount(componentName: string): number {
    return this.renderCounts.get(componentName) || 0;
  }

  // Get all render counts
  getAllRenderCounts(): Record<string, number> {
    return Object.fromEntries(Array.from(this.renderCounts.entries()));
  }

  // Reset metrics
  reset(): void {
    this.metrics.clear();
    this.renderCounts.clear();
  }

  // Log performance summary
  logSummary(): void {
    console.group('🚀 Performance Summary');
    
    console.log('📊 Render Counts:');
    for (const [component, count] of Array.from(this.renderCounts.entries())) {
      console.log(`  ${component}: ${count} renders`);
    }
    
    console.log('\n⏱️ Timing Metrics:');
    for (const [operation] of Array.from(this.metrics.entries())) {
      const stats = this.getStats(operation);
      if (stats) {
        console.log(`  ${operation}:`);
        console.log(`    Average: ${stats.avg.toFixed(2)}ms`);
        console.log(`    Min: ${stats.min.toFixed(2)}ms`);
        console.log(`    Max: ${stats.max.toFixed(2)}ms`);
        console.log(`    Count: ${stats.count}`);
      }
    }
    
    console.groupEnd();
  }
}

// React hook for performance tracking
export const usePerformanceTracker = (componentName: string) => {
  const tracker = PerformanceTracker.getInstance();
  
  // Track render
  tracker.trackRender(componentName);
  
  return {
    startTiming: (operationName: string) => tracker.startTiming(operationName),
    getRenderCount: () => tracker.getRenderCount(componentName),
    getStats: (operationName: string) => tracker.getStats(operationName)
  };
};

// Utility to measure WebSocket performance
export const measureWebSocketDelay = (eventType: string, timestamp: string) => {
  const receivedAt = Date.now();
  const sentAt = new Date(timestamp).getTime();
  const delay = receivedAt - sentAt;
  
  const tracker = PerformanceTracker.getInstance();
  const endTiming = tracker.startTiming(`websocket_${eventType}`);
  endTiming();
  
  if (delay > 1000) { // Log if delay > 1 second
    console.warn(`⚠️ High WebSocket delay for ${eventType}: ${delay}ms`);
  }
  
  return delay;
};

// Export singleton instance
export const performanceTracker = PerformanceTracker.getInstance();