///// IMPORTANT: this page is a feature I am not sure I will keep - I will delete it at the end //////////////////

// user recoedings page - allows web mic, transcribing, and saving

'use client';

// React imports
import React, { useEffect, useRef, useState } from 'react';
import { useParams, useRouter } from 'next/navigation';

// Database functions and types imports
import {
  updateLORAAudioFiles,
  getLORAProfileByID
} from '../../../components/db_funcs/db_funcs';

// Styles import
import '../../../../../styles/CreatorViewStyles.css';

declare global {
  interface Window {
    webkitSpeechRecognition: any;
  }
}

type Recording = {
  name: string;
  duration: number;
  text: string;
};

type VoiceData = {
  id: string;
  creator_id: string;
  recordings: Recording[];
};

function formatDuration(seconds: number) {
  const m = Math.floor(seconds / 60).toString().padStart(2, '0');
  const s = Math.floor(seconds % 60).toString().padStart(2, '0');
  return `${m}:${s}`;
}

export default function RecordingsPage() {
  const router = useRouter();
  const params = useParams();
  const loraid = params?.loraid as string;

  const [voiceData, setVoiceData] = useState<VoiceData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const finalTranscript = useRef('');
  const [recordingDuration, setRecordingDuration] = useState<number | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const recognitionRef = useRef<any>(null);
  const chunks = useRef<Blob[]>([]);
  const startTimeRef = useRef<number | null>(null);

  const [showConfirmationModal, setShowConfirmationModal] = useState(false);
  const [showNameForm, setShowNameForm] = useState(false);
  const [newRecordingName, setNewRecordingName] = useState('');
  const [nameError, setNameError] = useState('');

  useEffect(() => {
    fetchVoiceData();
    return () => {
      recognitionRef.current?.stop();
    };
  }, [loraid]);

  const fetchVoiceData = async () => {
    setLoading(true);
    setError('');
    const lora = await getLORAProfileByID(loraid);

    if (!lora) {
      setError('Failed to load recordings.');
      setLoading(false);
      return;
    }

    setVoiceData({
      id: lora.id,
      creator_id: lora.creator_id,
      recordings: lora.audio_files || [],
    });

    setLoading(false);
  };

  const toggleMic = async () => {
    if (!isRecording) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const recorder = new MediaRecorder(stream);
        mediaRecorderRef.current = recorder;
        chunks.current = [];
        startTimeRef.current = Date.now();

        recorder.ondataavailable = (e) => chunks.current.push(e.data);
        recorder.onstop = () => {
          const blob = new Blob(chunks.current, { type: 'audio/ogg; codecs=opus' });
          const url = URL.createObjectURL(blob);
          const duration = startTimeRef.current ? (Date.now() - startTimeRef.current) / 1000 : 0;
          setRecordingDuration(duration);
          setShowConfirmationModal(true);
        };

        recorder.start();

        recognitionRef.current = new window.webkitSpeechRecognition();
        recognitionRef.current.continuous = true;
        recognitionRef.current.interimResults = true;
        recognitionRef.current.onresult = (event: any) => {
          let interimTranscript = '';

          for (let i = event.resultIndex; i < event.results.length; i++) {
            const result = event.results[i];
            if (result.isFinal) {
              finalTranscript.current += result[0].transcript + ' ';
            } else {
              interimTranscript += result[0].transcript + ' ';
            }
          }

          setTranscript(finalTranscript.current + interimTranscript);
        };
        recognitionRef.current.start();

        setIsRecording(true);
      } catch (err) {
        console.error('Mic access error:', err);
      }
    } else {
      mediaRecorderRef.current?.stop();
      recognitionRef.current?.stop();
      setIsRecording(false);
    }
  };

  const handleConfirmation = (confirmed: boolean) => {
    setShowConfirmationModal(false);
    if (confirmed) {
      setShowNameForm(true);
    } else {
      resetRecording();
    }
  };

  const resetRecording = () => {
    setTranscript("");
    finalTranscript.current = "";
    setRecordingDuration(null);
    setIsRecording(false);
  };

  const saveRecording = async () => {
    if (!newRecordingName.trim()) {
      setNameError('Recording name is required.');
      return;
    }
    if (voiceData?.recordings.some(r => r.name === newRecordingName.trim())) {
      setNameError('Recording name must be unique.');
      return;
    }

    const newEntry: Recording = {
      name: newRecordingName.trim(),
      duration: recordingDuration || 0,
      text: transcript,
    };

    const updatedRecordings = [...(voiceData?.recordings || []), newEntry];

    const audioFilesWereUpdated = await updateLORAAudioFiles(updatedRecordings, voiceData);

    if (!audioFilesWereUpdated) {
      setNameError('Failed to save recording.');
      return;
    }

    setShowNameForm(false);
    setNewRecordingName('');
    resetRecording();
    fetchVoiceData();
  };

  const handleDelete = async (nameToDelete: string) => {
    if (!voiceData) return;

    const updated = voiceData.recordings.filter(r => r.name !== nameToDelete);

    const recordingWasDeleted = await updateLORAAudioFiles(updated, voiceData);

    if (!recordingWasDeleted) {
      alert('Failed to delete recording.');
      return;
    }

    fetchVoiceData();
  };

  return (
    <main className="pageContainer">
      <h1 className="pageTitle">My Recordings</h1>

      <p className="recording-guidelines">
        🎙️ For the best results, speak clearly and avoid noisy environments. <br />
        🎧 Avoid having any listening devices plugged in (headphones, earphones, earbuds, or similar), as this can reduce transcription accuracy. <br />
        ⏱️ Shorter recordings usually yield clearer and more accurate transcriptions. <br />
        🗣️ Don’t worry — longer clips work too! <br />
        ⚠️ Just remember, longer recordings may not be as sharp unless you speak clearly throughout.
      </p>

      <button className="back-btn" onClick={() => router.push('../Creator_dashboard')}>
        ← Back to dashboard
      </button>

      <section className="recordMicSection">
        <button className={`mic-button ${isRecording ? 'is-recording' : ''}`} onClick={toggleMic}>
          <img
            src={isRecording ? '/stop-recording-icon.svg' : '/start-recording-icon.svg'}
            alt={isRecording ? 'Stop recording' : 'Start recording'}
            className="mic-icon"
          />
        </button>
      </section>

      {(showConfirmationModal || showNameForm) && (
        <div className="confirmation-modal">
          <div className="modal-box">
            {showConfirmationModal && (
              <>
                <p className="modal-question">Did you say:</p>
                <p className="modal-transcript">"{transcript}"</p>
                <div className="modal-actions">
                  <button className="modal-btn yes" onClick={() => handleConfirmation(true)}>Yes</button>
                  <button className="modal-btn no" onClick={() => handleConfirmation(false)}>No</button>
                </div>
                <p className="modal-note">❗Clicking “No” will discard this recording and you’ll need to record again.</p>
              </>
            )}

            {showNameForm && (
              <>
                <h2 className="create-voice-title">Name Your Recording</h2>
                <input
                  className="voice-name-input"
                  type="text"
                  placeholder="Enter a name"
                  value={newRecordingName}
                  onChange={(e) => {
                    setNewRecordingName(e.target.value);
                    setNameError('');
                  }}
                />
                {nameError && <p className="voice-error-message">{nameError}</p>}
                <button className="voice-save-button" onClick={saveRecording}>Save Recording</button>
                <button
                  className="record-more-button"
                  onClick={() => {
                    setShowNameForm(false);
                    resetRecording();
                  }}>
                  Cancel
                </button>
              </>
            )}
          </div>
        </div>
      )}

      <section className="uploadedRecordingsSection">
        <h2 className="uploadedRecordingsTitle">Recordings</h2>

        {loading && <p className="loadingText">Loading recordings...</p>}
        {error && <p className="errorText">{error}</p>}

        {voiceData?.recordings.length ? (
          <div className="audioFilesContainer">
            {voiceData.recordings.map(({ name, duration, text }) => (
              <div key={name} className="audioFileRow">
                <div className="audioName">{name}</div>
                <div className="audioDuration">{formatDuration(duration)}</div>
                <div className="audioTranscript">{text.length > 50 ? text.slice(0, 50) + '...' : text}</div>
                <button className="deleteButton" onClick={() => {
                  if (confirm(`Delete recording "${name}"?`)) {
                    handleDelete(name);
                  }
                }}>
                  <img src="/delete-icon.svg" alt="Delete" className="deleteIcon" />
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="noRecordingsText">No recordings found.</p>
        )}
      </section>
    </main>
  );
}