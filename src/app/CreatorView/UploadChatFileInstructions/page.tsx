'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';

export default function UploadChatFileInstructions() {
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files?.length) return;
    const uploadedFile = e.target.files[0];

    // Validate file type or size if needed
    if (!uploadedFile.name.endsWith('.txt') && !uploadedFile.name.endsWith('.db') && !uploadedFile.name.endsWith('.json') && !uploadedFile.name.endsWith('.zip')) {
      setError('Unsupported file type. Please upload .txt, .db, .json or .zip files.');
      return;
    }
    setError(null);
    setFile(uploadedFile);
  };

  const handleUpload = async () => {
    if (!file) {
      setError('Please select a file first.');
      return;
    }
    // Upload logic here: send to your backend for parsing + ingestion
    const formData = new FormData();
    formData.append('chatFile', file);

    try {
      const res = await fetch('/api/upload-chat-file', {
        method: 'POST',
        body: formData,
      });

      if (res.ok) {
        // Redirect to chat selection or confirmation page
        router.push('/CreatorView/ChatSelection');
      } else {
        setError('Failed to upload chat file. Please try again.');
      }
    } catch (err) {
      setError('Unexpected error occurred.');
      console.error(err);
    }
  };

  return (
    <main className="upload-chat-file-page">
      <h1>Upload Your Chat File</h1>
      <section>
        <h2>How to Export Your Chat</h2>
        <ul>
          <li><strong>WhatsApp:</strong> Export chat as .txt via chat options</li>
          <li><strong>iMessage (macOS):</strong> Copy <code>~/Library/Messages/chat.db</code></li>
          <li><strong>Telegram:</strong> Use API login or export chat from Desktop</li>
        </ul>
      </section>

      <section>
        <input type="file" accept=".txt,.db,.json,.zip" onChange={handleFileChange} />
        {error && <p className="error-message">{error}</p>}
        <button onClick={handleUpload} disabled={!file}>Upload and Continue</button>
      </section>
    </main>
  );
}