import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import LoadingSpinner from '../components/LoadingSpinner';
import StatsCard from '../components/StatsCard';
import PortfolioChart from '../components/PortfolioChart';

const Dashboard = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [portfolioData, setPortfolioData] = useState(null);
  const [wallets, setWallets] = useState([]);
  const [totalBalance, setTotalBalance] = useState(0);

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const fetchDashboardData = async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Fetch portfolio data and wallets in parallel
      const [portfoliosResponse, walletsResponse] = await Promise.all([
        axios.get('/portfolios'),
        axios.get('/portfolios')
      ]);

      if (portfoliosResponse.data.success && portfoliosResponse.data.data.length > 0) {
        const portfolio = portfoliosResponse.data.data[0]; // Get first portfolio
        setPortfolioData(portfolio);
        setTotalBalance(0); // Will be calculated from wallet balances
      }

      if (walletsResponse.data.success && walletsResponse.data.data.length > 0) {
        const portfolio = walletsResponse.data.data[0];
        // Get wallets for the portfolio
        const walletsResponse2 = await axios.get(`/portfolios/${portfolio.portfolio_id}/wallets`);
        if (walletsResponse2.data.success) {
          setWallets(walletsResponse2.data.data || []);
        }
      }
    } catch (err) {
      console.error('Error fetching dashboard data:', err);
      setError('Failed to load dashboard data. Please check your connection.');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-EU', {
      style: 'currency',
      currency: 'EUR',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2
    }).format(amount || 0);
  };

  const formatPercentage = (value) => {
    return `${(value || 0).toFixed(2)}%`;
  };

  const getTopAssets = () => {
    if (!portfolioData?.assets) return [];
    return portfolioData.assets
      .sort((a, b) => (b.balance || 0) - (a.balance || 0))
      .slice(0, 5);
  };

  const getRecentActivity = () => {
    if (!portfolioData?.recent_transactions) return [];
    return portfolioData.recent_transactions.slice(0, 5);
  };

  if (loading) {
    return (
      <div className="dashboard-loading">
        <LoadingSpinner size="lg" />
        <p className="text-secondary mt-4">Loading your portfolio...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="dashboard-error">
        <div className="card">
          <div className="card-body text-center">
            <div className="error-icon">⚠️</div>
            <h3 className="mb-4">Unable to Load Dashboard</h3>
            <p className="text-secondary mb-6">{error}</p>
            <button 
              className="btn btn-primary"
              onClick={fetchDashboardData}
            >
              Try Again
            </button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="dashboard fade-in">
      {/* Header */}
      <div className="dashboard-header mb-8">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="mb-2">Portfolio Overview</h1>
            <p className="text-secondary">
              Track your crypto investments across all wallets
            </p>
          </div>
          <button 
            className="btn btn-outline"
            onClick={fetchDashboardData}
            disabled={loading}
          >
            <span className="refresh-icon">🔄</span>
            Refresh
          </button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="stats-grid grid grid-cols-4 mb-8">
        <StatsCard
          title="Total Balance"
          value={formatCurrency(totalBalance)}
          icon="💰"
          trend={portfolioData?.balance_change_24h}
          className="slide-in-left"
        />
        <StatsCard
          title="Active Wallets"
          value={wallets.length}
          icon="💼"
          subtitle={`${wallets.filter(w => w.is_active).length} synchronized`}
          className="slide-in-left"
          style={{ animationDelay: '0.1s' }}
        />
        <StatsCard
          title="Total Assets"
          value={portfolioData?.total_assets || 0}
          icon="📈"
          subtitle="Different cryptocurrencies"
          className="slide-in-left"
          style={{ animationDelay: '0.2s' }}
        />
        <StatsCard
          title="24h Change"
          value={formatPercentage(portfolioData?.change_24h)}
          icon={portfolioData?.change_24h >= 0 ? "📈" : "📉"}
          trend={portfolioData?.change_24h}
          className="slide-in-left"
          style={{ animationDelay: '0.3s' }}
        />
      </div>

      <div className="grid grid-cols-3 gap-6">
        {/* Portfolio Chart */}
        <div className="col-span-2">
          <div className="card slide-in-right">
            <div className="card-header">
              <h3>Portfolio Distribution</h3>
              <p className="text-secondary">Asset allocation by value</p>
            </div>
            <div className="card-body">
              <PortfolioChart data={getTopAssets()} />
            </div>
          </div>
        </div>

        {/* Top Assets */}
        <div className="col-span-1">
          <div className="card slide-in-right" style={{ animationDelay: '0.1s' }}>
            <div className="card-header">
              <h3>Top Assets</h3>
              <p className="text-secondary">By portfolio value</p>
            </div>
            <div className="card-body">
              <div className="assets-list">
                {getTopAssets().map((asset, index) => (
                  <div key={asset.symbol} className="asset-item">
                    <div className="asset-info">
                      <div className="asset-symbol">{asset.symbol}</div>
                      <div className="asset-name text-muted">{asset.name}</div>
                    </div>
                    <div className="asset-value text-right">
                      <div className="value-primary">
                        {formatCurrency(asset.balance)}
                      </div>
                      <div className="value-secondary text-muted">
                        {asset.quantity?.toFixed(6)} {asset.symbol}
                      </div>
                    </div>
                  </div>
                ))}
                {getTopAssets().length === 0 && (
                  <div className="empty-state">
                    <p className="text-muted text-center">No assets found</p>
                    <Link to="/wallets" className="btn btn-sm btn-primary">
                      Add Wallet
                    </Link>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Wallets Overview and Recent Activity */}
      <div className="grid grid-cols-2 gap-6 mt-6">
        {/* Wallets Overview */}
        <div className="card slide-in-left" style={{ animationDelay: '0.2s' }}>
          <div className="card-header">
            <div className="flex justify-between items-center">
              <div>
                <h3>Wallets</h3>
                <p className="text-secondary">Connected exchanges and wallets</p>
              </div>
              <Link to="/wallets" className="btn btn-sm btn-outline">
                View All
              </Link>
            </div>
          </div>
          <div className="card-body">
            <div className="wallets-list">
              {wallets.slice(0, 4).map((wallet) => (
                <Link
                  key={wallet.id}
                  to={`/wallets/${wallet.id}`}
                  className="wallet-item"
                >
                  <div className="wallet-info">
                    <div className="wallet-icon">
                      {wallet.type === 'kraken' ? '🐙' : '💼'}
                    </div>
                    <div>
                      <div className="wallet-name">{wallet.name}</div>
                      <div className="wallet-type text-muted">{wallet.type}</div>
                    </div>
                  </div>
                  <div className="wallet-status">
                    <div className={`status-badge ${wallet.is_active ? 'active' : 'inactive'}`}>
                      {wallet.is_active ? 'Active' : 'Inactive'}
                    </div>
                    <div className="wallet-balance text-muted">
                      {formatCurrency(wallet.balance || 0)}
                    </div>
                  </div>
                </Link>
              ))}
              {wallets.length === 0 && (
                <div className="empty-state">
                  <p className="text-muted text-center mb-4">
                    No wallets connected
                  </p>
                  <Link to="/wallets" className="btn btn-primary">
                    Add Your First Wallet
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="card slide-in-right" style={{ animationDelay: '0.2s' }}>
          <div className="card-header">
            <h3>Recent Activity</h3>
            <p className="text-secondary">Latest transactions</p>
          </div>
          <div className="card-body">
            <div className="activity-list">
              {getRecentActivity().map((transaction, index) => (
                <div key={index} className="activity-item">
                  <div className="activity-icon">
                    {transaction.type === 'buy' ? '📈' : '📉'}
                  </div>
                  <div className="activity-info">
                    <div className="activity-description">
                      {transaction.type === 'buy' ? 'Bought' : 'Sold'} {transaction.asset}
                    </div>
                    <div className="activity-time text-muted">
                      {new Date(transaction.timestamp).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="activity-amount">
                    <div className={`amount ${transaction.type === 'buy' ? 'positive' : 'negative'}`}>
                      {formatCurrency(transaction.amount)}
                    </div>
                  </div>
                </div>
              ))}
              {getRecentActivity().length === 0 && (
                <div className="empty-state">
                  <p className="text-muted text-center">No recent activity</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <style jsx>{`
        .dashboard-loading,
        .dashboard-error {
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

        .dashboard-header {
          border-bottom: 1px solid var(--dark-border);
          padding-bottom: 2rem;
        }

        .refresh-icon {
          margin-right: 0.5rem;
          display: inline-block;
          transition: transform 0.3s ease;
        }

        .btn:hover .refresh-icon {
          transform: rotate(180deg);
        }

        .stats-grid {
          gap: 1.5rem;
        }

        .assets-list,
        .wallets-list,
        .activity-list {
          display: flex;
          flex-direction: column;
          gap: 1rem;
        }

        .asset-item,
        .activity-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1rem;
          border-radius: var(--border-radius);
          background: rgba(59, 130, 246, 0.05);
          border: 1px solid transparent;
          transition: var(--transition);
        }

        .asset-item:hover,
        .activity-item:hover {
          border-color: var(--primary-blue);
          background: rgba(59, 130, 246, 0.1);
        }

        .wallet-item {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1rem;
          border-radius: var(--border-radius);
          background: rgba(59, 130, 246, 0.05);
          border: 1px solid transparent;
          transition: var(--transition);
          text-decoration: none;
          color: inherit;
        }

        .wallet-item:hover {
          border-color: var(--primary-blue);
          background: rgba(59, 130, 246, 0.1);
          transform: translateY(-1px);
        }

        .asset-info,
        .wallet-info,
        .activity-info {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .asset-symbol,
        .wallet-name,
        .activity-description {
          font-weight: 600;
          color: var(--text-primary);
        }

        .asset-name,
        .wallet-type,
        .activity-time {
          font-size: 0.875rem;
          color: var(--text-muted);
        }

        .wallet-icon,
        .activity-icon {
          font-size: 1.5rem;
          width: 2.5rem;
          height: 2.5rem;
          display: flex;
          align-items: center;
          justify-content: center;
          border-radius: 50%;
          background: var(--primary-blue);
          color: white;
        }

        .value-primary,
        .amount {
          font-weight: 600;
          color: var(--text-primary);
        }

        .value-secondary {
          font-size: 0.875rem;
        }

        .status-badge {
          padding: 0.25rem 0.75rem;
          border-radius: 9999px;
          font-size: 0.75rem;
          font-weight: 500;
        }

        .status-badge.active {
          background: var(--success);
          color: white;
        }

        .status-badge.inactive {
          background: var(--dark-border);
          color: var(--text-muted);
        }

        .amount.positive {
          color: var(--success);
        }

        .amount.negative {
          color: var(--error);
        }

        .empty-state {
          text-align: center;
          padding: 2rem;
        }

        @media (max-width: 1024px) {
          .grid-cols-4 {
            grid-template-columns: repeat(2, 1fr);
          }
          
          .grid-cols-3 {
            grid-template-columns: 1fr;
          }
          
          .col-span-2,
          .col-span-1 {
            grid-column: span 1;
          }
        }

        @media (max-width: 768px) {
          .stats-grid {
            grid-template-columns: 1fr;
          }
          
          .grid-cols-2 {
            grid-template-columns: 1fr;
          }
          
          .dashboard-header .flex {
            flex-direction: column;
            align-items: flex-start;
            gap: 1rem;
          }
          
          .asset-item,
          .wallet-item,
          .activity-item {
            flex-direction: column;
            align-items: flex-start;
            gap: 0.5rem;
          }
          
          .asset-value,
          .wallet-status {
            text-align: left;
            width: 100%;
          }
        }
      `}</style>
    </div>
  );
};

export default Dashboard;
