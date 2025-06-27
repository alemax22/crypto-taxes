import React, { useState, useEffect } from 'react';
import { Card, Table, Form, Row, Col, Badge, Pagination, Spinner, Alert } from 'react-bootstrap';
import axios from 'axios';

const Transactions = () => {
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [transactionsPerPage] = useState(50);
  const [filterAsset, setFilterAsset] = useState('');
  const [filterType, setFilterType] = useState('');
  const [sortField, setSortField] = useState('datetime');
  const [sortDirection, setSortDirection] = useState('desc');

  useEffect(() => {
    fetchTransactions();
  }, []);

  const fetchTransactions = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post('/api/calculate-taxes');
      if (response.data.success) {
        setTransactions(response.data.transactions || []);
      } else {
        setError(response.data.error || 'Failed to fetch transactions');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred while fetching transactions');
    } finally {
      setLoading(false);
    }
  };

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('it-IT', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount);
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString('it-IT');
  };

  const handleSort = (field) => {
    if (sortField === field) {
      setSortDirection(sortDirection === 'asc' ? 'desc' : 'asc');
    } else {
      setSortField(field);
      setSortDirection('asc');
    }
  };

  const getSortedAndFilteredTransactions = () => {
    let filtered = transactions;

    // Apply filters
    if (filterAsset) {
      filtered = filtered.filter(tx => 
        tx.cryptocur?.toLowerCase().includes(filterAsset.toLowerCase())
      );
    }

    if (filterType) {
      filtered = filtered.filter(tx => {
        if (filterType === 'buy') return tx.cryptocur === 'ZEUR';
        if (filterType === 'sell') return tx.cryptocur !== 'ZEUR';
        return true;
      });
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aVal = a[sortField];
      let bVal = b[sortField];

      if (sortField === 'datetime') {
        aVal = new Date(aVal);
        bVal = new Date(bVal);
      }

      if (aVal < bVal) return sortDirection === 'asc' ? -1 : 1;
      if (aVal > bVal) return sortDirection === 'asc' ? 1 : -1;
      return 0;
    });

    return filtered;
  };

  const sortedAndFilteredTransactions = getSortedAndFilteredTransactions();

  // Pagination
  const indexOfLastTransaction = currentPage * transactionsPerPage;
  const indexOfFirstTransaction = indexOfLastTransaction - transactionsPerPage;
  const currentTransactions = sortedAndFilteredTransactions.slice(indexOfFirstTransaction, indexOfLastTransaction);
  const totalPages = Math.ceil(sortedAndFilteredTransactions.length / transactionsPerPage);

  const getUniqueAssets = () => {
    const assets = [...new Set(transactions.map(tx => tx.cryptocur))];
    return assets.filter(asset => asset).sort();
  };

  const getTransactionType = (transaction) => {
    return transaction.cryptocur === 'ZEUR' ? 'Buy' : 'Sell';
  };

  const getTransactionTypeBadge = (transaction) => {
    const type = getTransactionType(transaction);
    return (
      <Badge bg={type === 'Buy' ? 'success' : 'info'}>
        {type}
      </Badge>
    );
  };

  const getGainLossClass = (amount) => {
    if (amount > 0) return 'profit';
    if (amount < 0) return 'loss';
    return 'neutral';
  };

  const SortableHeader = ({ field, children }) => (
    <th 
      style={{ cursor: 'pointer' }}
      onClick={() => handleSort(field)}
    >
      {children}
      {sortField === field && (
        <span className="ms-1">
          {sortDirection === 'asc' ? '↑' : '↓'}
        </span>
      )}
    </th>
  );

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1>Transactions</h1>
        <div>
          <Badge bg="secondary" className="me-2">
            Total: {transactions.length}
          </Badge>
          <Badge bg="info">
            Filtered: {sortedAndFilteredTransactions.length}
          </Badge>
        </div>
      </div>

      {error && (
        <Alert variant="danger" className="mb-4">
          <Alert.Heading>Error</Alert.Heading>
          <p>{error}</p>
        </Alert>
      )}

      {/* Filters */}
      <Card className="mb-4">
        <Card.Header>Filters</Card.Header>
        <Card.Body>
          <Row>
            <Col md={4}>
              <Form.Group>
                <Form.Label>Asset</Form.Label>
                <Form.Select
                  value={filterAsset}
                  onChange={(e) => setFilterAsset(e.target.value)}
                >
                  <option value="">All Assets</option>
                  {getUniqueAssets().map(asset => (
                    <option key={asset} value={asset}>{asset}</option>
                  ))}
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={4}>
              <Form.Group>
                <Form.Label>Transaction Type</Form.Label>
                <Form.Select
                  value={filterType}
                  onChange={(e) => setFilterType(e.target.value)}
                >
                  <option value="">All Types</option>
                  <option value="buy">Buy</option>
                  <option value="sell">Sell</option>
                </Form.Select>
              </Form.Group>
            </Col>
            <Col md={4} className="d-flex align-items-end">
              <button
                className="btn btn-outline-secondary"
                onClick={() => {
                  setFilterAsset('');
                  setFilterType('');
                }}
              >
                Clear Filters
              </button>
            </Col>
          </Row>
        </Card.Body>
      </Card>

      {/* Transactions Table */}
      <Card>
        <Card.Header>Transaction History</Card.Header>
        <Card.Body>
          {loading ? (
            <div className="loading-spinner">
              <Spinner animation="border" />
              <span className="ms-2">Loading transactions...</span>
            </div>
          ) : (
            <>
              <div className="table-responsive">
                <Table striped hover>
                  <thead>
                    <tr>
                      <SortableHeader field="datetime">Date & Time</SortableHeader>
                      <SortableHeader field="cryptocur">Asset</SortableHeader>
                      <th>Type</th>
                      <SortableHeader field="quantity">Quantity</SortableHeader>
                      <SortableHeader field="price">Price (EUR)</SortableHeader>
                      <SortableHeader field="total">Total (EUR)</SortableHeader>
                    </tr>
                  </thead>
                  <tbody>
                    {currentTransactions.map((tx, index) => (
                      <tr key={index}>
                        <td>{formatDate(tx.datetime)}</td>
                        <td>
                          <Badge bg="secondary">{tx.cryptocur}</Badge>
                        </td>
                        <td>{getTransactionTypeBadge(tx)}</td>
                        <td>{Math.abs(tx.quantity).toFixed(8)}</td>
                        <td>{formatCurrency(Math.abs(tx.price))}</td>
                        <td className={getGainLossClass(tx.total)}>
                          {formatCurrency(Math.abs(tx.total))}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>

              {/* Pagination */}
              {totalPages > 1 && (
                <div className="d-flex justify-content-center mt-4">
                  <Pagination>
                    <Pagination.First 
                      onClick={() => setCurrentPage(1)}
                      disabled={currentPage === 1}
                    />
                    <Pagination.Prev 
                      onClick={() => setCurrentPage(currentPage - 1)}
                      disabled={currentPage === 1}
                    />
                    
                    {Array.from({ length: Math.min(5, totalPages) }, (_, i) => {
                      const pageNum = Math.max(1, Math.min(totalPages - 4, currentPage - 2)) + i;
                      return (
                        <Pagination.Item
                          key={pageNum}
                          active={pageNum === currentPage}
                          onClick={() => setCurrentPage(pageNum)}
                        >
                          {pageNum}
                        </Pagination.Item>
                      );
                    })}
                    
                    <Pagination.Next 
                      onClick={() => setCurrentPage(currentPage + 1)}
                      disabled={currentPage === totalPages}
                    />
                    <Pagination.Last 
                      onClick={() => setCurrentPage(totalPages)}
                      disabled={currentPage === totalPages}
                    />
                  </Pagination>
                </div>
              )}

              <div className="text-center mt-3">
                <small className="text-muted">
                  Showing {indexOfFirstTransaction + 1} to {Math.min(indexOfLastTransaction, sortedAndFilteredTransactions.length)} of {sortedAndFilteredTransactions.length} transactions
                </small>
              </div>
            </>
          )}
        </Card.Body>
      </Card>
    </div>
  );
};

export default Transactions; 