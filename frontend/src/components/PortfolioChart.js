import React from 'react';

const PortfolioChart = ({ data = [] }) => {
  const colors = [
    '#3b82f6', '#1d4ed8', '#60a5fa', '#2563eb', '#1e40af',
    '#10b981', '#059669', '#34d399', '#6ee7b7', '#a7f3d0'
  ];

  const total = data.reduce((sum, asset) => sum + (asset.balance || 0), 0);

  const getPercentage = (value) => {
    if (total === 0) return 0;
    return ((value / total) * 100).toFixed(1);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-EU', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(amount || 0);
  };

  if (!data || data.length === 0) {
    return (
      <div className="portfolio-chart">
        <div className="empty-chart">
          <div className="empty-icon">📊</div>
          <p className="text-muted">No portfolio data available</p>
        </div>

        <style jsx>{`
          .portfolio-chart {
            height: 300px;
            display: flex;
            align-items: center;
            justify-content: center;
          }

          .empty-chart {
            text-align: center;
          }

          .empty-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
            opacity: 0.5;
          }
        `}</style>
      </div>
    );
  }

  // Calculate angles for pie chart
  let currentAngle = 0;
  const segments = data.map((asset, index) => {
    const percentage = (asset.balance / total) * 100;
    const angle = (percentage / 100) * 360;
    const startAngle = currentAngle;
    currentAngle += angle;

    return {
      ...asset,
      percentage,
      startAngle,
      endAngle: currentAngle,
      color: colors[index % colors.length]
    };
  });

  const createPath = (centerX, centerY, radius, startAngle, endAngle) => {
    const start = polarToCartesian(centerX, centerY, radius, endAngle);
    const end = polarToCartesian(centerX, centerY, radius, startAngle);
    const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";

    return [
      "M", centerX, centerY,
      "L", start.x, start.y,
      "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y,
      "Z"
    ].join(" ");
  };

  const polarToCartesian = (centerX, centerY, radius, angleInDegrees) => {
    const angleInRadians = (angleInDegrees - 90) * Math.PI / 180.0;
    return {
      x: centerX + (radius * Math.cos(angleInRadians)),
      y: centerY + (radius * Math.sin(angleInRadians))
    };
  };

  const centerX = 150;
  const centerY = 150;
  const radius = 100;

  return (
    <div className="portfolio-chart">
      <div className="chart-container">
        <svg width="300" height="300" className="pie-chart">
          {segments.map((segment, index) => (
            <path
              key={segment.symbol}
              d={createPath(centerX, centerY, radius, segment.startAngle, segment.endAngle)}
              fill={segment.color}
              className="chart-segment"
              data-tooltip={`${segment.symbol}: ${formatCurrency(segment.balance)} (${segment.percentage.toFixed(1)}%)`}
            />
          ))}
        </svg>
        
        <div className="chart-center">
          <div className="total-value">{formatCurrency(total)}</div>
          <div className="total-label">Total Value</div>
        </div>
      </div>

      <div className="chart-legend">
        {segments.map((segment) => (
          <div key={segment.symbol} className="legend-item">
            <div 
              className="legend-color"
              style={{ backgroundColor: segment.color }}
            ></div>
            <div className="legend-info">
              <div className="legend-symbol">{segment.symbol}</div>
              <div className="legend-percentage">{segment.percentage.toFixed(1)}%</div>
            </div>
            <div className="legend-value">
              {formatCurrency(segment.balance)}
            </div>
          </div>
        ))}
      </div>

      <style jsx>{`
        .portfolio-chart {
          display: flex;
          gap: 2rem;
          align-items: center;
          justify-content: center;
          min-height: 300px;
        }

        .chart-container {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .pie-chart {
          filter: drop-shadow(0 4px 8px rgba(0, 0, 0, 0.1));
        }

        .chart-segment {
          transition: all 0.3s ease;
          cursor: pointer;
        }

        .chart-segment:hover {
          filter: brightness(1.1);
          transform: scale(1.02);
        }

        .chart-center {
          position: absolute;
          text-align: center;
          pointer-events: none;
        }

        .total-value {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--text-primary);
          line-height: 1;
        }

        .total-label {
          font-size: 0.75rem;
          color: var(--text-muted);
          margin-top: 0.25rem;
        }

        .chart-legend {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
          max-height: 300px;
          overflow-y: auto;
        }

        .legend-item {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 0.5rem;
          border-radius: var(--border-radius);
          transition: var(--transition);
        }

        .legend-item:hover {
          background: rgba(59, 130, 246, 0.05);
        }

        .legend-color {
          width: 12px;
          height: 12px;
          border-radius: 50%;
          flex-shrink: 0;
        }

        .legend-info {
          flex: 1;
          min-width: 0;
        }

        .legend-symbol {
          font-weight: 600;
          color: var(--text-primary);
          font-size: 0.875rem;
        }

        .legend-percentage {
          font-size: 0.75rem;
          color: var(--text-muted);
        }

        .legend-value {
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-secondary);
          text-align: right;
        }

        @media (max-width: 768px) {
          .portfolio-chart {
            flex-direction: column;
            gap: 1.5rem;
          }

          .chart-container svg {
            width: 250px;
            height: 250px;
          }

          .total-value {
            font-size: 1.25rem;
          }

          .chart-legend {
            max-height: none;
            width: 100%;
          }
        }

        @media (max-width: 480px) {
          .chart-container svg {
            width: 200px;
            height: 200px;
          }

          .total-value {
            font-size: 1rem;
          }
        }
      `}</style>
    </div>
  );
};

export default PortfolioChart;
