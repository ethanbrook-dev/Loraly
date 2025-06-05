'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  getAuthenticatedUser,
  initLORA,
  updateLORAProfilePic
} from '../../components/db_funcs/db_funcs';
import ProfilePicture_lora from '../../components/ProfilePicture_Lora';
import '../../../../styles/CreatorViewStyles.css';

export default function CreateVoice() {
  const [name, setName] = useState('');
  const [errorMsg, setErrorMsg] = useState('');
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [loraId, setLoraId] = useState<string | null>(null);
  const router = useRouter();
  const creator_dashboard_naviagtion = '../../CreatorView/Creator_dashboard';

  const handleCreateLora = async () => {
    if (!name.trim()) {
      setErrorMsg('Voice name is required.');
      return;
    }

    const user = await getAuthenticatedUser();
    if (!user) return;

    // Step 1: create the LoRA with empty profile_pic_url
    const initID = await initLORA(user.id, name.trim());
    if (!initID) {
      setErrorMsg('Error creating voice. Try again.');
      return;
    }

    setLoraId(initID); // trigger showing the image uploader
  };

  return (
    <div className="creator-voice-section">
      <div className="create-voice-container">
        <h2 className="create-voice-title">Create Voice</h2>

        {loraId ? (
          <>
            <div className="voice-name-input-container">
              <p className="voice-name-note">
                You can now upload a profile picture for this Voice.
              </p>
              <ProfilePicture_lora loraId={loraId} onUploadSuccess={(filePath) => setImageUrl(filePath)} />
            </div>
              <button
                className="voice-save-button"
                onClick={async () => {
                  const success = await updateLORAProfilePic(loraId, imageUrl);
                  if (!success) {
                    setErrorMsg('Failed to save profile picture.');
                  } else {
                    router.push(creator_dashboard_naviagtion);
                  }
                }}
              >
                Save Profile Pic
              </button>
          </>
        ) : (
          <>
            <input
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="Display name of this Voice"
              className="voice-name-input"
            />
            <p className="voice-name-note">
              This voice cannot be renamed once created.
            </p>
            {errorMsg && <p className="voice-error-message">{errorMsg}</p>}
            <button onClick={handleCreateLora} className="voice-save-button">
              Save
            </button>
          </>
        )}

      </div>
    </div>
  );
}