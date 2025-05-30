'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { supabase } from '../../../../supabase/client';
import ProfilePicture_lora from '../../components/ProfilePicture_Lora';
import UserHeader from '../../components/UserHeader';
import { MIN_WORDS_FOR_LORA_GEN } from '../../constants/MIN_WORDS_FOR_LORA_GEN';
import '../../../../styles/CreatorViewStyles.css';
import '../../../../styles/LoraCardStyles.css';

type Lora = {
  id: string;
  name: string;
  profile_pic_url: string | null;
};

export default function CreatorDashboard() {
  const router = useRouter();

  const [username, setUsername] = useState('Loading...');
  const [profilePicUrl, setProfilePicUrl] = useState<string | null>(null);
  const [loras, setLoras] = useState<Lora[]>([]);
  const [userId, setUserId] = useState<string | null>(null);
  const [userEmail, setUserEmail] = useState<string | null>(null);

  const [loadingLoraId, setLoadingLoraId] = useState<string | null>(null);
  const [errorLoraId, setErrorLoraId] = useState<string | null>(null);

  // Fetch user profile
  useEffect(() => {
    async function fetchUserProfile() {
      const {
        data: { user },
      } = await supabase.auth.getUser();
      if (!user) return;

      setUserId(user.id);
      setUserEmail(user.email ?? null);

      const { data: profile, error } = await supabase
        .from('profiles')
        .select('username, profile_pic_url')
        .eq('id', user.id)
        .single();

      if (!profile || error) {
        setUsername('Unknown User');
        return;
      }

      setUsername(profile.username);

      if (profile.profile_pic_url) {
        const { data: signedUrlData } = await supabase.storage
          .from('avatars')
          .createSignedUrl(profile.profile_pic_url, 60);
        if (signedUrlData?.signedUrl) setProfilePicUrl(signedUrlData.signedUrl);
      }
    }

    fetchUserProfile();
  }, []);

  // Fetch LoRAs created by the user
  useEffect(() => {
    async function fetchLoras() {
      if (!userId) return;

      const { data, error } = await supabase
        .from('loras')
        .select('id, name, profile_pic_url')
        .eq('creator_id', userId);

      if (!error && data) setLoras(data);
    }

    fetchLoras();
  }, [userId]);

  useEffect(() => {
    // Reset loading state when component mounts
    setLoadingLoraId(null);
  }, []);

  // Handle LoRA Deletion
  const handleDeleteLora = async (loraId: string, profilePicUrl: string | null) => {
    if (!confirm('Are you sure you want to delete this voice?')) return;

    // Delete profile pic from storage if exists
    if (profilePicUrl) {
      await supabase.storage.from('avatars').remove([profilePicUrl]);
    }

    // Delete LoRA from DB
    const { error } = await supabase.from('loras').delete().eq('id', loraId);

    if (!error) {
      setLoras((prev) => prev.filter((lora) => lora.id !== loraId));
    } else {
      console.error('Error deleting LoRA:', error.message);
    }
  };

  const handleGenerateVoice = async (loraId: string) => {
    const returnTime = 2000; // 2 seconds buffer

    try {
      // Fetch audio_files for this LoRA
      const { data, error } = await supabase
        .from('loras')
        .select('audio_files')
        .eq('id', loraId)
        .single();

      if (error || !data) {
        console.error("Failed to fetch audio files:", error?.message);
        setErrorLoraId(loraId);
        setLoadingLoraId(null);
        setTimeout(() => setErrorLoraId(null), returnTime);
        return;
      }

      const audioFiles = data.audio_files || [];

      // 🔍 First, we count total words
      const totalWords = audioFiles.reduce((sum: number, file: { text: string }) => {
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
      const fullText = audioFiles
        .map((file: { text: string }) => file.text?.trim())
        .filter(Boolean)
        .join(' ');

      // ✅ Send to backend
      const pythonBackendUrl = process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL || 'http://localhost:8000'; //fallback

      const res = await fetch(`${pythonBackendUrl}/generate-voice`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          loraId,
          rawText: fullText,
          userEmail
        }),
      });

      if (res.ok) {
        alert('TODO: SHOW MESSAGE (NICE UI INSTEAD OF ALERT)');
      } else {
        alert(`Something went wrong. Please try again.`);
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
        username={username}
        profilePicUrl={profilePicUrl}
        onBackClick={() => router.push('../../../RoleSelect')}
      />

      <section className="creator-voice-section">
        {loras.length === 0 ? (
          <p className="italic">You haven’t created any voices yet.</p>
        ) : (
          <div className="loras-scroll-container">
            {loras.map((lora) => (
              <div key={lora.id} className="lora-card">
                <div className="lora-info">
                  <ProfilePicture_lora
                    loraId={lora.id}
                    onUploadSuccess={async (newUrl) => {
                      const { error } = await supabase
                        .from('loras')
                        .update({ profile_pic_url: newUrl })
                        .eq('id', lora.id);

                      if (!error) {
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
                          This voice needs <br /> more recordings before <br /> it can be generated.
                        </p>
                      )}
                    </>
                  )}
                </div>

                <button
                  className="delete-button"
                  onClick={() => handleDeleteLora(lora.id, lora.profile_pic_url)}
                  title="Delete Voice"
                >
                  <img src="/delete-icon.svg" alt="Delete" />
                </button>
              </div>
            ))}
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