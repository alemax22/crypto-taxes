import React from 'react';
import { BrowserRouter as Router, Routes, Route, Link } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Wallets from './pages/Wallets';
import Transactions from './pages/Transactions';
import TaxSummary from './pages/TaxSummary';
import Balance from './pages/Balance';
import 'bootstrap/dist/css/bootstrap.min.css';
import 'bootstrap-icons/font/bootstrap-icons.css';
import './App.css';
import './dark-theme.css';

function App() {
  return (
    <Router>
      <nav className="navbar navbar-expand-lg navbar-dark bg-dark">
        <div className="container-fluid">
          <Link className="navbar-brand" to="/">Crypto Taxes</Link>
          <button className="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" aria-controls="navbarNav" aria-expanded="false" aria-label="Toggle navigation">
            <span className="navbar-toggler-icon"></span>
          </button>
          <div className="collapse navbar-collapse" id="navbarNav">
            <ul className="navbar-nav me-auto mb-2 mb-lg-0">
              <li className="nav-item">
                <Link className="nav-link" to="/">Dashboard</Link>
              </li>
              <li className="nav-item">
                <Link className="nav-link" to="/wallets">Wallets</Link>
              </li>
              <li className="nav-item">
                <Link className="nav-link" to="/transactions">Transactions</Link>
              </li>
              <li className="nav-item">
                <Link className="nav-link" to="/tax-summary">Tax Reports</Link>
              </li>
              <li className="nav-item">
                <Link className="nav-link" to="/balance">Settings</Link>
              </li>
            </ul>
            <div className="navbar-nav">
              <span className="badge bg-secondary me-3">Free Plan</span>
            </div>
          </div>
        </div>
      </nav>
      <main className="container-fluid py-4" style={{ maxWidth: '1200px' }}>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/wallets" element={<Wallets />} />
          <Route path="/transactions" element={<Transactions />} />
          <Route path="/tax-summary" element={<TaxSummary />} />
          <Route path="/balance" element={<Balance />} />
        </Routes>
      </main>
    </Router>
  );
}

export default App; 