import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import LoadingSpinner from '../components/LoadingSpinner';
import WalletCard from '../components/WalletCard';
import AddWalletModal from '../components/AddWalletModal';

const Wallets = () => {
  const [wallets, setWallets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');
  const [sortBy, setSortBy] = useState('name');
  const [filterBy, setFilterBy] = useState('all');

  useEffect(() => {
    fetchWallets();
  }, []);

  const fetchWallets = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await axios.get('/api/wallets');
      if (response.data.success) {
        setWallets(response.data.wallets || []);
      } else {
        setError('Failed to fetch wallets');
      }
    } catch (err) {
      console.error('Error fetching wallets:', err);
      setError('Failed to connect to the server');
    } finally {
      setLoading(false);
    }
  };

  const handleAddWallet = async (walletData) => {
    try {
      const response = await axios.post('/api/wallets', walletData);
      if (response.data.success) {
        setWallets([...wallets, response.data.wallet]);
        setShowAddModal(false);
        return { success: true };
      } else {
        return { success: false, error: response.data.error || 'Failed to add wallet' };
      }
    } catch (err) {
      console.error('Error adding wallet:', err);
      return { 
        success: false, 
        error: err.response?.data?.error || 'Failed to add wallet' 
      };
    }
  };

  const handleDeleteWallet = async (walletId) => {
    if (!window.confirm('Are you sure you want to delete this wallet?')) {
      return;
    }

    try {
      const response = await axios.delete(`/api/wallets/${walletId}`);
      if (response.data.success) {
        setWallets(wallets.filter(w => w.id !== walletId));
      } else {
        alert('Failed to delete wallet');
      }
    } catch (err) {
      console.error('Error deleting wallet:', err);
      alert('Failed to delete wallet');
    }
  };

  const handleSyncWallet = async (walletId) => {
    try {
      const response = await axios.post(`/api/wallets/${walletId}/sync`);
      if (response.data.success) {
        // Update the wallet in the list
        setWallets(wallets.map(w => 
          w.id === walletId 
            ? { ...w, last_sync: new Date().toISOString(), is_syncing: true }
            : w
        ));
      } else {
        alert('Failed to sync wallet');
      }
    } catch (err) {
      console.error('Error syncing wallet:', err);
      alert('Failed to sync wallet');
    }
  };

  const getFilteredAndSortedWallets = () => {
    let filtered = wallets;

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(wallet =>
        wallet.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
        wallet.type.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Apply status filter
    if (filterBy !== 'all') {
      filtered = filtered.filter(wallet => {
        switch (filterBy) {
          case 'active':
            return wallet.is_active;
          case 'inactive':
            return !wallet.is_active;
          case 'synced':
            return wallet.last_sync;
          case 'unsynced':
            return !wallet.last_sync;
          default:
            return true;
        }
      });
    }

    // Apply sorting
    filtered.sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'type':
          return a.type.localeCompare(b.type);
        case 'balance':
          return (b.balance || 0) - (a.balance || 0);
        case 'last_sync':
          return new Date(b.last_sync || 0) - new Date(a.last_sync || 0);
        case 'created':
        default:
          return new Date(b.created_at || 0) - new Date(a.created_at || 0);
      }
    });

    return filtered;
  };

  const getTotalBalance = () => {
    return wallets.reduce((sum, wallet) => sum + (wallet.balance || 0), 0);
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-EU', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount || 0);
  };

  const filteredWallets = getFilteredAndSortedWallets();

  if (loading) {
    return (
      <div className="wallets-loading">
        <LoadingSpinner size="lg" />
        <p className="text-secondary mt-4">Loading your wallets...</p>
      </div>
    );
  }

  return (
    <div className="wallets-page fade-in">
      {/* Header */}
      <div className="wallets-header mb-8">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="mb-2">Wallets & Exchanges</h1>
            <p className="text-secondary">
              Manage your connected wallets and track their performance
            </p>
          </div>
          <button 
            className="btn btn-primary"
            onClick={() => setShowAddModal(true)}
          >
            <span className="btn-icon">➕</span>
            Add Wallet
          </button>
        </div>

        {/* Stats Summary */}
        <div className="wallets-stats grid grid-cols-4 gap-4 mb-6">
          <div className="stat-item">
            <div className="stat-value">{wallets.length}</div>
            <div className="stat-label">Total Wallets</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{wallets.filter(w => w.is_active).length}</div>
            <div className="stat-label">Active</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{formatCurrency(getTotalBalance())}</div>
            <div className="stat-label">Total Balance</div>
          </div>
          <div className="stat-item">
            <div className="stat-value">{wallets.filter(w => w.last_sync).length}</div>
            <div className="stat-label">Synchronized</div>
          </div>
        </div>
      </div>

      {/* Filters and Search */}
      <div className="wallets-filters mb-6">
        <div className="filters-row">
          {/* Search */}
          <div className="search-container">
            <div className="search-input-wrapper">
              <span className="search-icon">🔍</span>
              <input
                type="text"
                placeholder="Search wallets..."
                className="input search-input"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>
          </div>

          {/* Filters */}
          <div className="filter-controls">
            <select
              className="input filter-select"
              value={filterBy}
              onChange={(e) => setFilterBy(e.target.value)}
            >
              <option value="all">All Wallets</option>
              <option value="active">Active Only</option>
              <option value="inactive">Inactive Only</option>
              <option value="synced">Synchronized</option>
              <option value="unsynced">Not Synchronized</option>
            </select>

            <select
              className="input filter-select"
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
            >
              <option value="created">Newest First</option>
              <option value="name">Name A-Z</option>
              <option value="type">Type</option>
              <option value="balance">Balance High-Low</option>
              <option value="last_sync">Recently Synced</option>
            </select>
          </div>
        </div>
      </div>

      {/* Error Display */}
      {error && (
        <div className="error-banner mb-6">
          <div className="error-content">
            <span className="error-icon">⚠️</span>
            <span className="error-message">{error}</span>
            <button 
              className="btn btn-sm btn-outline"
              onClick={fetchWallets}
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Wallets Grid */}
      <div className="wallets-grid">
        {filteredWallets.length > 0 ? (
          <div className="grid grid-cols-2 gap-6">
            {filteredWallets.map((wallet, index) => (
              <WalletCard
                key={wallet.id}
                wallet={wallet}
                onDelete={() => handleDeleteWallet(wallet.id)}
                onSync={() => handleSyncWallet(wallet.id)}
                className="slide-in-left"
                style={{ animationDelay: `${index * 0.1}s` }}
              />
            ))}
          </div>
        ) : (
          <div className="empty-state">
            {searchTerm || filterBy !== 'all' ? (
              <div className="empty-content">
                <div className="empty-icon">🔍</div>
                <h3>No wallets match your filters</h3>
                <p className="text-secondary mb-4">
                  Try adjusting your search or filter criteria
                </p>
                <button 
                  className="btn btn-outline"
                  onClick={() => {
                    setSearchTerm('');
                    setFilterBy('all');
                  }}
                >
                  Clear Filters
                </button>
              </div>
            ) : (
              <div className="empty-content">
                <div className="empty-icon">💼</div>
                <h3>No wallets connected yet</h3>
                <p className="text-secondary mb-4">
                  Connect your first wallet or exchange to start tracking your portfolio
                </p>
                <button 
                  className="btn btn-primary"
                  onClick={() => setShowAddModal(true)}
                >
                  <span className="btn-icon">➕</span>
                  Add Your First Wallet
                </button>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Add Wallet Modal */}
      <AddWalletModal
        isOpen={showAddModal}
        onClose={() => setShowAddModal(false)}
        onAdd={handleAddWallet}
      />

      <style jsx>{`
        .wallets-loading {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 400px;
        }

        .wallets-header {
          border-bottom: 1px solid var(--dark-border);
          padding-bottom: 2rem;
        }

        .btn-icon {
          margin-right: 0.5rem;
        }

        .wallets-stats {
          background: var(--gradient-surface);
          border: 1px solid var(--dark-border);
          border-radius: var(--border-radius-lg);
          padding: 1.5rem;
        }

        .stat-item {
          text-align: center;
          padding: 1rem;
          border-radius: var(--border-radius);
          background: rgba(59, 130, 246, 0.05);
          transition: var(--transition);
        }

        .stat-item:hover {
          background: rgba(59, 130, 246, 0.1);
          transform: translateY(-2px);
        }

        .stat-value {
          font-size: 1.75rem;
          font-weight: 700;
          color: var(--text-primary);
          margin-bottom: 0.25rem;
        }

        .stat-label {
          font-size: 0.875rem;
          color: var(--text-muted);
        }

        .wallets-filters {
          background: var(--dark-surface);
          border: 1px solid var(--dark-border);
          border-radius: var(--border-radius);
          padding: 1.5rem;
        }

        .filters-row {
          display: flex;
          gap: 1.5rem;
          align-items: center;
        }

        .search-container {
          flex: 1;
        }

        .search-input-wrapper {
          position: relative;
          display: flex;
          align-items: center;
        }

        .search-icon {
          position: absolute;
          left: 1rem;
          color: var(--text-muted);
          z-index: 1;
        }

        .search-input {
          padding-left: 2.5rem;
          width: 100%;
        }

        .filter-controls {
          display: flex;
          gap: 1rem;
        }

        .filter-select {
          min-width: 150px;
        }

        .error-banner {
          background: rgba(239, 68, 68, 0.1);
          border: 1px solid var(--error);
          border-radius: var(--border-radius);
          padding: 1rem;
        }

        .error-content {
          display: flex;
          align-items: center;
          gap: 1rem;
        }

        .error-icon {
          font-size: 1.25rem;
        }

        .error-message {
          flex: 1;
          color: var(--error);
          font-weight: 500;
        }

        .wallets-grid {
          min-height: 400px;
        }

        .empty-state {
          display: flex;
          align-items: center;
          justify-content: center;
          min-height: 400px;
        }

        .empty-content {
          text-align: center;
          max-width: 400px;
        }

        .empty-icon {
          font-size: 4rem;
          margin-bottom: 1.5rem;
          opacity: 0.6;
        }

        .empty-content h3 {
          margin-bottom: 1rem;
          color: var(--text-primary);
        }

        @media (max-width: 1024px) {
          .grid-cols-4 {
            grid-template-columns: repeat(2, 1fr);
          }
          
          .grid-cols-2 {
            grid-template-columns: 1fr;
          }
        }

        @media (max-width: 768px) {
          .wallets-header .flex {
            flex-direction: column;
            align-items: flex-start;
            gap: 1rem;
          }
          
          .wallets-stats {
            grid-template-columns: repeat(2, 1fr);
          }
          
          .filters-row {
            flex-direction: column;
            gap: 1rem;
          }
          
          .search-container,
          .filter-controls {
            width: 100%;
          }
          
          .filter-controls {
            flex-direction: column;
          }
          
          .filter-select {
            min-width: auto;
          }
          
          .error-content {
            flex-direction: column;
            text-align: center;
            gap: 0.75rem;
          }
        }

        @media (max-width: 480px) {
          .wallets-stats {
            grid-template-columns: 1fr;
          }
          
          .stat-value {
            font-size: 1.5rem;
          }
        }
      `}</style>
    </div>
  );
};

export default Wallets;
