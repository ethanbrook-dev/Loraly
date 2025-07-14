'use client';

import React, { useState, useEffect } from 'react';
import JSZip from 'jszip';
import { useRouter, useSearchParams } from 'next/navigation';
import { MIN_WORDS_FOR_LORA_GEN } from '@/app/constants/MIN_WORDS_FOR_LORA_GEN';
import '../../../../styles/uploadChatHistory.css';

interface Message {
  name: string;
  message: string;
}

interface Entry {
  input: string;
  output: string;
}

interface UploadWhatsappChatProps {
  loraId: string | null;
}

export default function UploadWhatsappChat({ loraId }: UploadWhatsappChatProps) {
  const router = useRouter();

  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [participants, setParticipants] = useState<string[]>([]);
  const [selectedParticipant, setSelectedParticipant] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [allMessages, setAllMessages] = useState<Message[]>([]);
  const [generating, setGenerating] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    setParticipants([]);
    setSelectedParticipant(null);
    if (!e.target.files?.length) return;

    const uploadedFile = e.target.files[0];

    if (!uploadedFile.name.toLowerCase().endsWith('.zip')) {
      setError('Only .zip files exported from WhatsApp are supported.');
      return;
    }

    setFile(uploadedFile);
    parseZipFile(uploadedFile);
  };

  const parseZipFile = async (zipFile: File) => {
    setLoading(true);
    try {
      const zip = await JSZip.loadAsync(zipFile);
      const chatFileName = Object.keys(zip.files).find(name =>
        name.toLowerCase().endsWith('_chat.txt')
      );
      if (!chatFileName) {
        setError("No '_chat.txt' file found in the zip.");
        setLoading(false);
        return;
      }

      const chatText = await zip.files[chatFileName].async('text');
      const lines = chatText.split(/\r?\n/);

      const messageRegex = /^\[(\d{1,2}\/\d{1,2}\/\d{2,4}), \d{1,2}:\d{2}:\d{2}\] (.*?): (.*)$/;
      const uniqueNames = new Set<string>();
      const tempMessages: Message[] = [];

      for (const line of lines) {
        const match = line.match(messageRegex);
        if (!match) continue;

        let name = match[2].trim().replace(/\u200E/g, '');
        let message = match[3].trim().replace(/\u200E/g, '');

        if (
          message === '' ||
          message === 'image omitted' ||
          message.startsWith('Messages and calls are end-to-end encrypted') ||
          name === 'You'
        ) continue;

        uniqueNames.add(name);
        tempMessages.push({ name, message });
      }

      setAllMessages(tempMessages);
      setParticipants(Array.from(uniqueNames));
      setError(null);
    } catch (err) {
      console.error(err);
      setError('Failed to parse the WhatsApp .zip file.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirm = async () => {
    if (!selectedParticipant || !loraId) {
      setError('Please select your name and ensure LoRA ID is present.');
      return;
    }

    const entries: Entry[] = [];
    let inputBuffer: string[] = [];

    for (const msg of allMessages) {
      if (msg.name !== selectedParticipant) {
        inputBuffer.push(msg.message);
      } else {
        if (inputBuffer.length > 0) {
          entries.push({
            input: inputBuffer.join(' '),
            output: msg.message,
          });
          inputBuffer = [];
        }
      }
    }

    const fullText = entries
      .map(e => `[INST] ${e.input.trim()} [/INST] ${e.output.trim()}`)
      .join('\n')
      .trim();

    const wordCount = entries.reduce((sum, e) => {
      const inputWords = e.input.trim().split(/\s+/).length;
      const outputWords = e.output.trim().split(/\s+/).length;
      return sum + inputWords + outputWords;
    }, 0);

    if (wordCount < MIN_WORDS_FOR_LORA_GEN) {
      setError(`Not enough text. You need at least ${MIN_WORDS_FOR_LORA_GEN} words.`);
      return;
    }

    router.push('../../../CreatorView/TrainingStartedPage');
    return;

    // try {
    //   setGenerating(true);
    //   const res = await fetch(`${process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL}/generate-voice`, {
    //     method: 'POST',
    //     headers: { 'Content-Type': 'application/json' },
    //     body: JSON.stringify({
    //       loraId,
    //       rawText: fullText,
    //     }),
    //   });

    //   if (res.ok) {
    //     router.push('../../../CreatorView/TrainingStartedPage');
    //   } else {
    //     setError('Voice generation failed. Please try again.');
    //   }
    // } catch (err) {
    //   console.error(err);
    //   setError('Unexpected error during voice generation.');
    // } finally {
    //   setGenerating(false);
    // }
  };

  return (
    <main className="upload-chat-file-page">
      <h1 className="page-title">Upload Your WhatsApp Chat</h1>
      <p className="subheading">(.zip only)</p>

      <section className="instructions-section">
        <h2 className="section-title">Export Instructions (Phone)</h2>
        <ol className="instruction-list">
          <li>Open WhatsApp on your phone.</li>
          <li>Open the chat you want to export.</li>
          <li>Tap the contact or group name at the top.</li>
          <li>Tap "Export Chat" and select "Without Media".</li>
          <li>Save to Files, then upload the .zip here.</li>
        </ol>
      </section>

      <section className="upload-section">
        <input className="file-input" type="file" accept=".zip" onChange={handleFileChange} />
        {error && <p className="error-message">{error}</p>}
        {loading && <p className="loading-message">Reading file...</p>}
      </section>

      {participants.length > 0 && (
        <section className="participants-section">
          <h2 className="section-title">Which one is you?</h2>
          <ul className="participants-list">
            {participants.map(name => (
              <li key={name} className="participant-item">
                <label className="participant-label">
                  <input
                    type="radio"
                    name="participant"
                    value={name}
                    checked={selectedParticipant === name}
                    onChange={() => setSelectedParticipant(name)}
                    className="participant-radio"
                  />
                  {name}
                </label>
              </li>
            ))}
          </ul>
          <button
            className="confirm-button"
            onClick={handleConfirm}
            disabled={generating}
          >
            {generating ? 'Generating Voice...' : 'Confirm & Generate Voice'}
          </button>
        </section>
      )}
    </main>
  );
}
