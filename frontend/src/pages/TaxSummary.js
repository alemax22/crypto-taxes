import React, { useState, useEffect } from 'react';
import { Card, Row, Col, Table, Badge, Alert, Spinner, Button } from 'react-bootstrap';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import axios from 'axios';

const TaxSummary = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [selectedYear, setSelectedYear] = useState(null);

  useEffect(() => {
    fetchTaxData();
  }, []);

  const fetchTaxData = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await axios.post('/api/calculate-taxes');
      if (response.data.success) {
        setData(response.data);
        if (response.data.gains_by_year?.length > 0) {
          setSelectedYear(response.data.gains_by_year[0].year);
        }
      } else {
        setError(response.data.error || 'Failed to fetch tax data');
      }
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred while fetching tax data');
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

  const getGainLossClass = (amount) => {
    if (amount > 0) return 'profit';
    if (amount < 0) return 'loss';
    return 'neutral';
  };

  const getTotalGains = () => {
    if (!data?.gains_by_year) return 0;
    return data.gains_by_year.reduce((sum, year) => sum + (year.gain || 0), 0);
  };

  const getTotalTaxes = () => {
    if (!data?.gains_by_year) return 0;
    return data.gains_by_year.reduce((sum, year) => sum + (year.taxes || 0), 0);
  };

  const getYearlyData = () => {
    if (!data?.gains_by_year) return [];
    return data.gains_by_year.map(year => ({
      ...year,
      netGain: year.gain - year.taxes
    }));
  };

  const getAssetDataForYear = () => {
    if (!data?.gains_by_year_asset || !selectedYear) return [];
    return data.gains_by_year_asset
      .filter(item => item.year === selectedYear)
      .map(item => ({
        ...item,
        netGain: item.gain - item.taxes
      }));
  };

  const getTaxRate = (gain, taxes) => {
    if (gain === 0) return 0;
    return (taxes / gain) * 100;
  };

  const COLORS = ['#0088FE', '#00C49F', '#FFBB28', '#FF8042', '#8884D8', '#82CA9D'];

  if (loading) {
    return (
      <div className="loading-spinner">
        <Spinner animation="border" />
        <span className="ms-2">Calculating taxes...</span>
      </div>
    );
  }

  return (
    <div>
      <div className="d-flex justify-content-between align-items-center mb-4">
        <h1>Tax Summary</h1>
        <Button variant="primary" onClick={fetchTaxData} disabled={loading}>
          Refresh Data
        </Button>
      </div>

      {error && (
        <Alert variant="danger" className="mb-4">
          <Alert.Heading>Error</Alert.Heading>
          <p>{error}</p>
        </Alert>
      )}

      {data && (
        <>
          {/* Summary Cards */}
          <Row className="mb-4">
            <Col md={3}>
              <Card className="stats-card">
                <Card.Body>
                  <div className="stats-number">
                    {formatCurrency(getTotalGains())}
                  </div>
                  <div className="stats-label">Total Gains/Losses</div>
                </Card.Body>
              </Card>
            </Col>
            <Col md={3}>
              <Card className="stats-card">
                <Card.Body>
                  <div className="stats-number">
                    {formatCurrency(getTotalTaxes())}
                  </div>
                  <div className="stats-label">Total Taxes</div>
                </Card.Body>
              </Card>
            </Col>
            <Col md={3}>
              <Card className="stats-card">
                <Card.Body>
                  <div className="stats-number">
                    {formatCurrency(getTotalGains() - getTotalTaxes())}
                  </div>
                  <div className="stats-label">Net Gains</div>
                </Card.Body>
              </Card>
            </Col>
            <Col md={3}>
              <Card className="stats-card">
                <Card.Body>
                  <div className="stats-number">
                    {getTotalGains() > 0 ? ((getTotalTaxes() / getTotalGains()) * 100).toFixed(1) : 0}%
                  </div>
                  <div className="stats-label">Effective Tax Rate</div>
                </Card.Body>
              </Card>
            </Col>
          </Row>

          {/* Yearly Overview Chart */}
          <Card className="mb-4">
            <Card.Header>Yearly Tax Overview</Card.Header>
            <Card.Body>
              <ResponsiveContainer width="100%" height={400}>
                <BarChart data={getYearlyData()}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="year" />
                  <YAxis />
                  <Tooltip 
                    formatter={(value, name) => [
                      formatCurrency(value), 
                      name === 'gain' ? 'Gains/Losses' : 
                      name === 'taxes' ? 'Taxes' : 'Net Gains'
                    ]}
                  />
                  <Bar dataKey="gain" fill="#28a745" name="Gains/Losses" />
                  <Bar dataKey="taxes" fill="#dc3545" name="Taxes" />
                  <Bar dataKey="netGain" fill="#17a2b8" name="Net Gains" />
                </BarChart>
              </ResponsiveContainer>
            </Card.Body>
          </Card>

          {/* Yearly Tax Table */}
          <Card className="mb-4">
            <Card.Header>Tax Summary by Year</Card.Header>
            <Card.Body>
              <div className="table-responsive">
                <Table striped hover>
                  <thead>
                    <tr>
                      <th>Year</th>
                      <th>Gains/Losses (EUR)</th>
                      <th>Taxes (EUR)</th>
                      <th>Net Gains (EUR)</th>
                      <th>Tax Rate</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data.gains_by_year?.map((year, index) => (
                      <tr 
                        key={index}
                        style={{ cursor: 'pointer' }}
                        onClick={() => setSelectedYear(year.year)}
                        className={selectedYear === year.year ? 'table-active' : ''}
                      >
                        <td>
                          <Badge bg="primary">{year.year}</Badge>
                        </td>
                        <td className={getGainLossClass(year.gain)}>
                          {formatCurrency(year.gain)}
                        </td>
                        <td className="loss">
                          {formatCurrency(year.taxes)}
                        </td>
                        <td className={getGainLossClass(year.gain - year.taxes)}>
                          {formatCurrency(year.gain - year.taxes)}
                        </td>
                        <td>
                          {year.gain > 0 ? `${getTaxRate(year.gain, year.taxes).toFixed(1)}%` : '0%'}
                        </td>
                        <td>
                          {year.gain > 0 ? (
                            <Badge bg="warning">Taxable</Badge>
                          ) : (
                            <Badge bg="success">No Tax</Badge>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </Table>
              </div>
            </Card.Body>
          </Card>

          {/* Asset Breakdown for Selected Year */}
          {selectedYear && (
            <Row>
              <Col md={8}>
                <Card className="mb-4">
                  <Card.Header>Asset Breakdown for {selectedYear}</Card.Header>
                  <Card.Body>
                    <div className="table-responsive">
                      <Table striped hover>
                        <thead>
                          <tr>
                            <th>Asset</th>
                            <th>Gains/Losses (EUR)</th>
                            <th>Taxes (EUR)</th>
                            <th>Net Gains (EUR)</th>
                            <th>Tax Rate</th>
                          </tr>
                        </thead>
                        <tbody>
                          {getAssetDataForYear().map((asset, index) => (
                            <tr key={index}>
                              <td>
                                <Badge bg="secondary">{asset.asset}</Badge>
                              </td>
                              <td className={getGainLossClass(asset.gain)}>
                                {formatCurrency(asset.gain)}
                              </td>
                              <td className="loss">
                                {formatCurrency(asset.taxes)}
                              </td>
                              <td className={getGainLossClass(asset.netGain)}>
                                {formatCurrency(asset.netGain)}
                              </td>
                              <td>
                                {asset.gain > 0 ? `${getTaxRate(asset.gain, asset.taxes).toFixed(1)}%` : '0%'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </Table>
                    </div>
                  </Card.Body>
                </Card>
              </Col>
              <Col md={4}>
                <Card className="mb-4">
                  <Card.Header>Asset Distribution {selectedYear}</Card.Header>
                  <Card.Body>
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie
                          data={getAssetDataForYear()}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          label={({ asset, gain }) => `${asset}: ${formatCurrency(gain)}`}
                          outerRadius={80}
                          fill="#8884d8"
                          dataKey="gain"
                        >
                          {getAssetDataForYear().map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value) => formatCurrency(value)} />
                      </PieChart>
                    </ResponsiveContainer>
                  </Card.Body>
                </Card>
              </Col>
            </Row>
          )}

          {/* Tax Calculation Notes */}
          <Card>
            <Card.Header>Tax Calculation Notes</Card.Header>
            <Card.Body>
              <ul>
                <li>Tax rate: 26% on crypto gains (Italian regulation)</li>
                <li>2024 includes franchigia (€2,000 deductible threshold)</li>
                <li>Gains and losses are calculated using FIFO method</li>
                <li>Only realized gains are taxable (when crypto is sold for EUR)</li>
                <li>Holding period doesn't affect tax rate for crypto assets</li>
              </ul>
            </Card.Body>
          </Card>
        </>
      )}
    </div>
  );
};

export default TaxSummary; 