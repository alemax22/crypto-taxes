import React, { useState, useEffect } from 'react';
import { useParams, Link, useNavigate } from 'react-router-dom';
import axios from 'axios';
import LoadingSpinner from '../components/LoadingSpinner';
import TransactionTable from '../components/TransactionTable';
import WalletStats from '../components/WalletStats';

const WalletDetails = () => {
  const { walletId } = useParams();
  const navigate = useNavigate();
  const [wallet, setWallet] = useState(null);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [syncing, setSyncing] = useState(false);
  const [activeTab, setActiveTab] = useState('transactions');

  useEffect(() => {
    fetchWalletDetails();
  }, [walletId]);

  const fetchWalletDetails = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const [walletResponse, transactionsResponse] = await Promise.all([
        axios.get(`/api/wallets/${walletId}`),
        axios.get(`/api/wallets/${walletId}/transactions`)
      ]);

      if (walletResponse.data.success) {
        setWallet(walletResponse.data.wallet);
      } else {
        setError('Wallet not found');
        return;
      }

      if (transactionsResponse.data.success) {
        setTransactions(transactionsResponse.data.transactions || []);
      }
    } catch (err) {
      console.error('Error fetching wallet details:', err);
      if (err.response?.status === 404) {
        setError('Wallet not found');
      } else {
        setError('Failed to load wallet details');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async () => {
    setSyncing(true);
    try {
      const response = await axios.post(`/api/wallets/${walletId}/sync`);
      if (response.data.success) {
        // Refresh data after sync
        await fetchWalletDetails();
      } else {
        alert('Failed to sync wallet');
      }
    } catch (err) {
      console.error('Error syncing wallet:', err);
      alert('Failed to sync wallet');
    } finally {
      setSyncing(false);
    }
  };

  const handleDelete = async () => {
    if (!window.confirm(`Are you sure you want to delete "${wallet.name}"? This action cannot be undone.`)) {
      return;
    }

    try {
      const response = await axios.delete(`/api/wallets/${walletId}`);
      if (response.data.success) {
        navigate('/wallets');
      } else {
        alert('Failed to delete wallet');
      }
    } catch (err) {
      console.error('Error deleting wallet:', err);
      alert('Failed to delete wallet');
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-EU', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount || 0);
  };

  const getWalletIcon = () => {
    switch (wallet?.type?.toLowerCase()) {
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

  const getStatusInfo = () => {
    if (!wallet) return { status: 'unknown', label: 'Unknown', color: 'var(--text-muted)' };
    
    if (wallet.is_syncing || syncing) {
      return { status: 'syncing', label: 'Syncing...', color: 'var(--primary-blue)' };
    }
    
    if (!wallet.is_active) {
      return { status: 'inactive', label: 'Inactive', color: 'var(--text-muted)' };
    }
    
    if (!wallet.last_sync) {
      return { status: 'unsynced', label: 'Not Synced', color: 'var(--warning)' };
    }
    
    const lastSync = new Date(wallet.last_sync);
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

  if (loading) {
    return (
      <div className="wallet-details-loading">
        <LoadingSpinner size="lg" />
        <p className="text-secondary mt-4">Loading wallet details...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="wallet-details-error">
        <div className="card">
          <div className="card-body text-center">
            <div className="error-icon">⚠️</div>
            <h3 className="mb-4">{error}</h3>
            <div className="error-actions">
              <Link to="/wallets" className="btn btn-primary">
                Back to Wallets
              </Link>
              <button 
                className="btn btn-outline"
                onClick={fetchWalletDetails}
              >
                Try Again
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const statusInfo = getStatusInfo();

  return (
    <div className="wallet-details fade-in">
      {/* Breadcrumb */}
      <div className="breadcrumb mb-6">
        <Link to="/wallets" className="breadcrumb-link">Wallets</Link>
        <span className="breadcrumb-separator">›</span>
        <span className="breadcrumb-current">{wallet.name}</span>
      </div>

      {/* Wallet Header */}
      <div className="wallet-header card mb-6">
        <div className="card-body">
          <div className="header-content">
            <div className="wallet-info">
              <div className="wallet-icon-container">
                <div className="wallet-icon">{getWalletIcon()}</div>
                {(wallet.is_syncing || syncing) && (
                  <div className="sync-indicator spinning">⟳</div>
                )}
              </div>
              <div className="wallet-details">
                <h1 className="wallet-name">{wallet.name}</h1>
                <div className="wallet-meta">
                  <span className="wallet-type">{wallet.type}</span>
                  <span className="wallet-separator">•</span>
                  <span 
                    className="wallet-status"
                    style={{ color: statusInfo.color }}
                  >
                    {statusInfo.label}
                  </span>
                  {wallet.description && (
                    <>
                      <span className="wallet-separator">•</span>
                      <span className="wallet-description">{wallet.description}</span>
                    </>
                  )}
                </div>
              </div>
            </div>
            
            <div className="wallet-actions">
              <button 
                className="btn btn-outline btn-sm"
                onClick={handleSync}
                disabled={syncing || wallet.is_syncing}
              >
                {syncing || wallet.is_syncing ? (
                  <>
                    <LoadingSpinner size="sm" />
                    <span style={{ marginLeft: '0.5rem' }}>Syncing...</span>
                  </>
                ) : (
                  <>
                    <span className="action-icon">🔄</span>
                    Sync Wallet
                  </>
                )}
              </button>
              <button 
                className="btn btn-outline btn-sm text-error"
                onClick={handleDelete}
              >
                <span className="action-icon">🗑️</span>
                Delete
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Wallet Stats */}
      <WalletStats wallet={wallet} transactions={transactions} />

      {/* Navigation Tabs */}
      <div className="wallet-tabs mb-6">
        <div className="tab-list">
          <button
            className={`tab-button ${activeTab === 'transactions' ? 'active' : ''}`}
            onClick={() => setActiveTab('transactions')}
          >
            <span className="tab-icon">📊</span>
            Transactions ({transactions.length})
          </button>
          <button
            className={`tab-button ${activeTab === 'assets' ? 'active' : ''}`}
            onClick={() => setActiveTab('assets')}
          >
            <span className="tab-icon">💰</span>
            Assets ({wallet.asset_count || 0})
          </button>
        </div>
      </div>

      {/* Tab Content */}
      <div className="tab-content">
        {activeTab === 'transactions' && (
          <div className="transactions-tab fade-in">
            <TransactionTable 
              transactions={transactions} 
              walletName={wallet.name}
            />
          </div>
        )}
        
        {activeTab === 'assets' && (
          <div className="assets-tab fade-in">
            <div className="card">
              <div className="card-header">
                <h3>Asset Holdings</h3>
                <p className="text-secondary">Current asset balances in this wallet</p>
              </div>
              <div className="card-body">
                <div className="coming-soon">
                  <div className="coming-soon-icon">🚧</div>
                  <h4>Asset Holdings View</h4>
                  <p className="text-secondary">
                    Asset breakdown and holdings view is coming soon. 
                    For now, you can view your transactions to see asset activity.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .wallet-details-loading,
        .wallet-details-error {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 400px;
        }

        .error-icon {
          font-size: 3rem;
          margin-bottom: 1rem;
        }

        .error-actions {
          display: flex;
          gap: 1rem;
          justify-content: center;
        }

        .breadcrumb {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-size: 0.875rem;
        }

        .breadcrumb-link {
          color: var(--primary-blue);
          text-decoration: none;
          transition: var(--transition);
        }

        .breadcrumb-link:hover {
          color: var(--primary-blue-light);
        }

        .breadcrumb-separator {
          color: var(--text-muted);
        }

        .breadcrumb-current {
          color: var(--text-secondary);
        }

        .wallet-header {
          position: relative;
          overflow: hidden;
        }

        .wallet-header::before {
          content: '';
          position: absolute;
          top: 0;
          left: 0;
          right: 0;
          height: 4px;
          background: var(--gradient-primary);
        }

        .header-content {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          gap: 2rem;
        }

        .wallet-info {
          display: flex;
          gap: 1.5rem;
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
          font-size: 3rem;
          width: 4rem;
          height: 4rem;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: var(--border-radius-lg);
          background: rgba(59, 130, 246, 0.1);
          border: 3px solid rgba(59, 130, 246, 0.2);
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
        }

        .wallet-name {
          font-size: 2rem;
          font-weight: 700;
          color: var(--text-primary);
          margin: 0 0 0.5rem 0;
          line-height: 1.2;
        }

        .wallet-meta {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          flex-wrap: wrap;
          font-size: 0.875rem;
        }

        .wallet-type {
          color: var(--text-secondary);
          font-weight: 600;
          text-transform: capitalize;
        }

        .wallet-separator {
          color: var(--text-muted);
        }

        .wallet-status {
          font-weight: 600;
        }

        .wallet-description {
          color: var(--text-muted);
          font-style: italic;
        }

        .wallet-actions {
          display: flex;
          gap: 0.75rem;
          flex-shrink: 0;
        }

        .action-icon {
          margin-right: 0.5rem;
        }

        .text-error {
          color: var(--error) !important;
        }

        .text-error:hover {
          color: var(--error) !important;
          background: rgba(239, 68, 68, 0.1) !important;
        }

        .wallet-tabs {
          border-bottom: 1px solid var(--dark-border);
        }

        .tab-list {
          display: flex;
          gap: 0;
        }

        .tab-button {
          background: none;
          border: none;
          padding: 1rem 1.5rem;
          color: var(--text-secondary);
          cursor: pointer;
          transition: var(--transition);
          border-bottom: 3px solid transparent;
          display: flex;
          align-items: center;
          gap: 0.5rem;
          font-weight: 500;
        }

        .tab-button:hover {
          color: var(--text-primary);
          background: rgba(59, 130, 246, 0.05);
        }

        .tab-button.active {
          color: var(--primary-blue);
          border-bottom-color: var(--primary-blue);
          background: rgba(59, 130, 246, 0.1);
        }

        .tab-icon {
          font-size: 1.1rem;
        }

        .tab-content {
          min-height: 400px;
        }

        .coming-soon {
          text-align: center;
          padding: 4rem 2rem;
        }

        .coming-soon-icon {
          font-size: 4rem;
          margin-bottom: 1.5rem;
          opacity: 0.6;
        }

        .coming-soon h4 {
          margin-bottom: 1rem;
          color: var(--text-primary);
        }

        @media (max-width: 768px) {
          .header-content {
            flex-direction: column;
            gap: 1.5rem;
          }

          .wallet-info {
            width: 100%;
          }

          .wallet-actions {
            width: 100%;
            justify-content: stretch;
          }

          .wallet-actions .btn {
            flex: 1;
          }

          .wallet-name {
            font-size: 1.75rem;
          }

          .wallet-meta {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
          }

          .tab-list {
            flex-wrap: wrap;
          }

          .tab-button {
            flex: 1;
            min-width: 0;
            padding: 0.75rem 1rem;
          }

          .error-actions {
            flex-direction: column;
            width: 100%;
            max-width: 300px;
          }
        }

        @media (max-width: 480px) {
          .wallet-icon {
            font-size: 2.5rem;
            width: 3.5rem;
            height: 3.5rem;
          }

          .wallet-name {
            font-size: 1.5rem;
          }

          .coming-soon {
            padding: 2rem 1rem;
          }

          .coming-soon-icon {
            font-size: 3rem;
          }
        }
      `}</style>
    </div>
  );
};

export default WalletDetails;
