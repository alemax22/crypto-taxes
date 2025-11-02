import React from 'react';

const LoadingSpinner = ({ size = 'md', className = '' }) => {
  const sizeClasses = {
    sm: 'spinner',
    md: 'spinner',
    lg: 'spinner-lg'
  };

  return (
    <div className={`loading-spinner ${className}`}>
      <div className={sizeClasses[size]}></div>
      
      <style jsx>{`
        .loading-spinner {
          display: flex;
          align-items: center;
          justify-content: center;
        }
        
        .spinner {
          width: 1.5rem;
          height: 1.5rem;
          border: 2px solid var(--dark-border);
          border-top: 2px solid var(--primary-blue);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        
        .spinner-lg {
          width: 3rem;
          height: 3rem;
          border: 3px solid var(--dark-border);
          border-top: 3px solid var(--primary-blue);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};

export default LoadingSpinner;
