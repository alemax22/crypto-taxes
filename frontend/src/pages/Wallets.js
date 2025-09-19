import React, { useState, useEffect, useCallback } from 'react';
import { Card, Button, Alert, Spinner, Modal, Form, Badge, Dropdown } from 'react-bootstrap';
import axios from 'axios';

const Wallets = () => {
  const [wallets, setWallets] = useState([]);
  const [portfolios, setPortfolios] = useState([]);
  const [selectedPortfolio, setSelectedPortfolio] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState(null);
  const [showAddModal, setShowAddModal] = useState(false);
  const [addingWallet, setAddingWallet] = useState(false);
  const [sortBy, setSortBy] = useState('created_datetime');
  const [searchTerm, setSearchTerm] = useState('');

  // Add wallet form state
  const [newWallet, setNewWallet] = useState({
    wallet_type: 'KrakenWallet',
    name: '',
    description: '',
    api_key: '',
    api_secret: '',
    reference_fiat: 'EUR'
  });

  // Fetch portfolios on component mount
  const fetchPortfolios = useCallback(async () => {
    try {
      const response = await axios.get('/portfolios');
      if (response.data.success && response.data.portfolios.length > 0) {
        setPortfolios(response.data.portfolios);
        // Select first portfolio by default
        const firstPortfolio = response.data.portfolios[0];
        setSelectedPortfolio(firstPortfolio);
        return firstPortfolio.portfolio_id;
      }
    } catch (err) {
      console.error('Error fetching portfolios:', err);
      setError('Failed to fetch portfolios');
    }
    return null;
  }, []);

  // Fetch wallets for selected portfolio
  const fetchWallets = useCallback(async (portfolioId) => {
    if (!portfolioId) return;
    
    try {
      setLoading(true);
      const response = await axios.get(`/portfolios/${portfolioId}/wallets`);
      if (response.data.success) {
        setWallets(response.data.wallets || []);
      }
    } catch (err) {
      console.error('Error fetching wallets:', err);
      setError('Failed to fetch wallets');
    } finally {
      setLoading(false);
    }
  }, []);

  // Initialize data
  useEffect(() => {
    const initializeData = async () => {
      const portfolioId = await fetchPortfolios();
      if (portfolioId) {
        await fetchWallets(portfolioId);
      }
    };
    initializeData();
  }, [fetchPortfolios, fetchWallets]);

  // Sync all wallets
  const handleSyncAll = async () => {
    if (!selectedPortfolio) return;
    
    setSyncing(true);
    setError(null);
    
    try {
      const response = await axios.post(`/portfolios/${selectedPortfolio.portfolio_id}/wallets/synchronize`);
      if (response.data.success) {
        // Refresh wallet data after sync
        await fetchWallets(selectedPortfolio.portfolio_id);
      } else {
        setError(response.data.error || 'Synchronization failed');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to synchronize wallets');
    } finally {
      setSyncing(false);
    }
  };

  // Add new wallet
  const handleAddWallet = async (e) => {
    e.preventDefault();
    if (!selectedPortfolio) return;

    setAddingWallet(true);
    setError(null);

    try {
      const response = await axios.post(`/portfolios/${selectedPortfolio.portfolio_id}/wallets`, newWallet);
      if (response.data.success) {
        setShowAddModal(false);
        setNewWallet({
          wallet_type: 'KrakenWallet',
          name: '',
          description: '',
          api_key: '',
          api_secret: '',
          reference_fiat: 'EUR'
        });
        // Refresh wallet list
        await fetchWallets(selectedPortfolio.portfolio_id);
      } else {
        setError(response.data.error || 'Failed to add wallet');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to add wallet');
    } finally {
      setAddingWallet(false);
    }
  };

  // Delete wallet
  const handleDeleteWallet = async (walletId) => {
    if (!selectedPortfolio || !window.confirm('Are you sure you want to delete this wallet?')) return;

    try {
      const response = await axios.delete(`/portfolios/${selectedPortfolio.portfolio_id}/wallets/${walletId}`);
      if (response.data.success) {
        // Refresh wallet list
        await fetchWallets(selectedPortfolio.portfolio_id);
      } else {
        setError(response.data.error || 'Failed to delete wallet');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'Failed to delete wallet');
    }
  };

  // Get status badge
  const getStatusBadge = (wallet) => {
    const syncStatus = wallet.sync_status || 'NOT_SYNCHRONIZED';
    const updatedTime = wallet.updated_datetime;
    
    if (syncStatus === 'COMPLETED' && updatedTime) {
      const lastSync = new Date(updatedTime);
      const now = new Date();
      const diffHours = (now - lastSync) / (1000 * 60 * 60);
      
      if (diffHours < 24) {
        return <Badge bg="success">SYNCED</Badge>;
      } else {
        return <Badge bg="warning">⚠ {Math.floor(diffHours / 24)} days ago</Badge>;
      }
    } else if (syncStatus === 'IN_PROGRESS') {
      return <Badge bg="info">SYNCING...</Badge>;
    } else if (syncStatus === 'FAILED') {
      return <Badge bg="danger">SYNC FAILED</Badge>;
    } else {
      return <Badge bg="secondary">NOT SYNCHRONIZED</Badge>;
    }
  };

  // Format currency
  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('en-EU', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount || 0);
  };

  // Get wallet icon
  const getWalletIcon = (walletType) => {
    if (walletType === 'KrakenWallet') {
      return '🐙'; // Kraken emoji
    }
    return '💼'; // Default wallet emoji
  };

  // Filter and sort wallets
  const filteredAndSortedWallets = [...wallets]
    .filter(wallet => 
      wallet.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (wallet.description || '').toLowerCase().includes(searchTerm.toLowerCase()) ||
      wallet.wallet_type.toLowerCase().includes(searchTerm.toLowerCase())
    )
    .sort((a, b) => {
      switch (sortBy) {
        case 'name':
          return a.name.localeCompare(b.name);
        case 'created_datetime':
          return new Date(b.created_datetime) - new Date(a.created_datetime);
        case 'updated_datetime':
          return new Date(b.updated_datetime || 0) - new Date(a.updated_datetime || 0);
        default:
          return 0;
      }
    });

  return (
    <div className="wallets-page">
      {/* Header */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div className="d-flex align-items-center">
          <h1 className="me-3">Wallets</h1>
          <Badge bg="secondary" className="fs-6">{wallets.length}</Badge>
        </div>
        <div className="d-flex gap-3">
          <Button 
            variant="outline-primary" 
            onClick={handleSyncAll}
            disabled={syncing || wallets.length === 0}
            className="d-flex align-items-center"
          >
            {syncing ? (
              <>
                <Spinner animation="border" size="sm" className="me-2" />
                Sync all
              </>
            ) : (
              <>
                <i className="bi bi-arrow-clockwise me-2"></i>
                Sync all
              </>
            )}
          </Button>
          <Button 
            variant="primary" 
            onClick={() => setShowAddModal(true)}
            className="d-flex align-items-center"
          >
            <span className="me-2">+</span>
            Add wallet / exchange
          </Button>
        </div>
      </div>

      {/* Search and Sort */}
      <div className="d-flex justify-content-between align-items-center mb-4">
        <div className="search-container position-relative">
          <i className="bi bi-search position-absolute top-50 start-0 translate-middle-y ms-3 text-muted"></i>
          <Form.Control
            type="text"
            placeholder="Find wallet..."
            className="search-input ps-5"
            style={{ width: '300px' }}
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
        <Dropdown>
          <Dropdown.Toggle variant="outline-secondary" id="sort-dropdown" className="d-flex align-items-center">
            <i className="bi bi-clock-history me-2"></i>
            Sort by {sortBy === 'name' ? 'Name' : sortBy === 'updated_datetime' ? 'Last Sync' : 'Date Added'}
          </Dropdown.Toggle>
          <Dropdown.Menu>
            <Dropdown.Item onClick={() => setSortBy('created_datetime')}>
              <i className="bi bi-calendar-plus me-2"></i>
              Date Added
            </Dropdown.Item>
            <Dropdown.Item onClick={() => setSortBy('updated_datetime')}>
              <i className="bi bi-arrow-clockwise me-2"></i>
              Last Sync
            </Dropdown.Item>
            <Dropdown.Item onClick={() => setSortBy('name')}>
              <i className="bi bi-sort-alpha-down me-2"></i>
              Name
            </Dropdown.Item>
          </Dropdown.Menu>
        </Dropdown>
      </div>

      {/* Error Alert */}
      {error && (
        <Alert variant="danger" className="mb-4" dismissible onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Wallets List */}
      {loading ? (
        <div className="text-center py-5">
          <Spinner animation="border" role="status">
            <span className="visually-hidden">Loading...</span>
          </Spinner>
        </div>
      ) : (
        <div className="wallets-grid">
          {filteredAndSortedWallets.map((wallet) => (
            <Card key={wallet.wallet_id} className="wallet-card">
              <Card.Body className="d-flex justify-content-between align-items-center">
                <div className="d-flex align-items-center">
                  <div className="wallet-icon me-3">
                    {getWalletIcon(wallet.wallet_type)}
                  </div>
                  <div>
                    <h5 className="mb-1">{wallet.name}</h5>
                    <div className="d-flex align-items-center mb-2">
                      {getStatusBadge(wallet)}
                      {wallet.updated_datetime && (
                        <small className="text-muted ms-2">
                          {new Date(wallet.updated_datetime).toLocaleDateString()}
                        </small>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="text-end">
                  <div className="wallet-value mb-2">
                    <div className="value-amount">{formatCurrency(0)}</div>
                    <div className="value-label">Total value</div>
                  </div>
                  <Dropdown>
                    <Dropdown.Toggle variant="link" className="text-muted p-0 border-0 bg-transparent">
                      <i className="bi bi-three-dots-vertical"></i>
                    </Dropdown.Toggle>
                    <Dropdown.Menu align="end">
                      <Dropdown.Item onClick={() => handleSyncAll()}>
                        <i className="bi bi-arrow-clockwise me-2"></i>
                        Sync wallet
                      </Dropdown.Item>
                      <Dropdown.Item onClick={() => {}}>
                        <i className="bi bi-eye me-2"></i>
                        View details
                      </Dropdown.Item>
                      <Dropdown.Divider />
                      <Dropdown.Item 
                        className="text-danger" 
                        onClick={() => handleDeleteWallet(wallet.wallet_id)}
                      >
                        <i className="bi bi-trash me-2"></i>
                        Delete wallet
                      </Dropdown.Item>
                    </Dropdown.Menu>
                  </Dropdown>
                </div>
              </Card.Body>
              
              <div className="wallet-details">
                <div className="d-flex justify-content-between text-muted small">
                  <span>0 transactions</span>
                  <span>
                    {wallet.created_datetime ? 
                      `${Math.floor((new Date() - new Date(wallet.created_datetime)) / (1000 * 60 * 60 * 24))} days ago` : 
                      'Unknown'
                    }
                  </span>
                </div>
              </div>
            </Card>
          ))}
          
          {filteredAndSortedWallets.length === 0 && wallets.length > 0 && (
            <div className="text-center py-5">
              <h5>No wallets match your search</h5>
              <p className="text-muted">Try adjusting your search terms</p>
            </div>
          )}
          
          {wallets.length === 0 && (
            <div className="text-center py-5">
              <h5>No wallets found</h5>
              <p className="text-muted">Add your first wallet to get started</p>
              <Button variant="primary" onClick={() => setShowAddModal(true)}>
                Add wallet / exchange
              </Button>
            </div>
          )}
        </div>
      )}

      {/* Add Wallet Modal */}
      <Modal show={showAddModal} onHide={() => setShowAddModal(false)} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Add wallet / exchange</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleAddWallet}>
          <Modal.Body>
            <Form.Group className="mb-3">
              <Form.Label>Exchange Type</Form.Label>
              <Form.Select
                value={newWallet.wallet_type}
                onChange={(e) => setNewWallet({...newWallet, wallet_type: e.target.value})}
                required
              >
                <option value="KrakenWallet">Kraken</option>
              </Form.Select>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Wallet Name</Form.Label>
              <Form.Control
                type="text"
                value={newWallet.name}
                onChange={(e) => setNewWallet({...newWallet, name: e.target.value})}
                placeholder="e.g., My Kraken Account"
                required
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Description (Optional)</Form.Label>
              <Form.Control
                type="text"
                value={newWallet.description}
                onChange={(e) => setNewWallet({...newWallet, description: e.target.value})}
                placeholder="Optional description"
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>API Key</Form.Label>
              <Form.Control
                type="text"
                value={newWallet.api_key}
                onChange={(e) => setNewWallet({...newWallet, api_key: e.target.value})}
                placeholder="Enter your API key"
                required
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>API Secret</Form.Label>
              <Form.Control
                type="password"
                value={newWallet.api_secret}
                onChange={(e) => setNewWallet({...newWallet, api_secret: e.target.value})}
                placeholder="Enter your API secret"
                required
              />
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>Reference Currency</Form.Label>
              <Form.Select
                value={newWallet.reference_fiat}
                onChange={(e) => setNewWallet({...newWallet, reference_fiat: e.target.value})}
                required
              >
                <option value="EUR">EUR</option>
                <option value="USD">USD</option>
                <option value="GBP">GBP</option>
              </Form.Select>
            </Form.Group>

            <Alert variant="info">
              <strong>Required Permissions:</strong> Your API key needs Query Funds, Query Open Orders & Trades, and Query Ledgers permissions.
            </Alert>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={() => setShowAddModal(false)}>
              Cancel
            </Button>
            <Button 
              type="submit" 
              variant="primary" 
              disabled={addingWallet}
            >
              {addingWallet ? (
                <>
                  <Spinner animation="border" size="sm" className="me-2" />
                  Adding...
                </>
              ) : (
                'Add Wallet'
              )}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </div>
  );
};

export default Wallets;
