import React, { useState, useEffect, useCallback } from 'react';
import { Card, Button, Alert, Spinner, Badge } from 'react-bootstrap';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import axios from 'axios';
import ApiKeyManager from '../components/ApiKeyManager';

const Dashboard = () => {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [balance, setBalance] = useState(null);
  const [credentialsConfigured, setCredentialsConfigured] = useState(false);

  // Memoized function to check credentials
  const checkCredentialsStatus = useCallback(async () => {
    try {
      const response = await axios.get('/api/check-credentials');
      setCredentialsConfigured(response.data.valid);
    } catch (err) {
      console.error('Failed to check credentials status:', err);
    }
  }, []);

  const fetchBalance = useCallback(async () => {
    try {
      const response = await axios.get('/api/balance');
      if (response.data.success) {
        setBalance(response.data.balance);
      }
    } catch (err) {
      console.error('Failed to fetch balance:', err);
    }
  }, []);

  const calculateTaxes = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post('/api/calculate-taxes');
      if (response.data.success) {
        setData(response.data);
      } else {
        setError(response.data.error || 'Failed to calculate taxes');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred while calculating taxes');
    } finally {
      setLoading(false);
    }
  };

  // When credentials are set, refresh status and balance
  const handleCredentialsSet = async () => {
    await checkCredentialsStatus();
    await fetchBalance();
    setData(null); // Optionally clear old data
  };

  useEffect(() => {
    checkCredentialsStatus();
    if (credentialsConfigured) {
      fetchBalance();
    }
  }, [credentialsConfigured, checkCredentialsStatus, fetchBalance]);

  const formatCurrency = (amount) => {
    return new Intl.NumberFormat('it-IT', {
      style: 'currency',
      currency: 'EUR'
    }).format(amount);
  };

  const getTotalGains = () => {
    if (!data?.gains_by_year) return 0;
    return data.gains_by_year.reduce((sum, year) => sum + (year.gain || 0), 0);
  };

  const getTotalTaxes = () => {
    if (!data?.gains_by_year) return 0;
    return data.gains_by_year.reduce((sum, year) => sum + (year.taxes || 0), 0);
  };

  const getTotalBalance = () => {
    if (!balance) return 0;
    return balance.reduce((sum, asset) => sum + (asset.balance || 0), 0);
  };

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1>Dashboard</h1>
        {credentialsConfigured && (
          <Button 
            variant="success" 
            size="lg" 
            onClick={calculateTaxes}
            disabled={loading}
            className="btn-calculate"
          >
            {loading ? (
              <>
                <Spinner animation="border" size="sm" className="me-2" />
                Calculating Taxes...
              </>
            ) : (
              'Calculate Taxes'
            )}
          </Button>
        )}
      </div>

      {/* API Key Manager */}
      <ApiKeyManager onCredentialsSet={handleCredentialsSet} />

      {error && (
        <Alert variant="danger" className="mb-4">
          <Alert.Heading>Error</Alert.Heading>
          <p>{error}</p>
        </Alert>
      )}

      {/* Statistics Cards - vertical stack */}
      <div className="d-flex flex-wrap gap-4 mb-4">
        <Card className="stats-card flex-fill">
          <div className="stats-number">{formatCurrency(getTotalGains())}</div>
          <div className="stats-label">Total Gains/Losses</div>
        </Card>
        <Card className="stats-card flex-fill">
          <div className="stats-number">{formatCurrency(getTotalTaxes())}</div>
          <div className="stats-label">Total Taxes</div>
        </Card>
        <Card className="stats-card flex-fill">
          <div className="stats-number">{data?.total_transactions || 0}</div>
          <div className="stats-label">Total Transactions</div>
        </Card>
        <Card className="stats-card flex-fill">
          <div className="stats-number">{data?.assets_in_portfolio?.length || 0}</div>
          <div className="stats-label">Assets in Portfolio</div>
        </Card>
      </div>

      {/* Tax Summary by Year Chart */}
      {data?.gains_by_year && (
        <Card className="mb-4">
          <Card.Header>Tax Summary by Year</Card.Header>
          <Card.Body>
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={data.gains_by_year}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="year" />
                <YAxis />
                <Tooltip 
                  formatter={(value, name) => [
                    formatCurrency(value), 
                    name === 'gain' ? 'Gains/Losses' : 'Taxes'
                  ]}
                />
                <Bar dataKey="gain" fill="#28a745" name="Gains/Losses" />
                <Bar dataKey="taxes" fill="#dc3545" name="Taxes" />
              </BarChart>
            </ResponsiveContainer>
          </Card.Body>
        </Card>
      )}

      {/* Current Balance */}
      {balance && (
        <Card className="mb-4">
          <Card.Header>Current Portfolio Balance</Card.Header>
          <Card.Body>
            <div className="row">
              {balance.map((asset, index) => (
                <div key={index} className="col-md-3 mb-2">
                  <div className="d-flex justify-content-between align-items-center p-2 border rounded">
                    <span className="fw-bold">{asset.assetnorm}</span>
                    <Badge bg="primary">{formatCurrency(asset.balance)}</Badge>
                  </div>
                </div>
              ))}
            </div>
          </Card.Body>
        </Card>
      )}

      {/* Recent Transactions Preview */}
      {data?.transactions && (
        <Card>
          <Card.Header>Recent Transactions</Card.Header>
          <Card.Body>
            <div className="table-responsive">
              <table className="table table-hover">
                <thead>
                  <tr>
                    <th>Date</th>
                    <th>Asset</th>
                    <th>Type</th>
                    <th>Quantity</th>
                    <th>Price (EUR)</th>
                    <th>Total (EUR)</th>
                  </tr>
                </thead>
                <tbody>
                  {data.transactions.slice(0, 10).map((tx, index) => (
                    <tr key={index}>
                      <td>{new Date(tx.datetime).toLocaleDateString('it-IT')}</td>
                      <td>
                        <Badge bg="secondary">{tx.cryptocur}</Badge>
                      </td>
                      <td>
                        <Badge bg={tx.cryptocur === 'ZEUR' ? 'success' : 'info'}>
                          {tx.cryptocur === 'ZEUR' ? 'Buy' : 'Sell'}
                        </Badge>
                      </td>
                      <td>{Math.abs(tx.quantity).toFixed(8)}</td>
                      <td>{formatCurrency(Math.abs(tx.price))}</td>
                      <td className={tx.total > 0 ? 'profit' : 'loss'}>
                        {formatCurrency(Math.abs(tx.total))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card.Body>
        </Card>
      )}

      {/* No Data Message */}
      {credentialsConfigured && !data && !loading && (
        <Card>
          <Card.Body className="text-center">
            <h5>No Data Available</h5>
            <p className="text-muted">
              Click "Calculate Taxes" to fetch and analyze your trading data from Kraken.
            </p>
          </Card.Body>
        </Card>
      )}
    </div>
  );
};

export default Dashboard; 