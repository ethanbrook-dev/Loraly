'use client';

// React imports
import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

// Database functions and types imports
import {
  getAuthenticatedUser,
  getUSERProfile,
  generateUSERProfilePicSignedUrl,
  getLORAProfilesByCreator,
  deleteLORA,
  updateLORAProfilePic
} from '../../components/db_funcs/db_funcs';

// Components imports
import ProfilePicture_lora from '../../components/ProfilePicture_Lora';
import UserHeader from '../../components/UserHeader';
import UploadWhatsappChat from '../uploadWhatsappChat/page';

// Constants imports
import { MIN_WORDS_FOR_LORA_GEN } from '../../constants/MIN_WORDS_FOR_LORA_GEN';
import { LoraStatus } from '@/app/constants/loraStatus';

// Styles imports
import '../../../../styles/CreatorViewStyles.css';
import '../../../../styles/LoraCardStyles.css';
import '../../../../styles/SharingLoraStyles.css'

type AudioFile = {
  name: string;
  text: string;
  duration: number;
};

type Lora = {
  id: string;
  creator_id: string;
  name: string;
  profile_pic_url: string | null;
  audio_files: AudioFile[];
  training_status: string;
};

type SharedLora = {
  id: string,
  name: string,
  shared_pic_url: string
}

type UserProfile = {
  id: string;
  username: string;
  email: string | null;
  profile_pic_url: string | null;
  loras_created: string[];
  loras_shared_w_me: SharedLora[];
}

export default function CreatorDashboard() {
  const router = useRouter();

  const [userData, setUserData] = useState<UserProfile | null>(null);
  const [userProfilePicUrl, setUserProfilePicUrl] = useState<string | null>(null);
  const [loras, setLoras] = useState<Lora[]>([]);
  const [userId, setUserId] = useState<string | null>(null);

  const [loadingLoraIDs, setLoadingLoraIDs] = useState<Record<string, boolean>>({});
  const [uploadingLoraId, setUploadingLoraId] = useState<string | null>(null);

  // Fetch user profile
  useEffect(() => {
    async function fetchUserProfile() {
      const user = await getAuthenticatedUser();
      if (!user) return;
      setUserId(user.id);

      const userData = await getUSERProfile(user.id)

      if (!userData) {
        setUserData(null);
        return;
      }

      setUserData(userData);

      if (userData.profile_pic_url) {
        const signedUrl = await generateUSERProfilePicSignedUrl(userData.profile_pic_url, 60);
        if (!signedUrl) return;
        setUserProfilePicUrl(signedUrl);
      }
    }

    fetchUserProfile();
  }, []);

  // Fetch LoRAs created by the user
  useEffect(() => {
    async function fetchLoras() {
      if (!userId) return;

      const loraData = await getLORAProfilesByCreator(userId);

      if (loraData) setLoras(loraData);
    }

    fetchLoras();
  }, [userId]);

  useEffect(() => {
    // Reset loading state when component mounts
    setLoadingLoraIDs({});
  }, []);

  // Handle LoRA Deletion
  const handleDeleteLora = async (lora: Lora) => {
    if (!confirm('Are you sure you want to delete this voice?')) return;

    const loraWasDeleted = await deleteLORA(lora);

    if (loraWasDeleted) {
      setLoras((prev) => prev.filter((lora1) => lora1.id !== lora.id));
    } else {
      console.error('Error deleting LoRA');
      return;
    }
  };

  if (uploadingLoraId) {
    return <UploadWhatsappChat loraId={uploadingLoraId} />;
  }

  return (
    <main className="creator-dashboard">
      <UserHeader
        role_of_user="Creator"
        username={userData?.username || 'Loading...'}
        profilePicUrl={userProfilePicUrl}
        onBackClick={() => router.push('../../../RoleSelect')}
      />

      <section className="creator-voice-section">
        {loras.length === 0 ? (
          <p className="italic">You haven’t created any voices yet.</p>
        ) : (
          <div className="loras-scroll-container">
            {loras.map((lora) => {
              const isTraining = lora.training_status === LoraStatus.TRAINING;
              const isTrainingCompleted = lora.training_status === LoraStatus.TRAINING_COMPLETED;

              return (
                <div key={lora.id} className="lora-card">
                  <div className="lora-info">
                    <ProfilePicture_lora
                      loraId={lora.id}
                      currentProfilePicPath={lora.profile_pic_url ?? null}
                      onUploadSuccess={async (newUrl) => {
                        if (isTraining || isTrainingCompleted) return; // 🔒 disable during/after training
                        const wasUpdated = await updateLORAProfilePic(lora.id, newUrl);
                        if (!wasUpdated) {
                          setLoras((prev) =>
                            prev.map((item) =>
                              item.id === lora.id ? { ...item, profile_pic_url: newUrl } : item
                            )
                          );
                        }
                      }}
                    />
                    <div className="lora-name">{lora.name}</div>
                  </div>

                  <div className="lora-buttons">
                    {isTraining || isTrainingCompleted ? (
                      <>
                        {isTraining && (
                          <p className="generating-voice-text">Generating Voice ...</p>
                        )}
                        {isTrainingCompleted && (
                          <button
                            className="share-button"
                            onClick={() => router.push(`../../../CreatorView/ShareLora/${lora.id}/${lora.name}`)}
                          >
                            Share Voice
                          </button>
                        )}
                      </>
                    ) : (
                      <>
                        {loadingLoraIDs[lora.id] ? (
                          <div className="spinner" />
                        ) : (
                          <>
                            <button
                              className="upload-chat-file-button"
                              onClick={() => setUploadingLoraId(lora.id)}
                            >
                              Upload WhatsApp Chat
                            </button>
                          </>
                        )}
                      </>
                    )}
                  </div>

                  {lora.training_status !== LoraStatus.TRAINING_COMPLETED && (
                    <button
                      className="delete-button"
                      onClick={() => handleDeleteLora(lora)}
                      title="Delete Voice"
                      disabled={
                        loadingLoraIDs[lora.id] || lora.training_status === LoraStatus.TRAINING
                      }
                      style={{
                        opacity:
                          loadingLoraIDs[lora.id] || lora.training_status === LoraStatus.TRAINING
                            ? 0.5
                            : 1,
                        cursor:
                          loadingLoraIDs[lora.id] || lora.training_status === LoraStatus.TRAINING
                            ? 'not-allowed'
                            : 'pointer',
                      }}
                    >
                      <img src="/delete-icon.svg" alt="Delete" />
                    </button>
                  )}
                </div>
              );
            })}

          </div>
        )}
      </section>

      <footer className="creator-footer">
        <button
          className="create-voice-button"
          onClick={() => router.push('../../../CreatorView/CreateVoice')}
        >
          Create Voice
        </button>
      </footer>
    </main >
  );
}