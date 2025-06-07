'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

import {
  getAuthenticatedUser,
  getUSERProfile,
  generateUSERProfilePicSignedUrl,
  generateSharedLORAProfilePicSignedUrl,
} from '../../components/db_funcs/db_funcs';

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
          <p className="no-loras-text">Nothing here just yet. When someone shares a voice with you, it’ll show up here 💌</p>
        ) : (
          userData?.loras_shared_w_me.map((lora) => (
            <div key={lora.id} className="lora-card">
              <img
                src={signedLoraPicUrls[lora.id]}
                alt="LoRA Profile"
                className="lora-profile-pic"
              />

              <div className="lora-details">
                <h3 className="lora-name">{lora.name}</h3>

                <div className="lora-card-buttons">
                  <button
                    className="chat-button"
                    onClick={() => router.push(`/ExplorerView/Chat/${lora.id}`)}
                  >
                    Chat
                  </button>

                  <button
                    className="delete-button"
                    onClick={() => alert(`Delete ${lora.id}`)}
                  >
                    Delete
                  </button>
                </div>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}