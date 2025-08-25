'use client';

import React, { useState, useEffect } from 'react';
import JSZip from 'jszip';
import { useRouter, useSearchParams } from 'next/navigation';
import { MIN_WORDS_FOR_LORA_GEN } from '@/app/constants/MIN_WORDS_FOR_LORA_GEN';
import '../../../../styles/uploadChatHistory.css';

interface Message {
  name: string;
  message: string;
  timestamp: Date;
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

      const messageRegex = /^\[(\d{1,2}\/\d{1,2}\/\d{2,4}), (\d{1,2}:\d{2}:\d{2})\] (.*?): (.*)$/;

      const uniqueNames = new Set<string>();
      const tempMessages: Message[] = [];

      for (const line of lines) {
        const match = line.match(messageRegex);
        if (!match) continue;

        const datePart = match[1];
        const timePart = match[2];
        const name = match[3].trim().replace(/\u200E/g, '');
        const message = match[4].trim().replace(/\u200E/g, '');

        if (!message || message === 'image omitted' || message.startsWith('Messages and calls are end-to-end encrypted') || name === 'You') continue;

        const timestamp = new Date(`${datePart} ${timePart}`);
        uniqueNames.add(name);
        tempMessages.push({ name, message, timestamp });
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
      setError('Please select your name.');
      return;
    }

    const MAX_GAP_HOURS = 1; // split if gap > 1 hour

    // sort messages by timestamp
    const sortedMessages = [...allMessages].sort(
      (a, b) => a.timestamp.getTime() - b.timestamp.getTime()
    );

    const conversationBlocks: string[] = [];
    let currentBlock: string[] = [];
    let lastTimestamp: Date | null = null;

    let lastAddedLine: string | null = null;

    for (const msg of sortedMessages) {
      const speaker = msg.name === selectedParticipant ? 'User' : 'Assistant';
      const line = `${speaker}: ${msg.message}`;

      // skip if it's exactly the same as the last added line
      if (line === lastAddedLine) continue;

      let startNewBlock = false;
      if (lastTimestamp) {
        const diffHours = (msg.timestamp.getTime() - lastTimestamp.getTime()) / 1000 / 3600;
        if (diffHours > MAX_GAP_HOURS) startNewBlock = true;
      }

      if (startNewBlock) {
        if (currentBlock.length > 0) {
          conversationBlocks.push(currentBlock.join('\n'));
        }
        currentBlock = [];
      }

      currentBlock.push(line);
      lastAddedLine = line;
      lastTimestamp = msg.timestamp;
    }

    if (currentBlock.length > 0) {
      conversationBlocks.push([...currentBlock].join('\n'));

      // Count words
      let wordCount = 0;
      conversationBlocks.forEach(block => {
        const lines = block.split('\n');
        lines.forEach(line => {
          const msgText = line.replace(/^(User|Assistant):\s*/, '');
          wordCount += msgText.split(/\s+/).filter(Boolean).length;
        });
      });

      console.log('Total word count:', wordCount);

      const fullText = conversationBlocks.map(block => JSON.stringify({ text: block })).join('\n');

      if (wordCount < MIN_WORDS_FOR_LORA_GEN) {
        const proceed = window.confirm(
          `You have ${wordCount} words.\nRecommended minimum: ${MIN_WORDS_FOR_LORA_GEN} words.\n\nDo you want to go ahead and generate the voice anyway?`
        );
        if (!proceed) return;
      }

      const assistantName = participants.find(name => name !== selectedParticipant);

      try {
        setGenerating(true);
        const res = await fetch(`${process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL}/generate-voice`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            loraId,
            rawText: fullText,
            participants: {
              user: selectedParticipant,
              assistant: assistantName,
            },
          }),
        });

        if (res.ok) {
          router.push('../../../CreatorView/TrainingStartedPage');
        } else {
          setError('Voice generation failed. Please try again.');
        }
      } catch (err) {
        console.error(err);
        setError('Unexpected error during voice generation.');
      } finally {
        setGenerating(false);
      }
    };
  }

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
