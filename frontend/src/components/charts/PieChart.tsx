import React from 'react';

interface PieChartData {
  label: string;
  value: number;
  color: string;
}

interface PieChartProps {
  data: PieChartData[];
  title: string;
  size?: number;
}

const PieChart: React.FC<PieChartProps> = ({ data, title, size = 120 }) => {
  const total = data.reduce((sum, item) => sum + item.value, 0);
  
  if (total === 0) {
    return (
      <div className="flex flex-col items-center space-y-2">
        <div className="text-sm font-medium text-gray-600 dark:text-gray-300">{title}</div>
        <div className="text-xs text-gray-400">No data available</div>
      </div>
    );
  }
  
  let currentAngle = 0;
  const radius = size / 2 - 10;
  const centerX = size / 2;
  const centerY = size / 2;
  
  const createPath = (startAngle: number, endAngle: number) => {
    const startAngleRad = (startAngle * Math.PI) / 180;
    const endAngleRad = (endAngle * Math.PI) / 180;
    
    const x1 = centerX + radius * Math.cos(startAngleRad);
    const y1 = centerY + radius * Math.sin(startAngleRad);
    const x2 = centerX + radius * Math.cos(endAngleRad);
    const y2 = centerY + radius * Math.sin(endAngleRad);
    
    const largeArcFlag = endAngle - startAngle <= 180 ? 0 : 1;
    
    return `M ${centerX} ${centerY} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;
  };
  
  return (
    <div className="flex flex-col items-center space-y-3">
      <div className="text-sm font-medium text-gray-600 dark:text-gray-300">{title}</div>
      
      <div className="flex items-center space-x-4">
        <svg width={size} height={size} className="drop-shadow-sm">
          {data.map((item, index) => {
            if (item.value === 0) return null;
            
            const percentage = (item.value / total) * 100;
            const angle = (percentage / 100) * 360;
            const path = createPath(currentAngle, currentAngle + angle);
            
            currentAngle += angle;
            
            return (
              <path
                key={index}
                d={path}
                fill={item.color}
                stroke="white"
                strokeWidth="1"
                className="hover:opacity-80 transition-opacity"
              />
            );
          })}
        </svg>
        
        <div className="space-y-1">
          {data.filter(item => item.value > 0).map((item, index) => (
            <div key={index} className="flex items-center space-x-2 text-xs">
              <div
                className="w-3 h-3 rounded-full"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-gray-600 dark:text-gray-300">
                {item.label}: {item.value}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default PieChart;