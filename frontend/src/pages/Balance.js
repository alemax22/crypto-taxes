import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Badge, Alert, Spinner, Button } from 'react-bootstrap';
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from 'recharts';
import axios from 'axios';

const Balance = () => {
  const [balance, setBalance] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchBalance();
  }, []);

  const fetchBalance = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.get('/api/balance');
      if (response.data.success) {
        setBalance(response.data.balance);
      } else {
        setError(response.data.error || 'Failed to fetch balance');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred while fetching balance');
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

  const getTotalBalance = () => {
    if (!balance) return 0;
    return balance.reduce((sum, asset) => sum + (asset.balance || 0), 0);
  };

  const getAssetsWithBalance = () => {
    if (!balance) return [];
    return balance.filter(asset => asset.balance > 0);
  };

  const getAssetPercentage = (assetBalance) => {
    const total = getTotalBalance();
    if (total === 0) return 0;
    return ((assetBalance / total) * 100).toFixed(1);
  };

  const COLORS = [
    '#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D',
    '#FFC658', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7'
  ];

  const getBalanceClass = (amount) => {
    if (amount > 1000) return 'success';
    if (amount > 100) return 'warning';
    return 'secondary';
  };

  if (loading) {
    return (
      <div className="loading-spinner">
        <Spinner animation="border" />
        <span className="ms-2">Loading balance...</span>
      </div>
    );
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1>Portfolio Balance</h1>
        <Button variant="primary" onClick={fetchBalance} disabled={loading}>
          Refresh Balance
        </Button>
      </div>

      {error && (
        <Alert variant="danger" className="mb-4">
          <Alert.Heading>Error</Alert.Heading>
          <p>{error}</p>
        </Alert>
      )}

      {balance && (
        <>
          {/* Total Balance Card */}
          <Card className="stats-card mb-4">
            <Card.Body>
              <Row className="align-items-center">
                <Col md={8}>
                  <div className="stats-number">
                    {formatCurrency(getTotalBalance())}
                  </div>
                  <div className="stats-label">Total Portfolio Value</div>
                </Col>
                <Col md={4} className="text-end">
                  <Badge bg="light" text="dark" className="fs-6">
                    {getAssetsWithBalance().length} Assets
                  </Badge>
                </Col>
              </Row>
            </Card.Body>
          </Card>

          <Row>
            {/* Balance Chart */}
            <Col md={6}>
              <Card className="stats-card mb-4">
                <Card.Header>Portfolio Distribution</Card.Header>
                <Card.Body>
                  {getAssetsWithBalance().length > 0 ? (
                    <ResponsiveContainer width="100%" height={400}>
                      <PieChart>
                        <Pie
                          data={getAssetsWithBalance()}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ assetnorm, balance }) => 
                            `${assetnorm}: ${formatCurrency(balance)}`
                          }
                          outerRadius={120}
                          fill="#8884d8"
                          dataKey="balance"
                        >
                          {getAssetsWithBalance().map((entry, index) => (
                            <Cell 
                              key={`cell-${index}`} 
                              fill={COLORS[index % COLORS.length]} 
                            />
                          ))}
                        </Pie>
                        <Tooltip 
                          formatter={(value) => [
                            formatCurrency(value),
                            'Balance'
                          ]}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="text-center text-muted py-5">
                      <h5>No assets with balance</h5>
                      <p>Your portfolio appears to be empty</p>
                    </div>
                  )}
                </Card.Body>
              </Card>
            </Col>

            {/* Asset List */}
            <Col md={6}>
              <Card className="stats-card mb-4">
                <Card.Header>Asset Breakdown</Card.Header>
                <Card.Body>
                  {getAssetsWithBalance().length > 0 ? (
                    <div className="table-responsive">
                      <table className="table table-hover">
                        <thead>
                          <tr>
                            <th>Asset</th>
                            <th>Balance</th>
                            <th>Percentage</th>
                          </tr>
                        </thead>
                        <tbody>
                          {getAssetsWithBalance()
                            .sort((a, b) => b.balance - a.balance)
                            .map((asset, index) => (
                              <tr key={index}>
                                <td>
                                  <div className="d-flex align-items-center">
                                    <div 
                                      className="me-2"
                                      style={{
                                        width: '12px',
                                        height: '12px',
                                        backgroundColor: COLORS[index % COLORS.length],
                                        borderRadius: '50%'
                                      }}
                                    />
                                    <Badge bg="secondary">{asset.assetnorm}</Badge>
                                  </div>
                                </td>
                                <td className={getBalanceClass(asset.balance)}>
                                  <strong>{formatCurrency(asset.balance)}</strong>
                                </td>
                                <td>
                                  <small className="text-muted">
                                    {getAssetPercentage(asset.balance)}%
                                  </small>
                                </td>
                              </tr>
                            ))}
                        </tbody>
                      </table>
                    </div>
                  ) : (
                    <div className="text-center text-muted py-4">
                      <p>No assets found in your portfolio</p>
                    </div>
                  )}
                </Card.Body>
              </Card>
            </Col>
          </Row>

          {/* Asset Grid */}
          <Card className="stats-card">
            <Card.Header>Asset Overview</Card.Header>
            <Card.Body>
              <Row>
                {getAssetsWithBalance()
                  .sort((a, b) => b.balance - a.balance)
                  .map((asset, index) => (
                    <Col key={index} md={3} className="mb-3">
                      <Card className="h-100">
                        <Card.Body className="text-center">
                          <div 
                            className="mb-2"
                            style={{
                              width: '40px',
                              height: '40px',
                              backgroundColor: COLORS[index % COLORS.length],
                              borderRadius: '50%',
                              margin: '0 auto'
                            }}
                          />
                          <h6 className="mb-1">{asset.assetnorm}</h6>
                          <div className="fw-bold text-primary">
                            {formatCurrency(asset.balance)}
                          </div>
                          <small className="text-muted">
                            {getAssetPercentage(asset.balance)}% of portfolio
                          </small>
                        </Card.Body>
                      </Card>
                    </Col>
                  ))}
              </Row>
              
              {getAssetsWithBalance().length === 0 && (
                <div className="text-center text-muted py-5">
                  <h5>No assets in portfolio</h5>
                  <p>Start trading to see your assets here</p>
                </div>
              )}
            </Card.Body>
          </Card>
        </>
      )}
    </div>
  );
};

export default Balance; 