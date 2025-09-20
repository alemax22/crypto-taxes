import React from 'react';

const WalletStats = ({ wallet, transactions = [] }) => {
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-EU', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount || 0);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-EU');
  };

  const getTransactionStats = () => {
    const stats = {
      total: transactions.length,
      buys: 0,
      sells: 0,
      deposits: 0,
      withdrawals: 0,
      totalVolume: 0
    };

    transactions.forEach(tx => {
      switch (tx.type?.toLowerCase()) {
        case 'buy':
        case 'trade_buy':
          stats.buys++;
          break;
        case 'sell':
        case 'trade_sell':
          stats.sells++;
          break;
        case 'deposit':
          stats.deposits++;
          break;
        case 'withdrawal':
          stats.withdrawals++;
          break;
      }
      stats.totalVolume += Math.abs(tx.amount || 0);
    });

    return stats;
  };

  const getRecentActivity = () => {
    if (transactions.length === 0) return null;
    
    const sortedTransactions = [...transactions]
      .sort((a, b) => new Date(b.timestamp || b.date) - new Date(a.timestamp || a.date));
    
    return sortedTransactions[0];
  };

  const getBalanceChange24h = () => {
    // This would typically come from the API with historical data
    // For now, we'll use mock data or wallet.balance_change_24h if available
    return wallet.balance_change_24h || 0;
  };

  const stats = getTransactionStats();
  const recentActivity = getRecentActivity();
  const balanceChange24h = getBalanceChange24h();

  return (
    <div className="wallet-stats mb-6">
      {/* Primary Stats */}
      <div className="primary-stats grid grid-cols-4 gap-4 mb-6">
        <div className="stat-card card">
          <div className="card-body">
            <div className="stat-header">
              <div className="stat-icon">💰</div>
              {balanceChange24h !== 0 && (
                <div className={`trend-indicator ${balanceChange24h >= 0 ? 'positive' : 'negative'}`}>
                  {balanceChange24h >= 0 ? '📈' : '📉'}
                </div>
              )}
            </div>
            <div className="stat-content">
              <div className="stat-value">{formatCurrency(wallet.balance)}</div>
              <div className="stat-label">Total Balance</div>
              {balanceChange24h !== 0 && (
                <div className={`stat-change ${balanceChange24h >= 0 ? 'positive' : 'negative'}`}>
                  {balanceChange24h >= 0 ? '+' : ''}{balanceChange24h.toFixed(2)}% (24h)
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="stat-card card">
          <div className="card-body">
            <div className="stat-header">
              <div className="stat-icon">📊</div>
            </div>
            <div className="stat-content">
              <div className="stat-value">{stats.total}</div>
              <div className="stat-label">Total Transactions</div>
              <div className="stat-meta">
                {stats.buys} buys • {stats.sells} sells
              </div>
            </div>
          </div>
        </div>

        <div className="stat-card card">
          <div className="card-body">
            <div className="stat-header">
              <div className="stat-icon">💎</div>
            </div>
            <div className="stat-content">
              <div className="stat-value">{wallet.asset_count || 0}</div>
              <div className="stat-label">Assets Held</div>
              <div className="stat-meta">Different cryptocurrencies</div>
            </div>
          </div>
        </div>

        <div className="stat-card card">
          <div className="card-body">
            <div className="stat-header">
              <div className="stat-icon">🔄</div>
            </div>
            <div className="stat-content">
              <div className="stat-value">{formatDate(wallet.last_sync)}</div>
              <div className="stat-label">Last Synchronized</div>
              <div className="stat-meta">
                {wallet.last_sync ? 'Data up to date' : 'Never synced'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Secondary Stats */}
      <div className="secondary-stats grid grid-cols-3 gap-4">
        <div className="info-card card">
          <div className="card-header">
            <h4>Activity Breakdown</h4>
          </div>
          <div className="card-body">
            <div className="activity-breakdown">
              <div className="activity-item">
                <div className="activity-type">
                  <span className="activity-icon">📈</span>
                  <span>Buy Orders</span>
                </div>
                <div className="activity-count">{stats.buys}</div>
              </div>
              <div className="activity-item">
                <div className="activity-type">
                  <span className="activity-icon">📉</span>
                  <span>Sell Orders</span>
                </div>
                <div className="activity-count">{stats.sells}</div>
              </div>
              <div className="activity-item">
                <div className="activity-type">
                  <span className="activity-icon">⬇️</span>
                  <span>Deposits</span>
                </div>
                <div className="activity-count">{stats.deposits}</div>
              </div>
              <div className="activity-item">
                <div className="activity-type">
                  <span className="activity-icon">⬆️</span>
                  <span>Withdrawals</span>
                </div>
                <div className="activity-count">{stats.withdrawals}</div>
              </div>
            </div>
          </div>
        </div>

        <div className="info-card card">
          <div className="card-header">
            <h4>Recent Activity</h4>
          </div>
          <div className="card-body">
            {recentActivity ? (
              <div className="recent-activity">
                <div className="recent-transaction">
                  <div className="transaction-type">
                    <span className="transaction-icon">
                      {recentActivity.type === 'buy' ? '📈' : 
                       recentActivity.type === 'sell' ? '📉' : '🔄'}
                    </span>
                    <span className="transaction-label">
                      {recentActivity.type?.charAt(0).toUpperCase() + 
                       recentActivity.type?.slice(1) || 'Transaction'}
                    </span>
                  </div>
                  <div className="transaction-details">
                    <div className="transaction-asset">{recentActivity.asset || 'Unknown'}</div>
                    <div className="transaction-amount">
                      {formatCurrency(Math.abs(recentActivity.amount || 0))}
                    </div>
                    <div className="transaction-date">
                      {formatDate(recentActivity.timestamp || recentActivity.date)}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="no-activity">
                <div className="no-activity-icon">📊</div>
                <p className="text-muted">No recent transactions</p>
              </div>
            )}
          </div>
        </div>

        <div className="info-card card">
          <div className="card-header">
            <h4>Wallet Info</h4>
          </div>
          <div className="card-body">
            <div className="wallet-info">
              <div className="info-item">
                <div className="info-label">Exchange</div>
                <div className="info-value">{wallet.type}</div>
              </div>
              <div className="info-item">
                <div className="info-label">Status</div>
                <div className="info-value">
                  <span className={`status-badge ${wallet.is_active ? 'active' : 'inactive'}`}>
                    {wallet.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </div>
              <div className="info-item">
                <div className="info-label">Created</div>
                <div className="info-value">{formatDate(wallet.created_at)}</div>
              </div>
              {wallet.description && (
                <div className="info-item">
                  <div className="info-label">Description</div>
                  <div className="info-value">{wallet.description}</div>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .primary-stats {
          gap: 1.5rem;
        }

        .stat-card {
          transition: var(--transition);
        }

        .stat-card:hover {
          transform: translateY(-2px);
        }

        .stat-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 3px;
          background: var(--gradient-primary);
          border-radius: var(--border-radius) var(--border-radius) 0 0;
        }

        .stat-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1rem;
        }

        .stat-icon {
          font-size: 1.75rem;
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

        .trend-indicator.positive {
          color: var(--success);
        }

        .trend-indicator.negative {
          color: var(--error);
        }

        .stat-content {
          text-align: left;
        }

        .stat-value {
          font-size: 1.75rem;
          font-weight: 700;
          color: var(--text-primary);
          line-height: 1;
          margin-bottom: 0.5rem;
        }

        .stat-label {
          font-size: 0.875rem;
          font-weight: 500;
          color: var(--text-secondary);
          margin-bottom: 0.25rem;
        }

        .stat-meta {
          font-size: 0.75rem;
          color: var(--text-muted);
        }

        .stat-change {
          font-size: 0.75rem;
          font-weight: 600;
          margin-top: 0.25rem;
        }

        .stat-change.positive {
          color: var(--success);
        }

        .stat-change.negative {
          color: var(--error);
        }

        .secondary-stats {
          gap: 1.5rem;
        }

        .info-card h4 {
          margin: 0;
          font-size: 1rem;
          color: var(--text-primary);
        }

        .activity-breakdown {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .activity-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.5rem;
          background: rgba(59, 130, 246, 0.05);
          border-radius: var(--border-radius);
        }

        .activity-type {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.875rem;
          color: var(--text-secondary);
        }

        .activity-icon {
          font-size: 1rem;
        }

        .activity-count {
          font-weight: 600;
          color: var(--text-primary);
        }

        .recent-activity {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .recent-transaction {
          padding: 1rem;
          background: rgba(59, 130, 246, 0.05);
          border-radius: var(--border-radius);
          border: 1px solid rgba(59, 130, 246, 0.1);
        }

        .transaction-type {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          margin-bottom: 0.75rem;
        }

        .transaction-icon {
          font-size: 1.2rem;
        }

        .transaction-label {
          font-weight: 600;
          color: var(--text-primary);
          text-transform: capitalize;
        }

        .transaction-details {
          display: flex;
          flex-direction: column;
          gap: 0.25rem;
        }

        .transaction-asset {
          font-weight: 600;
          color: var(--primary-blue);
        }

        .transaction-amount {
          font-size: 0.875rem;
          color: var(--text-secondary);
        }

        .transaction-date {
          font-size: 0.75rem;
          color: var(--text-muted);
        }

        .no-activity {
          text-align: center;
          padding: 2rem 1rem;
        }

        .no-activity-icon {
          font-size: 2rem;
          margin-bottom: 0.5rem;
          opacity: 0.5;
        }

        .wallet-info {
          display: flex;
          flex-direction: column;
          gap: 0.75rem;
        }

        .info-item {
          display: flex;
          justify-content: space-between;
          align-items: center;
          padding: 0.5rem;
          background: rgba(255, 255, 255, 0.02);
          border-radius: var(--border-radius);
        }

        .info-label {
          font-size: 0.875rem;
          color: var(--text-muted);
        }

        .info-value {
          font-size: 0.875rem;
          color: var(--text-secondary);
          font-weight: 500;
          text-align: right;
        }

        .status-badge {
          padding: 0.25rem 0.75rem;
          border-radius: 9999px;
          font-size: 0.75rem;
          font-weight: 600;
        }

        .status-badge.active {
          background: var(--success);
          color: white;
        }

        .status-badge.inactive {
          background: var(--dark-border);
          color: var(--text-muted);
        }

        @media (max-width: 1024px) {
          .primary-stats {
            grid-template-columns: repeat(2, 1fr);
          }
          
          .secondary-stats {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 768px) {
          .primary-stats {
            grid-template-columns: 1fr;
          }
          
          .stat-value {
            font-size: 1.5rem;
          }
          
          .activity-item,
          .info-item {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.25rem;
          }
          
          .info-value {
            text-align: left;
          }
        }
      `}</style>
    </div>
  );
};

export default WalletStats;
