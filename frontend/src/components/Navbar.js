import React, { useState } from 'react';
import { Link, useLocation } from 'react-router-dom';

const Navbar = () => {
  const location = useLocation();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  const navItems = [
    { path: '/', label: 'Dashboard', icon: '📊' },
    { path: '/wallets', label: 'Wallets', icon: '💼' }
  ];

  const isActive = (path) => {
    if (path === '/') {
      return location.pathname === '/';
    }
    return location.pathname.startsWith(path);
  };

  return (
    <nav className="navbar">
      <div className="container">
        <div className="navbar-content">
          {/* Logo */}
          <Link to="/" className="navbar-brand">
            <div className="logo">
              <span className="logo-icon">💰</span>
              <span className="logo-text">CryptoPortfolio</span>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <div className="navbar-nav desktop-nav">
            {navItems.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`nav-link ${isActive(item.path) ? 'active' : ''}`}
              >
                <span className="nav-icon">{item.icon}</span>
                <span className="nav-label">{item.label}</span>
              </Link>
            ))}
          </div>

          {/* Mobile Menu Button */}
          <button
            className="mobile-menu-btn"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            aria-label="Toggle menu"
          >
            <div className={`hamburger ${isMobileMenuOpen ? 'active' : ''}`}>
              <span></span>
              <span></span>
              <span></span>
            </div>
          </button>
        </div>

        {/* Mobile Navigation */}
        <div className={`mobile-nav ${isMobileMenuOpen ? 'open' : ''}`}>
          {navItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`mobile-nav-link ${isActive(item.path) ? 'active' : ''}`}
              onClick={() => setIsMobileMenuOpen(false)}
            >
              <span className="nav-icon">{item.icon}</span>
              <span className="nav-label">{item.label}</span>
            </Link>
          ))}
        </div>
      </div>

      <style jsx>{`
        .navbar {
          background: var(--dark-surface);
          border-bottom: 1px solid var(--dark-border);
          position: sticky;
          top: 0;
          z-index: 100;
          backdrop-filter: blur(10px);
        }

        .navbar-content {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: 1rem 0;
        }

        .navbar-brand {
          text-decoration: none;
          color: var(--text-primary);
          transition: var(--transition);
        }

        .navbar-brand:hover {
          transform: scale(1.02);
        }

        .logo {
          display: flex;
          align-items: center;
          gap: 0.75rem;
        }

        .logo-icon {
          font-size: 1.5rem;
          animation: pulse 2s ease-in-out infinite;
        }

        .logo-text {
          font-size: 1.25rem;
          font-weight: 700;
          background: var(--gradient-primary);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .desktop-nav {
          display: flex;
          align-items: center;
          gap: 2rem;
        }

        .nav-link {
          display: flex;
          align-items: center;
          gap: 0.5rem;
          padding: 0.75rem 1rem;
          border-radius: var(--border-radius);
          text-decoration: none;
          color: var(--text-secondary);
          transition: var(--transition);
          position: relative;
          overflow: hidden;
        }

        .nav-link::before {
          content: '';
          position: absolute;
          top: 0;
          left: -100%;
          width: 100%;
          height: 100%;
          background: var(--gradient-primary);
          opacity: 0.1;
          transition: var(--transition);
          z-index: -1;
        }

        .nav-link:hover::before,
        .nav-link.active::before {
          left: 0;
        }

        .nav-link:hover,
        .nav-link.active {
          color: var(--text-primary);
          transform: translateY(-1px);
        }

        .nav-link.active {
          color: var(--primary-blue);
          font-weight: 600;
        }

        .nav-icon {
          font-size: 1.1rem;
        }

        .nav-label {
          font-size: 0.875rem;
          font-weight: 500;
        }

        .mobile-menu-btn {
          display: none;
          background: none;
          border: none;
          cursor: pointer;
          padding: 0.5rem;
          border-radius: var(--border-radius);
          transition: var(--transition);
        }

        .mobile-menu-btn:hover {
          background: var(--dark-surface-hover);
        }

        .hamburger {
          width: 24px;
          height: 18px;
          position: relative;
        }

        .hamburger span {
          display: block;
          position: absolute;
          height: 2px;
          width: 100%;
          background: var(--text-primary);
          border-radius: 1px;
          opacity: 1;
          left: 0;
          transform: rotate(0deg);
          transition: 0.25s ease-in-out;
        }

        .hamburger span:nth-child(1) {
          top: 0px;
        }

        .hamburger span:nth-child(2) {
          top: 8px;
        }

        .hamburger span:nth-child(3) {
          top: 16px;
        }

        .hamburger.active span:nth-child(1) {
          top: 8px;
          transform: rotate(135deg);
        }

        .hamburger.active span:nth-child(2) {
          opacity: 0;
          left: -60px;
        }

        .hamburger.active span:nth-child(3) {
          top: 8px;
          transform: rotate(-135deg);
        }

        .mobile-nav {
          display: none;
          flex-direction: column;
          padding: 1rem 0;
          border-top: 1px solid var(--dark-border);
          background: var(--dark-surface);
          transform: translateY(-100%);
          opacity: 0;
          transition: var(--transition);
        }

        .mobile-nav.open {
          transform: translateY(0);
          opacity: 1;
        }

        .mobile-nav-link {
          display: flex;
          align-items: center;
          gap: 0.75rem;
          padding: 1rem;
          text-decoration: none;
          color: var(--text-secondary);
          transition: var(--transition);
          border-radius: var(--border-radius);
          margin: 0.25rem 0;
        }

        .mobile-nav-link:hover,
        .mobile-nav-link.active {
          color: var(--primary-blue);
          background: rgba(59, 130, 246, 0.1);
        }

        @media (max-width: 768px) {
          .desktop-nav {
            display: none;
          }

          .mobile-menu-btn {
            display: block;
          }

          .mobile-nav {
            display: flex;
          }

          .logo-text {
            font-size: 1.125rem;
          }
        }
      `}</style>
    </nav>
  );
};

export default Navbar;
