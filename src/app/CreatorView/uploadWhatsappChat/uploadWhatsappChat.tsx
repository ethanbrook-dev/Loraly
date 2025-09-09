'use client';

import React, { useState } from 'react';
import JSZip from 'jszip';
import { useRouter } from 'next/navigation';
import { MIN_WORDS_FOR_LORA_GEN } from '@/app/constants/MIN_WORDS_FOR_LORA_GEN';
import '../../../../styles/UploadChatHistory.css';

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

  const [error, setError] = useState<string | null>(null);
  const [participants, setParticipants] = useState<string[]>([]);
  const [selectedParticipant, setSelectedParticipant] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [allMessages, setAllMessages] = useState<Message[]>([]);
  const [generating, setGenerating] = useState(false);

  // --- File Handling ---
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

      const messageRegex =
        /^\[(\d{1,2}\/\d{1,2}\/\d{2,4}), (\d{1,2}:\d{2}:\d{2})\] (.*?): (.*)$/;

      const uniqueNames = new Set<string>();
      const tempMessages: Message[] = [];

      for (const line of lines) {
        const match = line.match(messageRegex);
        if (!match) continue;

        const [, datePart, timePart, rawName, rawMessage] = match;
        const name = rawName.trim().replace(/\u200E/g, '');
        const message = rawMessage.trim().replace(/\u200E/g, '');

        if (
          !message ||
          message === 'image omitted' ||
          message.startsWith('Messages and calls are end-to-end encrypted') ||
          name === 'You'
        )
          continue;

        const timestamp = new Date(`${datePart} ${timePart}`);
        uniqueNames.add(name);
        tempMessages.push({ name, message, timestamp });
      }

      setAllMessages(tempMessages);
      const tempParticipants = Array.from(uniqueNames);
      setParticipants(tempParticipants);

      if (tempParticipants.length !== 2) {
        setError(
          'Only one-on-one chats are supported. Please upload a chat with exactly 2 participants.'
        );
        setAllMessages([]);
        setParticipants([]);
        return;
      }
    } catch (err) {
      console.error(err);
      setError('Failed to parse the WhatsApp .zip file.');
    } finally {
      setLoading(false);
    }
  };

  // --- Confirm & Generate ---
  const handleConfirm = async () => {
    if (!selectedParticipant || !loraId) {
      setError('Please select whose voice should be mimicked.');
      return;
    }

    const sortedMessages = [...allMessages].sort(
      (a, b) => a.timestamp.getTime() - b.timestamp.getTime()
    );

    const conversationBlocks: string[] = [];
    for (const msg of sortedMessages) {
      const speaker = msg.name === selectedParticipant ? 'Assistant' : 'User';
      if (!msg.message.trim()) continue;
      conversationBlocks.push(`${speaker}: ${msg.message.trim()}`);
    }

    const jsonlPayload = conversationBlocks
      .map(line => JSON.stringify({ text: line }))
      .join('\n');

    const wordCount = conversationBlocks.reduce((count, line) => {
      const textOnly = line.replace(/^(User|Assistant):\s*/, '');
      return count + textOnly.split(/\s+/).filter(Boolean).length;
    }, 0);

    if (wordCount < MIN_WORDS_FOR_LORA_GEN) {
      const formattedMin = `${MIN_WORDS_FOR_LORA_GEN / 1000}k`; // formats 100000 as 100k
      const proceed = window.confirm(
        `Only ${wordCount} words provided.\n` +
        `Recommended minimum: ${formattedMin} words.\n\n` +
        `⚠️ When chatting with your AI (LoRA), the output will likely be garbled because the current word count is too small for the model to learn style.\n` +
        `You can still proceed to see the training process, output, share feature, and chat feature, but it is not recommended (as the AI won't respond well).`
      );

      setError(null);

      if (!proceed) return;
    }

    try {
      setGenerating(true);
      const res = await fetch(
        `${process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL}/generate-voice`,
        {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            loraId,
            rawText: jsonlPayload,
            participants: {
              user: participants.find(name => name !== selectedParticipant),
              assistant: selectedParticipant,
            },
          }),
        }
      );

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

  // --- UI ---
  return (
    <main className="upload-chat-file-page">
      {/* Header */}
      <header className="page-header">
        <h1 className="page-title">Upload Your WhatsApp Chat</h1>
        <p className="subheading">Only <code>.zip</code> exports are supported</p>
      </header>

      {/* Instructions */}
      <section className="instructions-section">
        <h2 className="section-title">How to Export (on your phone)</h2>
        <ol className="instruction-list">
          <li>Open WhatsApp and go to the chat you want to export.</li>
          <li>This must be a <strong>one-to-one chat</strong> (group chats not supported).</li>
          <li>Tap the contact’s name at the top → choose <em>Export Chat</em>.</li>
          <li>Select <em>Without Media</em> when asked.</li>
          <li>Save as <code>.zip</code>, then upload it here.</li>
        </ol>
      </section>

      {/* Upload */}
      <section className="upload-section">
        <label htmlFor="file-upload" className="file-input-label">
          <span className="upload-icon">📂</span> Choose WhatsApp Chat (.zip)
        </label>
        <input
          id="file-upload"
          className="file-input"
          type="file"
          accept=".zip"
          onChange={handleFileChange}
        />
        {error && <p className="error-message">{error}</p>}
        {loading && <p className="loading-message">Reading file...</p>}
      </section>

      {/* Participants */}
      {participants.length > 0 && (
        <section className="participants-section">
          <h2 className="section-title">Choose a Voice</h2>
          <p className="participant-help-text">
            Select the person whose texting style you want the AI to mimic.
          </p>

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
                  Mimic <strong>{name}</strong>
                </label>
              </li>
            ))}
          </ul>

          <button
            className="confirm-button"
            onClick={handleConfirm}
            disabled={generating}
          >
            {generating ? 'Processing... do not exit' : 'Confirm & Generate Voice'}
          </button>
        </section>
      )}
    </main>
  );
}
