import React from 'react';

interface BarChartData {
  label: string;
  value: number;
  color: string;
}

interface BarChartProps {
  data: BarChartData[];
  title: string;
  height?: number;
}

const BarChart: React.FC<BarChartProps> = ({ data, title, height = 120 }) => {
  const maxValue = Math.max(...data.map(item => item.value), 1);
  
  if (data.length === 0 || maxValue === 0) {
    return (
      <div className="flex flex-col items-center space-y-2">
        <div className="text-sm font-medium text-gray-600 dark:text-gray-300">{title}</div>
        <div className="text-xs text-gray-400">No data available</div>
      </div>
    );
  }
  
  const barWidth = 30;
  const barSpacing = 10;
  const chartWidth = data.length * (barWidth + barSpacing) - barSpacing + 40;
  const paddingLeft = 20;
  const paddingBottom = 20;
  
  return (
    <div className="flex flex-col space-y-3">
      <div className="text-sm font-medium text-gray-600 dark:text-gray-300 text-center">{title}</div>
      
      <div className="overflow-x-auto">
        <svg width={chartWidth} height={height + paddingBottom} className="drop-shadow-sm">
          {/* Bars */}
          {data.map((item, index) => {
            const barHeight = (item.value / maxValue) * height;
            const x = paddingLeft + index * (barWidth + barSpacing);
            const y = height - barHeight;
            
            return (
              <g key={index}>
                <rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={barHeight}
                  fill={item.color}
                  className="hover:opacity-80 transition-opacity"
                  rx="2"
                />
                
                {/* Value label on top of bar */}
                {item.value > 0 && (
                  <text
                    x={x + barWidth / 2}
                    y={y - 4}
                    textAnchor="middle"
                    className="fill-gray-600 dark:fill-gray-300 text-xs font-medium"
                  >
                    {item.value}
                  </text>
                )}
                
                {/* Label below bar */}
                <text
                  x={x + barWidth / 2}
                  y={height + 15}
                  textAnchor="middle"
                  className="fill-gray-500 dark:fill-gray-400 text-xs"
                >
                  {item.label.length > 8 ? item.label.substring(0, 8) + '...' : item.label}
                </text>
              </g>
            );
          })}
          
          {/* Y-axis line */}
          <line
            x1={paddingLeft - 5}
            y1={0}
            x2={paddingLeft - 5}
            y2={height}
            stroke="currentColor"
            strokeWidth="1"
            className="text-gray-300 dark:text-gray-600"
          />
          
          {/* X-axis line */}
          <line
            x1={paddingLeft - 5}
            y1={height}
            x2={chartWidth - 20}
            y2={height}
            stroke="currentColor"
            strokeWidth="1"
            className="text-gray-300 dark:text-gray-600"
          />
        </svg>
      </div>
    </div>
  );
};

export default BarChart;