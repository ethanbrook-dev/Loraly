'use client';

import '../../../../styles/TrainingStartedStyles.css';

export default function TrainingStartedPage() {
  return (
    <main className="training-container">
      <div className="training-content">
        {/* Animated header section */}
        <div className="animation-header">
          <div className="pulse-ring">
            <div className="spinner">
              <div className="spinner-inner">
                <svg className="spinner-svg" viewBox="0 0 100 100">
                  <circle className="spinner-track" cx="50" cy="50" r="45" />
                  <circle className="spinner-path" cx="50" cy="50" r="45" />
                </svg>
              </div>
            </div>
          </div>
          <div className="ai-icon">🤖</div>
        </div>

        {/* Main content */}
        <h1 className="training-title">Training in Progress!</h1>
        
        <div className="important-notice">
          <svg className="notice-icon" viewBox="0 0 24 24" width="24" height="24">
            <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
          </svg>
          <span>You may now exit the page</span>
        </div>

        <div className="training-details">
          <div className="info-card">
            <svg className="info-icon" viewBox="0 0 24 24" width="20" height="20">
              <path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-6h2v6zm0-8h-2V7h2v2z"/>
            </svg>
            <p>Your custom AI model is learning to replicate the writing style you provided.</p>
          </div>

          <div className="info-card">
            <svg className="time-icon" viewBox="0 0 24 24" width="20" height="20">
              <path fill="currentColor" d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm.5-13H11v6l5.25 3.15.75-1.23-4.5-2.67z"/>
            </svg>
            <p>Processing a 10,000-word conversation typically takes <strong>15-20 minutes</strong>.</p>
          </div>

          <div className="info-card">
            <svg className="data-icon" viewBox="0 0 24 24" width="20" height="20">
              <path fill="currentColor" d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>
            </svg>
            <p>For larger data sets, please allow for extra processing time.</p>
          </div>

          <div className="info-card highlight">
            <svg className="dashboard-icon" viewBox="0 0 24 24" width="20" height="20">
              <path fill="currentColor" d="M3 13h8V3H3v10zm0 8h8v-6H3v6zm10 0h8V11h-8v10zm0-18v6h8V3h-8z"/>
            </svg>
            <p>Check your dashboard later to begin generating text with your new model.</p>
          </div>
        </div>

        {/* Progress bar */}
        <div className="progress-container">
          <div className="progress-bar">
            <div className="progress-fill"></div>
          </div>
          <div className="progress-text">Processing your data...</div>
        </div>
      </div>
    </main>
  );
}