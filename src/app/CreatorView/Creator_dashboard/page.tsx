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

type UserProfile = {
  id: string;
  username: string;
  email: string | null;
  profile_pic_url: string | null;
  loras_created: Lora[];
  loras_shared_w_me: Lora[];
}

export default function CreatorDashboard() {
  const router = useRouter();

  const [userData, setUserData] = useState<UserProfile | null>(null);
  const [userProfilePicUrl, setUserProfilePicUrl] = useState<string | null>(null);
  const [loras, setLoras] = useState<Lora[]>([]);
  const [userId, setUserId] = useState<string | null>(null);

  const [loadingLoraId, setLoadingLoraId] = useState<string | null>(null);
  const [errorLoraId, setErrorLoraId] = useState<string | null>(null);

  const [trainingMessage, setTrainingMessage] = useState<string | null>(null);

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
    setLoadingLoraId(null);
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

  const handleGenerateVoice = async (loraId: string) => {
    const returnTime = 2000; // 2 seconds buffer

    try {
      // Fetch audio_files for this LoRA
      const audio_files = loras.find((lora) => lora.id === loraId)?.audio_files || [];

      if (audio_files.length === 0) {
        console.error("Failed to fetch audio files");
        setErrorLoraId(loraId);
        setLoadingLoraId(null);
        setTimeout(() => setErrorLoraId(null), returnTime);
        return;
      }

      // 🔍 First, we count total words
      const totalWords = audio_files.reduce((sum: number, file: { text: string }) => {
        if (file?.text) {
          const wordCount = file.text.trim().split(/\s+/).length;
          return sum + wordCount;
        }
        return sum;
      }, 0);

      // ❌ Not enough text — show message
      if (totalWords < MIN_WORDS_FOR_LORA_GEN) {
        setErrorLoraId(loraId);
        setLoadingLoraId(null);
        setTimeout(() => setErrorLoraId(null), returnTime);
        return;
      }

      // ✅ Proceed with voice generation
      console.log("Generating voice for:", loraId, "Total words:", totalWords);
      console.log("Route to another loading page saying generation started (FOR DEV) and route to pay  (FOR PRODUCTION)");

      // ✅ Enough words — now join everything
      const fullText = audio_files
        .map((file: { text: string }) => file.text?.trim())
        .filter(Boolean)
        .join(' ');

      const res = await fetch(`${process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL}/generate-voice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          loraId,
          rawText: fullText,
        }),
      });

      if (res.ok) {
        router.push('../../../CreatorView/TrainingStartedPage') // Redirect to a page indicating training has started
      } else {
        setTrainingMessage("Voice generation could not be started at this time. Please try again later.");
      }

    } catch (err) {
      console.error("Unexpected error:", err);
      setErrorLoraId(loraId);
      setTimeout(() => setErrorLoraId(null), returnTime);
    } finally {
      setLoadingLoraId(null);
    }
  };

  return (
    <main className="creator-dashboard">
      <UserHeader
        role_of_user="Creator"
        username={userData?.username || 'Loading...'}
        profilePicUrl={userProfilePicUrl}
        onBackClick={() => router.push('../../../RoleSelect')}
      />

      {trainingMessage && (
        <p className="training-message">{trainingMessage}</p>
      )}

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
                        {isTrainingCompleted && (
                          <button
                            className="share-button"
                            onClick={() => router.push(`../../../CreatorView/ShareLora/${lora.id}`)}
                          >
                            Share Voice
                          </button>
                        )}
                      </>
                    ) : (
                      <>
                        {loadingLoraId === lora.id ? (
                          <div className="spinner" />
                        ) : (
                          <>
                            <button
                              className="record-more-button"
                              onClick={() => {
                                setLoadingLoraId(lora.id);
                                setTimeout(() => {
                                  router.push(`../../../CreatorView/Creator_recordings/${lora.id}`);
                                }, 1000);
                              }}
                            >
                              Record for this Voice
                            </button>
                            <button
                              className="generate-voice-button"
                              onClick={() => {
                                setLoadingLoraId(lora.id);
                                setTimeout(() => {
                                  handleGenerateVoice(lora.id);
                                }, 1000);
                              }}
                            >
                              Generate Voice
                            </button>
                            {errorLoraId === lora.id && (
                              <p className="error-message">
                                This voice needs <br />
                                more recordings before <br />
                                it can be generated.
                              </p>
                            )}
                          </>
                        )}
                      </>
                    )}
                  </div>

                  <button
                    className="delete-button"
                    onClick={() => {
                      if (isTraining || isTrainingCompleted) return; // 🔒 disable delete
                      handleDeleteLora(lora);
                    }}
                    title="Delete Voice"
                    disabled={isTraining || isTrainingCompleted} // also disable click visually
                  >
                    <img src="/delete-icon.svg" alt="Delete" />
                  </button>
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