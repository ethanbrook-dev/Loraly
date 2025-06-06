'use client';

// React imports
import { useRouter, useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

export default function ShareLoraPage() {
  const router = useRouter();
  const params = useParams();
  const { loraId } = params;

  // You can fetch more data about the LoRA here based on loraId

  return (
    <main style={{ padding: 20 }}>
      <h1>Share Voice</h1>
      <p>This is the share page for voice ID: <strong>{loraId}</strong></p>
      <p>Implement sharing logic here (e.g., share links, social media buttons, etc.)</p>

      <button
        style={{
          marginTop: 20,
          padding: '10px 16px',
          borderRadius: 8,
          backgroundColor: '#4f46e5',
          color: 'white',
          border: 'none',
          cursor: 'pointer',
        }}
        onClick={() => router.back()}
      >
        Back to Dashboard
      </button>
    </main>
  );
}
