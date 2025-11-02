import React, { useState, useMemo } from 'react';

const TransactionTable = ({ transactions = [], walletName }) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [filterType, setFilterType] = useState('all');
  const [sortField, setSortField] = useState('timestamp');
  const [sortDirection, setSortDirection] = useState('desc');
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(25);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-EU', {
      style: 'currency',
      currency: 'EUR'
    }).format(Math.abs(amount) || 0);
  };

  const formatDate = (dateString) => {
    if (!dateString) return 'Unknown';
    return new Date(dateString).toLocaleString('en-EU', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getTransactionTypeInfo = (transaction) => {
    const type = transaction.type?.toLowerCase() || 'unknown';
    
    switch (type) {
      case 'buy':
      case 'trade_buy':
        return { label: 'Buy', icon: '📈', color: 'var(--success)' };
      case 'sell':
      case 'trade_sell':
        return { label: 'Sell', icon: '📉', color: 'var(--error)' };
      case 'deposit':
        return { label: 'Deposit', icon: '⬇️', color: 'var(--primary-blue)' };
      case 'withdrawal':
        return { label: 'Withdrawal', icon: '⬆️', color: 'var(--warning)' };
      case 'staking':
        return { label: 'Staking', icon: '🔒', color: 'var(--success)' };
      case 'reward':
        return { label: 'Reward', icon: '🎁', color: 'var(--success)' };
      default:
        return { label: 'Other', icon: '🔄', color: 'var(--text-muted)' };
    }
  };

  const filteredAndSortedTransactions = useMemo(() => {
    let filtered = [...transactions];

    // Apply search filter
    if (searchTerm) {
      filtered = filtered.filter(tx =>
        tx.asset?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        tx.type?.toLowerCase().includes(searchTerm.toLowerCase()) ||
        tx.description?.toLowerCase().includes(searchTerm.toLowerCase())
      );
    }

    // Apply type filter
    if (filterType !== 'all') {
      filtered = filtered.filter(tx => {
        const type = tx.type?.toLowerCase() || '';
        switch (filterType) {
          case 'trades':
            return type.includes('buy') || type.includes('sell');
          case 'deposits':
            return type === 'deposit';
          case 'withdrawals':
            return type === 'withdrawal';
          case 'rewards':
            return type === 'staking' || type === 'reward';
          default:
            return true;
        }
      });
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      if (sortField === 'timestamp' || sortField === 'date') {
        aVal = new Date(aVal || 0);
        bVal = new Date(bVal || 0);
      } else if (sortField === 'amount') {
        aVal = Math.abs(aVal || 0);
        bVal = Math.abs(bVal || 0);
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  }, [transactions, searchTerm, filterType, sortField, sortDirection]);

  const paginatedTransactions = useMemo(() => {
    const startIndex = (currentPage - 1) * itemsPerPage;
    return filteredAndSortedTransactions.slice(startIndex, startIndex + itemsPerPage);
  }, [filteredAndSortedTransactions, currentPage, itemsPerPage]);

  const totalPages = Math.ceil(filteredAndSortedTransactions.length / itemsPerPage);

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('desc');
    }
    setCurrentPage(1);
  };

  const getTransactionStats = () => {
    return {
      total: filteredAndSortedTransactions.length,
      totalVolume: filteredAndSortedTransactions.reduce((sum, tx) => sum + Math.abs(tx.amount || 0), 0),
      types: filteredAndSortedTransactions.reduce((acc, tx) => {
        const type = tx.type?.toLowerCase() || 'unknown';
        acc[type] = (acc[type] || 0) + 1;
        return acc;
      }, {})
    };
  };

  const stats = getTransactionStats();

  const SortableHeader = ({ field, children }) => (
    <th 
      className="sortable-header"
      onClick={() => handleSort(field)}
    >
      <div className="header-content">
        <span>{children}</span>
        {sortField === field && (
          <span className="sort-indicator">
            {sortDirection === 'asc' ? '↑' : '↓'}
          </span>
        )}
      </div>
    </th>
  );

  if (transactions.length === 0) {
    return (
      <div className="transaction-table">
        <div className="card">
          <div className="card-body">
            <div className="empty-transactions">
              <div className="empty-icon">📊</div>
              <h3>No Transactions Found</h3>
              <p className="text-secondary">
                {walletName} doesn't have any transactions yet. 
                Try syncing the wallet to fetch the latest data.
              </p>
            </div>
          </div>
        </div>
        
        <style jsx>{`
          .empty-transactions {
            text-align: center;
            padding: 4rem 2rem;
          }

          .empty-icon {
            font-size: 4rem;
            margin-bottom: 1.5rem;
            opacity: 0.6;
          }

          .empty-transactions h3 {
            margin-bottom: 1rem;
            color: var(--text-primary);
          }
        `}</style>
      </div>
    );
  }

  return (
    <div className="transaction-table">
      {/* Stats Summary */}
      <div className="transaction-stats card mb-4">
        <div className="card-body">
          <div className="stats-grid">
            <div className="stat-item">
              <div className="stat-value">{stats.total}</div>
              <div className="stat-label">Transactions</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{formatCurrency(stats.totalVolume)}</div>
              <div className="stat-label">Total Volume</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">{Object.keys(stats.types).length}</div>
              <div className="stat-label">Transaction Types</div>
            </div>
            <div className="stat-item">
              <div className="stat-value">
                {transactions.length > 0 ? formatDate(
                  Math.max(...transactions.map(tx => new Date(tx.timestamp || tx.date || 0)))
                ) : 'Never'}
              </div>
              <div className="stat-label">Latest Transaction</div>
            </div>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="transaction-filters card mb-4">
        <div className="card-body">
          <div className="filters-row">
            <div className="search-container">
              <div className="search-input-wrapper">
                <span className="search-icon">🔍</span>
                <input
                  type="text"
                  placeholder="Search transactions..."
                  className="input search-input"
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setCurrentPage(1);
                  }}
                />
              </div>
            </div>
            
            <div className="filter-controls">
              <select
                className="input filter-select"
                value={filterType}
                onChange={(e) => {
                  setFilterType(e.target.value);
                  setCurrentPage(1);
                }}
              >
                <option value="all">All Types</option>
                <option value="trades">Trades</option>
                <option value="deposits">Deposits</option>
                <option value="withdrawals">Withdrawals</option>
                <option value="rewards">Rewards</option>
              </select>
              
              <select
                className="input filter-select"
                value={itemsPerPage}
                onChange={(e) => {
                  setItemsPerPage(Number(e.target.value));
                  setCurrentPage(1);
                }}
              >
                <option value={25}>25 per page</option>
                <option value={50}>50 per page</option>
                <option value={100}>100 per page</option>
              </select>
            </div>
          </div>
        </div>
      </div>

      {/* Transactions Table */}
      <div className="card">
        <div className="card-header">
          <h3>Transaction History</h3>
          <p className="text-secondary">
            Showing {paginatedTransactions.length} of {filteredAndSortedTransactions.length} transactions
          </p>
        </div>
        <div className="card-body p-0">
          <div className="table-container">
            <table className="transactions-table">
              <thead>
                <tr>
                  <SortableHeader field="timestamp">Date & Time</SortableHeader>
                  <th>Type</th>
                  <SortableHeader field="asset">Asset</SortableHeader>
                  <SortableHeader field="quantity">Quantity</SortableHeader>
                  <SortableHeader field="price">Price</SortableHeader>
                  <SortableHeader field="amount">Amount</SortableHeader>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {paginatedTransactions.map((transaction, index) => {
                  const typeInfo = getTransactionTypeInfo(transaction);
                  return (
                    <tr key={transaction.id || index} className="transaction-row">
                      <td className="date-cell">
                        {formatDate(transaction.timestamp || transaction.date)}
                      </td>
                      <td className="type-cell">
                        <div className="transaction-type">
                          <span className="type-icon">{typeInfo.icon}</span>
                          <span 
                            className="type-label"
                            style={{ color: typeInfo.color }}
                          >
                            {typeInfo.label}
                          </span>
                        </div>
                      </td>
                      <td className="asset-cell">
                        <div className="asset-info">
                          <span className="asset-symbol">{transaction.asset || 'Unknown'}</span>
                        </div>
                      </td>
                      <td className="quantity-cell">
                        {transaction.quantity ? (
                          <span className="quantity-value">
                            {Math.abs(transaction.quantity).toFixed(8)}
                          </span>
                        ) : (
                          <span className="text-muted">-</span>
                        )}
                      </td>
                      <td className="price-cell">
                        {transaction.price ? (
                          <span className="price-value">
                            {formatCurrency(transaction.price)}
                          </span>
                        ) : (
                          <span className="text-muted">-</span>
                        )}
                      </td>
                      <td className="amount-cell">
                        <span 
                          className={`amount-value ${
                            (transaction.amount || 0) >= 0 ? 'positive' : 'negative'
                          }`}
                        >
                          {formatCurrency(transaction.amount)}
                        </span>
                      </td>
                      <td className="status-cell">
                        <span className="status-badge completed">
                          ✅ Completed
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="card-footer">
            <div className="pagination-container">
              <div className="pagination-info">
                Showing {((currentPage - 1) * itemsPerPage) + 1} to {Math.min(currentPage * itemsPerPage, filteredAndSortedTransactions.length)} of {filteredAndSortedTransactions.length} transactions
              </div>
              
              <div className="pagination-controls">
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => setCurrentPage(1)}
                  disabled={currentPage === 1}
                >
                  First
                </button>
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => setCurrentPage(currentPage - 1)}
                  disabled={currentPage === 1}
                >
                  Previous
                </button>
                
                <div className="page-numbers">
                  {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                    const pageNum = Math.max(1, Math.min(totalPages - 4, currentPage - 2)) + i;
                    return (
                      <button
                        key={pageNum}
                        className={`btn btn-sm ${pageNum === currentPage ? 'btn-primary' : 'btn-outline'}`}
                        onClick={() => setCurrentPage(pageNum)}
                      >
                        {pageNum}
                      </button>
                    );
                  })}
                </div>
                
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => setCurrentPage(currentPage + 1)}
                  disabled={currentPage === totalPages}
                >
                  Next
                </button>
                <button
                  className="btn btn-outline btn-sm"
                  onClick={() => setCurrentPage(totalPages)}
                  disabled={currentPage === totalPages}
                >
                  Last
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      <style jsx>{`
        .transaction-stats .stats-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: 2rem;
        }

        .stat-item {
          text-align: center;
        }

        .stat-value {
          font-size: 1.5rem;
          font-weight: 700;
          color: var(--text-primary);
          margin-bottom: 0.25rem;
        }

        .stat-label {
          font-size: 0.875rem;
          color: var(--text-muted);
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
          min-width: 130px;
        }

        .table-container {
          overflow-x: auto;
        }

        .transactions-table {
          width: 100%;
          border-collapse: collapse;
        }

        .transactions-table th,
        .transactions-table td {
          padding: 1rem;
          text-align: left;
          border-bottom: 1px solid var(--dark-border);
        }

        .transactions-table th {
          background: rgba(59, 130, 246, 0.05);
          font-weight: 600;
          color: var(--text-primary);
          position: sticky;
          top: 0;
          z-index: 1;
        }

        .sortable-header {
          cursor: pointer;
          transition: var(--transition);
        }

        .sortable-header:hover {
          background: rgba(59, 130, 246, 0.1);
        }

        .header-content {
          display: flex;
          align-items: center;
          justify-content: space-between;
          gap: 0.5rem;
        }

        .sort-indicator {
          font-size: 0.875rem;
          color: var(--primary-blue);
        }

        .transaction-row {
          transition: var(--transition);
        }

        .transaction-row:hover {
          background: rgba(59, 130, 246, 0.05);
        }

        .date-cell {
          font-size: 0.875rem;
          color: var(--text-secondary);
          min-width: 150px;
        }

        .transaction-type {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .type-icon {
          font-size: 1.1rem;
        }

        .type-label {
          font-weight: 500;
          font-size: 0.875rem;
        }

        .asset-info {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .asset-symbol {
          font-weight: 600;
          color: var(--text-primary);
          background: rgba(59, 130, 246, 0.1);
          padding: 0.25rem 0.5rem;
          border-radius: 4px;
          font-size: 0.75rem;
        }

        .quantity-value,
        .price-value {
          font-family: 'Courier New', monospace;
          font-size: 0.875rem;
          color: var(--text-secondary);
        }

        .amount-value {
          font-weight: 600;
          font-family: 'Courier New', monospace;
        }

        .amount-value.positive {
          color: var(--success);
        }

        .amount-value.negative {
          color: var(--error);
        }

        .status-badge {
          padding: 0.25rem 0.75rem;
          border-radius: 9999px;
          font-size: 0.75rem;
          font-weight: 500;
        }

        .status-badge.completed {
          background: rgba(16, 185, 129, 0.1);
          color: var(--success);
          border: 1px solid rgba(16, 185, 129, 0.2);
        }

        .pagination-container {
          display: flex;
          justify-content: space-between;
          align-items: center;
          gap: 1rem;
        }

        .pagination-info {
          font-size: 0.875rem;
          color: var(--text-muted);
        }

        .pagination-controls {
          display: flex;
          align-items: center;
          gap: 0.5rem;
        }

        .page-numbers {
          display: flex;
          gap: 0.25rem;
        }

        @media (max-width: 1024px) {
          .stats-grid {
            grid-template-columns: repeat(2, 1fr) !important;
          }
        }

        @media (max-width: 768px) {
          .stats-grid {
            grid-template-columns: 1fr !important;
            gap: 1rem !important;
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

          .pagination-container {
            flex-direction: column;
            gap: 1rem;
          }

          .pagination-controls {
            flex-wrap: wrap;
            justify-content: center;
          }

          .page-numbers {
            order: -1;
          }

          .transactions-table th,
          .transactions-table td {
            padding: 0.75rem 0.5rem;
            font-size: 0.875rem;
          }

          .date-cell {
            min-width: 120px;
            font-size: 0.75rem;
          }
        }

        @media (max-width: 480px) {
          .transactions-table {
            font-size: 0.75rem;
          }

          .transactions-table th,
          .transactions-table td {
            padding: 0.5rem 0.25rem;
          }

          .asset-symbol {
            font-size: 0.625rem;
          }

          .quantity-value,
          .price-value {
            font-size: 0.75rem;
          }
        }
      `}</style>
    </div>
  );
};

export default TransactionTable;
