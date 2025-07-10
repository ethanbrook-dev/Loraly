'use client';

import React, { useState } from 'react';
import JSZip from 'jszip';
import '../../../../styles/uploadChatHistory.css';

interface Message {
  name: string;
  message: string;
}

interface Entry {
  input: string;
  output: string;
}

export default function UploadWhatsappChat() {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [participants, setParticipants] = useState<string[]>([]);
  const [selectedParticipant, setSelectedParticipant] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [allMessages, setAllMessages] = useState<Message[]>([]);

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

    // Matches: [MM/DD/YY, HH:mm:ss] Name: message
    const messageRegex = /^\[(\d{1,2}\/\d{1,2}\/\d{2,4}), \d{1,2}:\d{2}:\d{2}\] (.*?): (.*)$/;

    const uniqueNames = new Set<string>();
    const tempMessages: Message[] = [];

    for (const line of lines) {
      const match = line.match(messageRegex);
      if (!match) continue;

      let name = match[2].trim().replace(/\u200E/g, '');  // remove invisible LTR marks
      let message = match[3].trim().replace(/\u200E/g, '');

      // Skip lines with only system messages or empty content
      if (
        message === 'Messages and calls are end-to-end encrypted. Only people in this chat can read, listen to, or share them.' ||
        message === 'image omitted' ||
        message === '‎You pinned a message' ||
        message === ''
      ) {
        continue;
      }

      // Skip WhatsApp's "You" placeholder (your own messages)
      if (name === 'You') continue;

      uniqueNames.add(name);
      tempMessages.push({ name, message });
    }

    setAllMessages(tempMessages);
    console.log("all messages I got are:", tempMessages);
    setParticipants(Array.from(uniqueNames));
    setError(null);
  } catch (err) {
    console.error(err);
    setError('Failed to parse the WhatsApp .zip file.');
  } finally {
    setLoading(false);
  }
};

  const handleConfirm = () => {
    if (!selectedParticipant) {
      setError('Please select your name from the list.');
      return;
    }
    setError(null);

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

    console.log('Entries for LoRA input/output:', entries);
    alert(`Parsed ${entries.length} input-output pairs for user ${selectedParticipant}. Check console.`);
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
      </section>

      {loading && <p className="loading-message">Reading file...</p>}

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
            disabled={!selectedParticipant}
          >
            Confirm
          </button>
        </section>
      )}
    </main>
  );
}
