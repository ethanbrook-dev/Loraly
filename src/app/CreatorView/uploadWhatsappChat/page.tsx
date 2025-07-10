'use client';

import React, { useState } from 'react';
import JSZip from 'jszip';
import '../../styles/uploadChatHistory.css';

interface Participant {
  name: string;
  count: number;
  firstMessageSnippet: string;
  duplicateIndex?: number;
}

export default function UploadWhatsappChat() {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [participants, setParticipants] = useState<Participant[]>([]);
  const [selectedParticipant, setSelectedParticipant] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setError(null);
    setParticipants([]);
    setSelectedParticipant(null);
    if (!e.target.files?.length) return;
    const uploadedFile = e.target.files[0];

    if (!uploadedFile.name.toLowerCase().endsWith('.zip')) {
      setError('Unsupported file type. Please upload a .zip file exported from WhatsApp.');
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
        setError("No '_chat.txt' file found inside the zip. Please export chat properly.");
        setLoading(false);
        return;
      }
      const chatFile = zip.files[chatFileName];
      const textContent = await chatFile.async('text');

      const lines = textContent.split(/\r?\n/);
      const participantMap = new Map<string, { count: number; firstMessage?: string }>();

      const messageRegex = /^\[\d{1,2}\/\d{1,2}\/\d{2,4}, \d{1,2}:\d{2}:\d{2}\] (.*?): (.*)$/;

      for (const line of lines) {
        const match = line.match(messageRegex);
        if (match) {
          const name = match[1].trim();
          const message = match[2].trim();
          if (!participantMap.has(name)) {
            participantMap.set(name, { count: 1, firstMessage: message });
          } else {
            participantMap.get(name)!.count += 1;
          }
        }
      }

      const participantsArr: Participant[] = [];
      const nameDuplicates = new Map<string, number>();

      for (const [name, data] of participantMap.entries()) {
        if (nameDuplicates.has(name)) {
          const idx = nameDuplicates.get(name)! + 1;
          nameDuplicates.set(name, idx);
          participantsArr.push({
            name: `${name} (${idx + 1})`,
            count: data.count,
            firstMessageSnippet: data.firstMessage ? data.firstMessage.slice(0, 50) : '',
            duplicateIndex: idx,
          });
        } else if (Array.from(participantMap.keys()).filter(n => n === name).length > 1) {
          nameDuplicates.set(name, 0);
          participantsArr.push({
            name: `${name} (1)`,
            count: data.count,
            firstMessageSnippet: data.firstMessage ? data.firstMessage.slice(0, 50) : '',
            duplicateIndex: 0,
          });
        } else {
          participantsArr.push({
            name,
            count: data.count,
            firstMessageSnippet: data.firstMessage ? data.firstMessage.slice(0, 50) : '',
          });
        }
      }

      participantsArr.sort((a, b) => b.count - a.count);

      setParticipants(participantsArr);
      setError(null);
    } catch (e) {
      setError('Failed to read or parse the zip file. Make sure it is a valid WhatsApp chat export.');
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  const handleSelectParticipant = (name: string) => {
    setSelectedParticipant(name);
    setError(null);
  };

  const handleConfirm = () => {
    if (!selectedParticipant) {
      setError('Please select which participant represents you.');
      return;
    }
    alert(`You selected: ${selectedParticipant}. Proceeding with this identity.`);
  };

  return (
    <main className="upload-chat-file-page">
      <h1 className="page-title">Upload Your WhatsApp Chat (.zip only)</h1>

      <section className="instructions-section">
        <h2 className="section-title">How to Export WhatsApp Chat</h2>
        <h3 className="subheading">On your phone:</h3>
        <ol className="instruction-list">
          <li>Open WhatsApp on your phone.</li>
          <li>Open the chat you wish to upload.</li>
          <li>Tap the chat group or contact name at the top.</li>
          <li>Scroll down and tap "Export Chat" — select "Without Media".</li>
          <li>Choose "Save to Files" and then upload the exported .zip file here.</li>
        </ol>
        <h3 className="subheading">On your computer:</h3>
        <ol className="instruction-list">
          <li>Open WhatsApp Desktop.</li>
          <li>Go to the chat you want to export.</li>
          <li>Click the chat name to open chat info.</li>
          <li>Use the Export Chat option (if available) or use the backup files.</li>
          <li>Save the exported .zip file and upload it here.</li>
        </ol>
      </section>

      <section className="upload-section">
        <input className="file-input" type="file" accept=".zip" onChange={handleFileChange} />
        {error && <p className="error-message">{error}</p>}
      </section>

      {loading && <p className="loading-message">Loading and parsing chat file...</p>}

      {participants.length > 0 && (
        <section className="participants-section">
          <h2 className="section-title">Select Your Participant Name</h2>
          <p className="participant-instruction">
            Multiple people in the chat may share the same name. Use the message counts and first
            message snippets to identify yourself. If you have duplicate names, they are numbered.
            You can add a unique emoji or nickname to your WhatsApp name before exporting to help
            later.
          </p>
          <ul className="participants-list">
            {participants.map((p) => (
              <li key={p.name} className="participant-item">
                <label className="participant-label">
                  <input
                    className="participant-radio"
                    type="radio"
                    name="participant"
                    value={p.name}
                    checked={selectedParticipant === p.name}
                    onChange={() => handleSelectParticipant(p.name)}
                  />
                  <strong>{p.name}</strong> — {p.count} messages — “
                  {p.firstMessageSnippet.length > 0 ? p.firstMessageSnippet : 'No messages yet'}…”
                </label>
              </li>
            ))}
          </ul>
          <button className="confirm-button" onClick={handleConfirm} disabled={!selectedParticipant}>
            Confirm and Continue
          </button>
        </section>
      )}
    </main>
  );
}
