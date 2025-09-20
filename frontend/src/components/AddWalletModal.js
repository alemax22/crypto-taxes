import React, { useState } from 'react';
import LoadingSpinner from './LoadingSpinner';

const AddWalletModal = ({ isOpen, onClose, onAdd }) => {
  const [formData, setFormData] = useState({
    name: '',
    type: 'kraken',
    api_key: '',
    api_secret: '',
    description: ''
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [step, setStep] = useState(1);

  const walletTypes = [
    {
      id: 'kraken',
      name: 'Kraken',
      icon: '🐙',
      description: 'Connect your Kraken exchange account',
      features: ['Spot Trading', 'Futures', 'Staking', 'DeFi']
    },
    {
      id: 'binance',
      name: 'Binance',
      icon: '🟡',
      description: 'Connect your Binance exchange account',
      features: ['Spot Trading', 'Futures', 'Options', 'Earn'],
      disabled: true
    },
    {
      id: 'coinbase',
      name: 'Coinbase Pro',
      icon: '🔵',
      description: 'Connect your Coinbase Pro account',
      features: ['Spot Trading', 'Advanced Trading'],
      disabled: true
    }
  ];

  const handleInputChange = (field, value) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    setError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await onAdd(formData);
      if (result.success) {
        handleClose();
      } else {
        setError(result.error || 'Failed to add wallet');
      }
    } catch (err) {
      setError('An unexpected error occurred');
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setFormData({
      name: '',
      type: 'kraken',
      api_key: '',
      api_secret: '',
      description: ''
    });
    setStep(1);
    setError(null);
    onClose();
  };

  const validateStep1 = () => {
    return formData.type && formData.name.trim();
  };

  const validateStep2 = () => {
    return formData.api_key.trim() && formData.api_secret.trim();
  };

  const selectedWalletType = walletTypes.find(w => w.id === formData.type);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={handleClose}>
      <div className="modal-container" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2>Add New Wallet</h2>
          <button className="close-btn" onClick={handleClose}>✕</button>
        </div>

        <div className="modal-body">
          {/* Progress Steps */}
          <div className="progress-steps">
            <div className={`step ${step >= 1 ? 'active' : ''}`}>
              <div className="step-number">1</div>
              <div className="step-label">Choose Wallet</div>
            </div>
            <div className={`step-connector ${step >= 2 ? 'active' : ''}`}></div>
            <div className={`step ${step >= 2 ? 'active' : ''}`}>
              <div className="step-number">2</div>
              <div className="step-label">Configure</div>
            </div>
          </div>

          {error && (
            <div className="error-message">
              <span className="error-icon">⚠️</span>
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit}>
            {step === 1 && (
              <div className="step-content fade-in">
                <h3>Choose Wallet Type</h3>
                <p className="text-secondary mb-6">
                  Select the exchange or wallet you want to connect
                </p>

                <div className="wallet-types">
                  {walletTypes.map((walletType) => (
                    <div
                      key={walletType.id}
                      className={`wallet-type-card ${
                        formData.type === walletType.id ? 'selected' : ''
                      } ${walletType.disabled ? 'disabled' : ''}`}
                      onClick={() => !walletType.disabled && handleInputChange('type', walletType.id)}
                    >
                      <div className="wallet-type-header">
                        <div className="wallet-type-icon">{walletType.icon}</div>
                        <div className="wallet-type-info">
                          <div className="wallet-type-name">{walletType.name}</div>
                          <div className="wallet-type-description">{walletType.description}</div>
                        </div>
                        {walletType.disabled && (
                          <div className="coming-soon-badge">Coming Soon</div>
                        )}
                      </div>
                      <div className="wallet-type-features">
                        {walletType.features.map((feature) => (
                          <span key={feature} className="feature-tag">{feature}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>

                <div className="form-group">
                  <label className="form-label">Wallet Name</label>
                  <input
                    type="text"
                    className="input"
                    placeholder={`My ${selectedWalletType?.name} Wallet`}
                    value={formData.name}
                    onChange={(e) => handleInputChange('name', e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">Description (Optional)</label>
                  <input
                    type="text"
                    className="input"
                    placeholder="Personal trading account"
                    value={formData.description}
                    onChange={(e) => handleInputChange('description', e.target.value)}
                  />
                </div>
              </div>
            )}

            {step === 2 && (
              <div className="step-content fade-in">
                <h3>Configure API Access</h3>
                <p className="text-secondary mb-6">
                  Enter your {selectedWalletType?.name} API credentials to connect your wallet
                </p>

                <div className="api-info-card">
                  <div className="api-info-header">
                    <span className="info-icon">ℹ️</span>
                    <strong>Required Permissions</strong>
                  </div>
                  <ul className="permissions-list">
                    <li>✅ Query Funds (View balances)</li>
                    <li>✅ Query Open Orders & Trades (Transaction history)</li>
                    <li>✅ Query Ledgers (Deposits & withdrawals)</li>
                    <li>❌ Trading permissions (Not required)</li>
                  </ul>
                </div>

                <div className="form-group">
                  <label className="form-label">API Key</label>
                  <input
                    type="text"
                    className="input"
                    placeholder="Enter your API key"
                    value={formData.api_key}
                    onChange={(e) => handleInputChange('api_key', e.target.value)}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label">API Secret</label>
                  <input
                    type="password"
                    className="input"
                    placeholder="Enter your API secret"
                    value={formData.api_secret}
                    onChange={(e) => handleInputChange('api_secret', e.target.value)}
                    required
                  />
                </div>

                <div className="security-note">
                  <span className="security-icon">🔒</span>
                  <div className="security-text">
                    <strong>Your data is secure</strong>
                    <p>API credentials are encrypted and stored locally. We never store your private keys.</p>
                  </div>
                </div>
              </div>
            )}
          </form>
        </div>

        <div className="modal-footer">
          <div className="footer-buttons">
            {step > 1 && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => setStep(step - 1)}
                disabled={loading}
              >
                Back
              </button>
            )}
            
            <div className="primary-buttons">
              <button
                type="button"
                className="btn btn-outline"
                onClick={handleClose}
                disabled={loading}
              >
                Cancel
              </button>
              
              {step === 1 ? (
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={() => setStep(2)}
                  disabled={!validateStep1()}
                >
                  Next
                </button>
              ) : (
                <button
                  type="submit"
                  className="btn btn-primary"
                  onClick={handleSubmit}
                  disabled={!validateStep2() || loading}
                >
                  {loading ? (
                    <>
                      <LoadingSpinner size="sm" />
                      <span style={{ marginLeft: '0.5rem' }}>Adding Wallet...</span>
                    </>
                  ) : (
                    'Add Wallet'
                  )}
                </button>
              )}
            </div>
          </div>
        </div>

        <style jsx>{`
          .modal-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            padding: 1rem;
          }

          .modal-container {
            background: var(--dark-surface);
            border: 1px solid var(--dark-border);
            border-radius: var(--border-radius-lg);
            width: 100%;
            max-width: 600px;
            max-height: 90vh;
            overflow-y: auto;
            box-shadow: var(--shadow-xl);
          }

          .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 1.5rem;
            border-bottom: 1px solid var(--dark-border);
          }

          .modal-header h2 {
            margin: 0;
            color: var(--text-primary);
          }

          .close-btn {
            background: none;
            border: none;
            color: var(--text-muted);
            font-size: 1.5rem;
            cursor: pointer;
            padding: 0.25rem;
            border-radius: 50%;
            transition: var(--transition);
          }

          .close-btn:hover {
            background: var(--dark-surface-hover);
            color: var(--text-primary);
          }

          .modal-body {
            padding: 1.5rem;
          }

          .progress-steps {
            display: flex;
            align-items: center;
            justify-content: center;
            margin-bottom: 2rem;
          }

          .step {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 0.5rem;
          }

          .step-number {
            width: 2rem;
            height: 2rem;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 600;
            border: 2px solid var(--dark-border);
            color: var(--text-muted);
            transition: var(--transition);
          }

          .step.active .step-number {
            background: var(--primary-blue);
            border-color: var(--primary-blue);
            color: white;
          }

          .step-label {
            font-size: 0.875rem;
            color: var(--text-muted);
            transition: var(--transition);
          }

          .step.active .step-label {
            color: var(--text-primary);
            font-weight: 500;
          }

          .step-connector {
            width: 4rem;
            height: 2px;
            background: var(--dark-border);
            margin: 0 1rem;
            transition: var(--transition);
          }

          .step-connector.active {
            background: var(--primary-blue);
          }

          .error-message {
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid var(--error);
            border-radius: var(--border-radius);
            padding: 1rem;
            margin-bottom: 1.5rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
            color: var(--error);
          }

          .error-icon {
            font-size: 1.25rem;
          }

          .step-content {
            min-height: 400px;
          }

          .step-content h3 {
            margin-bottom: 0.5rem;
            color: var(--text-primary);
          }

          .wallet-types {
            display: flex;
            flex-direction: column;
            gap: 1rem;
            margin-bottom: 2rem;
          }

          .wallet-type-card {
            border: 2px solid var(--dark-border);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            cursor: pointer;
            transition: var(--transition);
          }

          .wallet-type-card:hover:not(.disabled) {
            border-color: var(--primary-blue);
            background: rgba(59, 130, 246, 0.05);
          }

          .wallet-type-card.selected {
            border-color: var(--primary-blue);
            background: rgba(59, 130, 246, 0.1);
          }

          .wallet-type-card.disabled {
            opacity: 0.6;
            cursor: not-allowed;
          }

          .wallet-type-header {
            display: flex;
            align-items: flex-start;
            gap: 1rem;
            margin-bottom: 1rem;
          }

          .wallet-type-icon {
            font-size: 2rem;
            width: 3rem;
            height: 3rem;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: var(--border-radius);
            background: rgba(59, 130, 246, 0.1);
          }

          .wallet-type-info {
            flex: 1;
          }

          .wallet-type-name {
            font-size: 1.125rem;
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: 0.25rem;
          }

          .wallet-type-description {
            font-size: 0.875rem;
            color: var(--text-secondary);
          }

          .coming-soon-badge {
            background: var(--warning);
            color: var(--dark-bg);
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
          }

          .wallet-type-features {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
          }

          .feature-tag {
            background: var(--dark-surface);
            color: var(--text-secondary);
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            border: 1px solid var(--dark-border);
          }

          .form-group {
            margin-bottom: 1.5rem;
          }

          .form-label {
            display: block;
            margin-bottom: 0.5rem;
            font-weight: 500;
            color: var(--text-primary);
          }

          .api-info-card {
            background: rgba(59, 130, 246, 0.05);
            border: 1px solid rgba(59, 130, 246, 0.2);
            border-radius: var(--border-radius);
            padding: 1.5rem;
            margin-bottom: 2rem;
          }

          .api-info-header {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            margin-bottom: 1rem;
            color: var(--primary-blue);
          }

          .info-icon {
            font-size: 1.25rem;
          }

          .permissions-list {
            list-style: none;
            padding: 0;
            margin: 0;
          }

          .permissions-list li {
            padding: 0.25rem 0;
            font-size: 0.875rem;
            color: var(--text-secondary);
          }

          .security-note {
            display: flex;
            gap: 1rem;
            padding: 1rem;
            background: rgba(16, 185, 129, 0.05);
            border: 1px solid rgba(16, 185, 129, 0.2);
            border-radius: var(--border-radius);
            margin-top: 1.5rem;
          }

          .security-icon {
            font-size: 1.5rem;
            color: var(--success);
          }

          .security-text strong {
            color: var(--success);
            display: block;
            margin-bottom: 0.25rem;
          }

          .security-text p {
            margin: 0;
            font-size: 0.875rem;
            color: var(--text-secondary);
          }

          .modal-footer {
            padding: 1.5rem;
            border-top: 1px solid var(--dark-border);
            background: rgba(0, 0, 0, 0.1);
          }

          .footer-buttons {
            display: flex;
            justify-content: space-between;
            align-items: center;
            gap: 1rem;
          }

          .primary-buttons {
            display: flex;
            gap: 1rem;
          }

          @media (max-width: 768px) {
            .modal-overlay {
              padding: 0.5rem;
            }

            .modal-container {
              max-height: 95vh;
            }

            .modal-header,
            .modal-body,
            .modal-footer {
              padding: 1rem;
            }

            .step-content {
              min-height: 300px;
            }

            .progress-steps {
              margin-bottom: 1.5rem;
            }

            .step-connector {
              width: 2rem;
              margin: 0 0.5rem;
            }

            .wallet-type-header {
              flex-direction: column;
              align-items: center;
              text-align: center;
              gap: 0.75rem;
            }

            .footer-buttons {
              flex-direction: column;
              align-items: stretch;
            }

            .primary-buttons {
              order: -1;
            }
          }
        `}</style>
      </div>
    </div>
  );
};

export default AddWalletModal;
