'use client';

import { useRouter, useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import '../../../../../../styles/SharingLoraStyles.css';

export default function ShareLoraPage() {
  const router = useRouter();
  const params = useParams();
  const { loraid, loraName } = params;

  return (
    <main className="share-container">
      <h1 className="share-title">Share &quot;{loraName}&quot; with ... ?</h1>

      <input
        type="text"
        placeholder="Search users or emails..."
        className="share-search-input"
      />
      
      <button
        className="share-back-button"
        onClick={() => router.back()}
      >
        Back to Dashboard
      </button>
    </main>
  );
}
