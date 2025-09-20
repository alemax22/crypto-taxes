import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import Navbar from './components/Navbar';
import Dashboard from './pages/Dashboard';
import Wallets from './pages/Wallets';
import WalletDetails from './pages/WalletDetails';
import './styles/globals.css';

function App() {
  return (
    <div className="App">
      <Router>
        <Navbar />
        <main className="container" style={{ paddingTop: '2rem', paddingBottom: '2rem' }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/wallets" element={<Wallets />} />
            <Route path="/wallets/:walletId" element={<WalletDetails />} />
          </Routes>
        </main>
      </Router>
    </div>
  );
}

export default App;