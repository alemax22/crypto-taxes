import React from 'react';

const StatsCard = ({ 
  title, 
  value, 
  icon, 
  trend, 
  subtitle, 
  className = '', 
  style = {} 
}) => {
  const getTrendColor = (trendValue) => {
    if (trendValue > 0) return 'var(--success)';
    if (trendValue < 0) return 'var(--error)';
    return 'var(--text-muted)';
  };

  const formatTrend = (trendValue) => {
    if (!trendValue && trendValue !== 0) return null;
    const sign = trendValue > 0 ? '+' : '';
    return `${sign}${trendValue.toFixed(2)}%`;
  };

  return (
    <div className={`stats-card card ${className}`} style={style}>
      <div className="card-body">
        <div className="stats-header">
          <div className="stats-icon">{icon}</div>
          {trend !== undefined && (
            <div className="trend-indicator" style={{ color: getTrendColor(trend) }}>
              {trend > 0 ? '📈' : trend < 0 ? '📉' : '➖'}
            </div>
          )}
        </div>
        
        <div className="stats-content">
          <div className="stats-value">{value}</div>
          <div className="stats-title">{title}</div>
          
          {(subtitle || trend !== undefined) && (
            <div className="stats-meta">
              {subtitle && <span className="stats-subtitle">{subtitle}</span>}
              {trend !== undefined && (
                <span 
                  className="stats-trend"
                  style={{ color: getTrendColor(trend) }}
                >
                  {formatTrend(trend)}
                </span>
              )}
            </div>
          )}
        </div>
      </div>

      <style jsx>{`
        .stats-card {
          position: relative;
          overflow: hidden;
        }

        .stats-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 3px;
          background: var(--gradient-primary);
        }

        .card-body {
          padding: 1.5rem;
        }

        .stats-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .stats-icon {
          font-size: 2rem;
          padding: 0.5rem;
          border-radius: var(--border-radius);
          background: rgba(59, 130, 246, 0.1);
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .trend-indicator {
          font-size: 1.2rem;
          opacity: 0.8;
        }

        .stats-content {
          text-align: left;
        }

        .stats-value {
          font-size: 2rem;
          font-weight: 700;
          color: var(--text-primary);
          line-height: 1;
          margin-bottom: 0.5rem;
        }

        .stats-title {
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-secondary);
          margin-bottom: 0.5rem;
        }

        .stats-meta {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .stats-subtitle {
          font-size: 0.75rem;
          color: var(--text-muted);
        }

        .stats-trend {
          font-size: 0.75rem;
          font-weight: 600;
        }

        .stats-card:hover {
          transform: translateY(-2px);
        }

        .stats-card:hover .stats-icon {
          background: rgba(59, 130, 246, 0.2);
        }

        @media (max-width: 768px) {
          .stats-value {
            font-size: 1.75rem;
          }
          
          .stats-icon {
            font-size: 1.5rem;
            padding: 0.375rem;
          }
        }
      `}</style>
    </div>
  );
};

export default StatsCard;
