// Explorer dashboard

'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Image from 'next/image';

import {
  getAuthenticatedUser,
  getUSERProfile,
  generateUSERProfilePicSignedUrl,
  generateSharedLORAProfilePicSignedUrl,
  deleteSharedLORAFromUser
} from '../../components/db_funcs/db_funcs';

import ChatInterface from '@/app/ExplorerView/ChatInterface/ChatInterface';

import UserHeader from '@/app/components/UserHeader';
import '../../../../styles/ExplorerViewStyles.css';

type SharedLora = {
  id: string;
  name: string;
  shared_pic_url: string; // Just the path, not signed yet
};

type UserProfile = {
  id: string;
  username: string;
  email: string | null;
  profile_pic_url: string | null;
  loras_created: string[];
  loras_shared_w_me: SharedLora[];
};

export default function ExplorerDashboard() {
  const router = useRouter();

  const [userData, setUserData] = useState<UserProfile | null>(null);
  const [userProfilePicUrl, setUserProfilePicUrl] = useState<string | null>(null);
  const [signedLoraPicUrls, setSignedLoraPicUrls] = useState<Record<string, string>>({});

  const [showModal, setShowModal] = useState(false);
  const [selectedLora, setSelectedLora] = useState<SharedLora | null>(null);

  const [loraIdForChatInterface, setLoraIdForChatInterface] = useState<string | null>(null);
  const [loraNameForChatInterface, setLoraNameForChatInterface] = useState<string | null>(null);

  // Fetch user profile and signed URLs
  useEffect(() => {
    async function fetchUserProfile() {
      const user = await getAuthenticatedUser();
      if (!user) return;

      const profile = await getUSERProfile(user.id);
      if (!profile) {
        setUserData(null);
        return;
      }

      setUserData(profile);

      // Profile pic
      if (profile.profile_pic_url) {
        const signed = await generateUSERProfilePicSignedUrl(profile.profile_pic_url, 60);
        if (signed) setUserProfilePicUrl(signed);
      }

      // Shared LoRA pics
      const picMap: Record<string, string> = {};
      await Promise.all(
        profile.loras_shared_w_me.map(async (lora: SharedLora) => {
          const signedUrl = await generateSharedLORAProfilePicSignedUrl(lora.shared_pic_url, 60);
          if (signedUrl) picMap[lora.id] = signedUrl;
        })
      );

      setSignedLoraPicUrls(picMap);
    }

    fetchUserProfile();
  }, []);

  if (loraIdForChatInterface && loraNameForChatInterface) {
    return <ChatInterface loraid={loraIdForChatInterface} loraName={loraNameForChatInterface} />
  }

  return (
    <div className="explorer-dashboard-container">
      <UserHeader
        role_of_user="Explorer"
        username={userData?.username || 'Loading...'}
        profilePicUrl={userProfilePicUrl}
        onBackClick={() => router.push('../../../RoleSelect')}
      />

      <div className="shared-loras-container">
        {userData?.loras_shared_w_me.length === 0 ? (
          <p className="no-loras-text">Nothing here just yet. When someone shares a voice with you, it’ll show up here</p>
        ) : (
          userData?.loras_shared_w_me.map((lora) => (
            <div key={lora.id} className="lora-card">
              <div style={{ width: '80px', height: '80px', position: 'relative' }}>
                <Image
                  src={signedLoraPicUrls[lora.id]}
                  alt="LoRA Profile"
                  fill
                  style={{ objectFit: 'cover' }}
                  className="lora-profile-pic"
                />
              </div>

              <div className="lora-details">
                <h3 className="lora-name">{lora.name}</h3>

                <div className="lora-card-buttons">
                  <button
                    className="chat-button"
                    onClick={() => {
                      setLoraIdForChatInterface(lora.id);
                      setLoraNameForChatInterface(lora.name);
                    }}
                  >
                    Chat
                  </button>

                  <button
                    className="delete-button"
                    onClick={() => {
                      setSelectedLora(lora);
                      setShowModal(true);
                    }}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))
        )}

        {showModal && selectedLora && (
          <ConfirmDeleteModal
            onConfirm={async () => {
              setShowModal(false);

              const user = await getAuthenticatedUser();
              if (!user || !selectedLora) return;

              const deletedFromUser = await deleteSharedLORAFromUser(user.id, selectedLora.id);

              if (deletedFromUser) {
                // Update UI
                setUserData((prev) =>
                  prev
                    ? {
                      ...prev,
                      loras_shared_w_me: prev.loras_shared_w_me.filter((l) => l.id !== selectedLora.id),
                    }
                    : null
                );
              } else {
                alert("Failed to delete shared LoRA.");
              }

              setSelectedLora(null);
            }}
            onCancel={() => {
              setShowModal(false);
              setSelectedLora(null);
            }}
          />
        )}

      </div>
    </div>
  );
}

function ConfirmDeleteModal({ onConfirm, onCancel }: { onConfirm: () => void; onCancel: () => void }) {
  return (
    <div className="modal-overlay">
      <div className="modal-content">
        <p>Are you sure you want to delete this shared voice?</p>
        <div className="modal-buttons">
          <button className="confirm-button" onClick={onConfirm}>Yes, delete</button>
          <button className="cancel-button" onClick={onCancel}>Cancel</button>
        </div>
      </div>
    </div>
  );
}