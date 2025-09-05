'use client';

import React, { useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '../../../../supabase/client';

export default function UserEnvForm() {
  const router = useRouter();
  const [hfToken, setHfToken] = useState('');
  const [hfUsername, setHfUsername] = useState('');
  const [runpodApiKey, setRunpodApiKey] = useState('');
  const [loading, setLoading] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setLoading(true);
    setErrorMsg('');

    try {
      const res = await fetch(`${process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL}/save-env-vars`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          user_id: (await supabase.auth.getUser()).data.user?.id,
          hf_token: hfToken,
          hf_username: hfUsername,
          runpod_api_key: runpodApiKey,
        }),
      });
      
      if (res.ok) {
        router.push('/CreatorView/Creator_dashboard'); // go to dashboard after setup
      } else {
        const data = await res.json();
        setErrorMsg(data.error || 'Failed to save API keys.');
      }
    } catch (err) {
      console.error(err);
      setErrorMsg('Unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="loraly-container">
      <div className="loraly-wrapper">
        <h1>Set up your API keys</h1>
        <p>These keys are needed for LoRA training and voice generation.</p>

        <form onSubmit={handleSubmit} className="loraly-form">
          <input
            placeholder="HuggingFace Token"
            value={hfToken}
            onChange={(e) => setHfToken(e.target.value)}
            required
          />
          <input
            placeholder="HuggingFace Username"
            value={hfUsername}
            onChange={(e) => setHfUsername(e.target.value)}
            required
          />
          <input
            placeholder="RunPod API Key"
            value={runpodApiKey}
            onChange={(e) => setRunpodApiKey(e.target.value)}
            required
          />
          {errorMsg && <p className="error-message">{errorMsg}</p>}
          <button type="submit" disabled={loading}>
            {loading ? 'Saving...' : 'Save & Continue'}
          </button>
        </form>
      </div>
    </div>
  );
}
