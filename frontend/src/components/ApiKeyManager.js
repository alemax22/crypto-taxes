import React, { useState, useEffect } from 'react';
import { Card, Form, Button, Alert, Spinner, Modal } from 'react-bootstrap';
import axios from 'axios';

const ApiKeyManager = ({ onCredentialsSet }) => {
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);
  const [credentialsStatus, setCredentialsStatus] = useState(null);
  const [showModal, setShowModal] = useState(false);

  useEffect(() => {
    checkCredentialsStatus();
    // eslint-disable-next-line
  }, []);

  const checkCredentialsStatus = async () => {
    try {
      const response = await axios.get('/api/check-credentials');
      if (response.data.valid) {
        setCredentialsStatus(response.data);
        // Notify parent if credentials are valid
        onCredentialsSet();
      }
    } catch (err) {
      console.error('Error checking credentials status:', err);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setSuccess(null);

    try {
      const response = await axios.post('/api/setup-credentials', {
        api_key: apiKey,
        api_secret: apiSecret
      });

      if (response.data.valid) {
        setSuccess(response.data.valid);
        setApiKey('');
        setApiSecret('');
        setShowModal(false);
        await checkCredentialsStatus();
        if (onCredentialsSet) {
          onCredentialsSet();
        }
      } else {
        setError(response.data.error);
      }
    } catch (err) {
      setError(err.response?.data?.error || 'An error occurred while saving credentials');
    } finally {
      setLoading(false);
    }
  };

  const handleShowModal = () => {
    setShowModal(true);
    setError(null);
    setSuccess(null);
  };

  const handleCloseModal = () => {
    setShowModal(false);
    setApiKey('');
    setApiSecret('');
    setError(null);
    setSuccess(null);
  };

  const getStatusBadge = () => {
    if (!credentialsStatus) return null;
    if (credentialsStatus.valid) return null;
    return (
      <div className="d-flex align-items-center">
        <span className="badge bg-warning me-2">⚠ Not Configured</span>
        <small className="text-muted">{credentialsStatus.message}</small>
      </div>
    );
  };

  return (
    <>
      <Card className="stats-card mb-4">
        <Card.Header>
          <div className="d-flex justify-content-between align-items-center">
            <h5 className="mb-0">Kraken API Configuration</h5>
            {getStatusBadge()}
          </div>
        </Card.Header>
        <Card.Body>
          <p className="text-muted mb-3">
            Configure your Kraken API credentials to access your trading data. 
            Your credentials will be encrypted and stored securely.
          </p>
          {/* Only show the warning and button if not configured */}
          {!credentialsStatus?.valid && (
            <div className="text-center">
              <p className="text-warning mb-3">
                <strong>⚠ API credentials are required to access your data</strong>
              </p>
              <Button 
                variant="primary" 
                onClick={handleShowModal}
              >
                Configure API Credentials
              </Button>
            </div>
          )}
          {credentialsStatus?.valid && (
            <div className="text-center">
              <p className="text-success mb-3">
                <strong>✓ API credentials are configured and ready to use!</strong>
              </p>
            </div>
          )}
        </Card.Body>
      </Card>

      {/* Modal for API Key Configuration */}
      <Modal show={showModal} onHide={handleCloseModal} size="lg">
        <Modal.Header closeButton>
          <Modal.Title>Configure Kraken API Credentials</Modal.Title>
        </Modal.Header>
        <Form onSubmit={handleSubmit}>
          <Modal.Body>
            <Alert variant="info">
              <strong>Security Note:</strong> Your API credentials will be encrypted using 
              the application's encryption system and stored securely. They will persist 
              across application restarts.
            </Alert>

            {error && (
              <Alert variant="danger">
                <strong>Error:</strong> {error}
              </Alert>
            )}

            {success && (
              <Alert variant="success">
                <strong>Success:</strong> {success}
              </Alert>
            )}

            <Form.Group className="mb-3">
              <Form.Label>API Key</Form.Label>
              <Form.Control
                type="text"
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                placeholder="Enter your Kraken API key"
                required
                disabled={loading}
              />
              <Form.Text className="text-muted">
                Get your API key from <a href="https://support.kraken.com/it-it/articles/360000919966-how-to-create-an-api-key" target="_blank" rel="noopener noreferrer">Kraken API Settings</a>
              </Form.Text>
            </Form.Group>

            <Form.Group className="mb-3">
              <Form.Label>API Secret</Form.Label>
              <Form.Control
                type="text"
                value={apiSecret}
                onChange={(e) => setApiSecret(e.target.value)}
                placeholder="Enter your Kraken API secret"
                required
                disabled={loading}
              />
              <Form.Text className="text-muted">
                Your API secret is required for authentication
              </Form.Text>
            </Form.Group>

            <Alert variant="warning">
              <strong>Required Permissions:</strong> Your API key needs the following permissions:
              <ul className="mb-0 mt-2">
                <li><strong>Query Funds</strong> - To check balances</li>
                <li><strong>Query Open Orders & Trades</strong> - To download transaction history</li>
                <li><strong>Query Ledgers</strong> - To download deposit/withdrawal history</li>
              </ul>
            </Alert>
          </Modal.Body>
          <Modal.Footer>
            <Button variant="secondary" onClick={handleCloseModal} disabled={loading}>
              Cancel
            </Button>
            <Button 
              variant="primary" 
              type="submit" 
              disabled={loading || !apiKey || !apiSecret}
            >
              {loading ? (
                <>
                  <Spinner animation="border" size="sm" className="me-2" />
                  Testing & Saving...
                </>
              ) : (
                'Save Credentials'
              )}
            </Button>
          </Modal.Footer>
        </Form>
      </Modal>
    </>
  );
};

export default ApiKeyManager; 