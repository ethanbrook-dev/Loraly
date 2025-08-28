'use client';

export default function TrainingStartedPage() {

  return (
    <main style={styles.container}>
      <div style={styles.animation}>
        <div className="spinner" />
      </div>
      <h1>Training in progress!</h1>
      <p style={styles.important}>You may now exit the page</p>
      <p>Your custom AI model is learning to replicate the writing style you provided.</p>
      <p>Processing a 10,000-word conversation typically takes 15-20 minutes.</p>
      <p>For larger data sets, please allow for extra processing time.</p>
      <p>Check your dashboard later to begin generating text with your new model.</p>

      <style jsx>{`
        .spinner {
          margin: 0 auto 20px auto;
          width: 50px;
          height: 50px;
          border: 5px solid #ccc;
          border-top-color: #0070f3;
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        @keyframes spin {
          to {
            transform: rotate(360deg);
          }
        }
      `}</style>
    </main>
  );
}

const styles = {
  container: {
    maxWidth: '500px',
    margin: '100px auto',
    textAlign: 'center' as const,
    fontFamily: 'system-ui, sans-serif',
  },
  animation: {
    marginBottom: '1rem',
  },
  important: {
    color: '#e74c3c',
    fontWeight: 'bold',
    fontSize: '18px',
  },
};