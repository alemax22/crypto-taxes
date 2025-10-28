import React, { useState } from 'react';
import { Link } from 'react-router-dom';

const WalletCard = ({ wallet, onDelete, onSync, className = '', style = {} }) => {
  const [isMenuOpen, setIsMenuOpen] = useState(false);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-EU', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount || 0);
  };

  const getStatusInfo = () => {
    if (wallet.is_syncing) {
      return { status: 'syncing', label: 'Syncing...', color: 'var(--primary-blue)' };
    }
    
    if (!wallet.is_active) {
      return { status: 'inactive', label: 'Inactive', color: 'var(--text-muted)' };
    }
    
    if (wallet.sync_status === 'NOT_SYNCHRONIZED') {
      return { status: 'unsynced', label: 'Not Synced', color: 'var(--warning)' };
    }
    
    const lastSync = new Date(wallet.updated_datetime);
    const now = new Date();
    const diffHours = (now - lastSync) / (1000 * 60 * 60);
    
    if (diffHours < 24) {
      return { status: 'synced', label: 'Synced', color: 'var(--success)' };
    } else if (diffHours < 168) { // 1 week
      const days = Math.floor(diffHours / 24);
      return { status: 'stale', label: `${days}d ago`, color: 'var(--warning)' };
    } else {
      return { status: 'old', label: 'Needs Sync', color: 'var(--error)' };
    }
  };

  const getWalletIcon = () => {
    switch (wallet.wallet_type?.toLowerCase()) {
      case 'kraken':
        return '🐙';
      case 'binance':
        return '🟡';
      case 'coinbase':
        return '🔵';
      case 'metamask':
        return '🦊';
      default:
        return '💼';
    }
  };

  const getTransactionCount = () => {
    return wallet.transaction_count || 0;
  };

  const formatLastSync = () => {
    if (!wallet.updated_datetime) return 'Never';
    
    const date = new Date(wallet.updated_datetime);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);
    
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  const statusInfo = getStatusInfo();

  return (
    <div className={`wallet-card card ${className}`} style={style}>
      <div className="card-body">
        {/* Header */}
        <div className="wallet-header">
          <div className="wallet-info">
            <div className="wallet-icon-container">
              <div className="wallet-icon">{getWalletIcon()}</div>
              {wallet.is_syncing && <div className="sync-indicator spinning">⟳</div>}
            </div>
            <div className="wallet-details">
              <h3 className="wallet-name">{wallet.name}</h3>
              <div className="wallet-meta">
                <span className="wallet-type">{wallet.wallet_type}</span>
                <span className="wallet-separator">•</span>
                <span 
                  className="wallet-status"
                  style={{ color: statusInfo.color }}
                >
                  {statusInfo.label}
                </span>
              </div>
            </div>
          </div>
          
          <div className="wallet-actions">
            <div className="wallet-menu" onClick={(e) => e.stopPropagation()}>
              <button
                className="menu-trigger"
                onClick={() => setIsMenuOpen(!isMenuOpen)}
                aria-label="Wallet options"
              >
                ⋮
              </button>
              {isMenuOpen && (
                <div className="menu-dropdown">
                  <button 
                    className="menu-item"
                    onClick={() => {
                      onSync();
                      setIsMenuOpen(false);
                    }}
                    disabled={wallet.is_syncing}
                  >
                    <span className="menu-icon">🔄</span>
                    Sync Wallet
                  </button>
                  <button 
                    className="menu-item text-error"
                    onClick={() => {
                      onDelete();
                      setIsMenuOpen(false);
                    }}
                  >
                    <span className="menu-icon">🗑️</span>
                    Delete
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Balance */}
        <div className="wallet-balance">
          <div className="balance-main">
            <div className="balance-amount">{formatCurrency(wallet.balance)}</div>
            <div className="balance-label">Total Balance</div>
          </div>
          {wallet.balance_change_24h !== undefined && (
            <div className={`balance-change ${wallet.balance_change_24h >= 0 ? 'positive' : 'negative'}`}>
              <span className="change-icon">
                {wallet.balance_change_24h >= 0 ? '📈' : '📉'}
              </span>
              <span className="change-value">
                {wallet.balance_change_24h >= 0 ? '+' : ''}
                {wallet.balance_change_24h.toFixed(2)}%
              </span>
            </div>
          )}
        </div>

        {/* Stats */}
        <div className="wallet-stats">
          <div className="stat-item">
            <div className="stat-value">{getTransactionCount()}</div>
            <div className="stat-label">Transactions</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{wallet.asset_count || 0}</div>
            <div className="stat-label">Assets</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{formatLastSync()}</div>
            <div className="stat-label">Last Sync</div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="card-footer">
        <Link 
          to={`/wallets/${wallet.wallet_id}`}
          className="btn btn-outline btn-sm wallet-view-btn"
        >
          View Details
        </Link>
      </div>

      <style jsx>{`
        .wallet-card {
          position: relative;
          transition: var(--transition);
          cursor: pointer;
        }

        .wallet-card:hover {
          transform: translateY(-4px);
          box-shadow: var(--shadow-xl);
        }

        .wallet-card::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 4px;
          background: var(--gradient-primary);
          border-radius: var(--border-radius) var(--border-radius) 0 0;
        }

        .wallet-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 1.5rem;
        }

        .wallet-info {
          display: flex;
          gap: 1rem;
          align-items: flex-start;
          flex: 1;
        }

        .wallet-icon-container {
          position: relative;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .wallet-icon {
          font-size: 2.5rem;
          width: 3.5rem;
          height: 3.5rem;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: var(--border-radius);
          background: rgba(59, 130, 246, 0.1);
          border: 2px solid rgba(59, 130, 246, 0.2);
        }

        .sync-indicator {
          position: absolute;
          top: -4px;
          right: -4px;
          width: 1.5rem;
          height: 1.5rem;
          background: var(--primary-blue);
          color: white;
          border-radius: 50%;
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.875rem;
          font-weight: bold;
        }

        .wallet-details {
          flex: 1;
          min-width: 0;
        }

        .wallet-name {
          font-size: 1.25rem;
          font-weight: 600;
          color: var(--text-primary);
          margin: 0 0 0.25rem 0;
          line-height: 1.2;
        }

        .wallet-meta {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.875rem;
        }

        .wallet-type {
          color: var(--text-secondary);
          font-weight: 500;
          text-transform: capitalize;
        }

        .wallet-separator {
          color: var(--text-muted);
        }

        .wallet-status {
          font-weight: 500;
        }

        .wallet-actions {
          position: relative;
        }

        .wallet-menu {
          position: relative;
        }

        .menu-trigger {
          background: none;
          border: none;
          color: var(--text-muted);
          font-size: 1.25rem;
          padding: 0.5rem;
          border-radius: 50%;
          cursor: pointer;
          transition: var(--transition);
          width: 2rem;
          height: 2rem;
          display: flex;
          align-items: center;
          justify-content: center;
        }

        .menu-trigger:hover {
          background: var(--dark-surface-hover);
          color: var(--text-primary);
        }

        .menu-dropdown {
          position: absolute;
          top: 100%;
          right: 0;
          background: var(--dark-surface);
          border: 1px solid var(--dark-border);
          border-radius: var(--border-radius);
          box-shadow: var(--shadow-lg);
          z-index: 10;
          min-width: 150px;
          overflow: hidden;
        }

        .menu-item {
          width: 100%;
          padding: 0.75rem 1rem;
          background: none;
          border: none;
          text-align: left;
          color: var(--text-secondary);
          cursor: pointer;
          transition: var(--transition);
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.875rem;
        }

        .menu-item:hover {
          background: var(--dark-surface-hover);
          color: var(--text-primary);
        }

        .menu-item:disabled {
          opacity: 0.5;
          cursor: not-allowed;
        }

        .menu-item.text-error {
          color: var(--error);
        }

        .menu-item.text-error:hover {
          background: rgba(239, 68, 68, 0.1);
          color: var(--error);
        }

        .menu-icon {
          font-size: 1rem;
        }

        .wallet-balance {
          display: flex;
          justify-content: space-between;
          align-items: flex-end;
          margin-bottom: 1.5rem;
          padding: 1rem;
          background: rgba(59, 130, 246, 0.05);
          border-radius: var(--border-radius);
          border: 1px solid rgba(59, 130, 246, 0.1);
        }

        .balance-main {
          flex: 1;
        }

        .balance-amount {
          font-size: 1.75rem;
          font-weight: 700;
          color: var(--text-primary);
          line-height: 1;
          margin-bottom: 0.25rem;
        }

        .balance-label {
          font-size: 0.875rem;
          color: var(--text-muted);
        }

        .balance-change {
          display: flex;
          align-items: center;
          gap: 0.25rem;
          font-size: 0.875rem;
          font-weight: 600;
        }

        .balance-change.positive {
          color: var(--success);
        }

        .balance-change.negative {
          color: var(--error);
        }

        .change-icon {
          font-size: 1rem;
        }

        .wallet-stats {
          display: grid;
          grid-template-columns: repeat(3, 1fr);
          gap: 1rem;
        }

        .stat-item {
          text-align: center;
          padding: 0.75rem;
          background: rgba(255, 255, 255, 0.02);
          border-radius: var(--border-radius);
          border: 1px solid var(--dark-border);
        }

        .stat-value {
          font-size: 1.125rem;
          font-weight: 600;
          color: var(--text-primary);
          margin-bottom: 0.25rem;
        }

        .stat-label {
          font-size: 0.75rem;
          color: var(--text-muted);
        }

        .card-footer {
          background: rgba(0, 0, 0, 0.1);
          border-top: 1px solid var(--dark-border);
          padding: 1rem 1.5rem;
        }

        .wallet-view-btn {
          width: 100%;
          justify-content: center;
        }

        /* Click outside to close menu */
        .wallet-menu.open::before {
          content: '';
          position: fixed;
          top: 0;
          left: 0;
          right: 0;
          bottom: 0;
          z-index: 5;
        }

        @media (max-width: 768px) {
          .wallet-header {
            flex-direction: column;
            gap: 1rem;
          }
          
          .wallet-info {
            width: 100%;
          }
          
          .balance-amount {
            font-size: 1.5rem;
          }
          
          .wallet-stats {
            grid-template-columns: 1fr;
            gap: 0.75rem;
          }
          
          .stat-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            text-align: left;
          }
          
          .stat-value {
            margin-bottom: 0;
          }
        }
      `}</style>
    </div>
  );
};

export default WalletCard;
