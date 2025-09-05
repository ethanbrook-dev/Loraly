'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { supabase } from '../../../supabase/client';
import ProfilePicture_user from '../components/ProfilePicture_User';

export default function RoleSelect() {
  const router = useRouter();
  const [username, setUsername] = useState<string | null>(null);
  const [userId, setUserId] = useState<string | null>(null);
  const [hasEnvVars, setHasEnvVars] = useState<boolean>(false);

  useEffect(() => {
    (async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        setUserId(user.id);
        const { data: profile } = await supabase
          .from('profiles')
          .select('username, env_vars_encrypted')
          .eq('id', user.id)
          .single();

        if (profile) {
          setUsername(profile.username);
          setHasEnvVars(!!(profile.env_vars_encrypted && profile.env_vars_encrypted.trim().length > 0));
        }
      }
    })();
  }, []);

  const handleCreatorClick = () => {
    if (!userId) return;
    if (!hasEnvVars) {
      router.push('/RoleSelect/UserEnvForm');
    } else {
      router.push('/CreatorView/Creator_dashboard');
    }
  };

  return (
    <div className="role-select-container">
      <ProfilePicture_user />
      <h1 className="role-select-question">
        What brings you here {username}?
      </h1>

      <div className="role-select-buttons">
        <button
          className="role-button creator-button"
          onClick={handleCreatorClick}
        >
          <span className="title">I’m a Creator</span>
          <span className="subtitle">I want to create and share a voice</span>
        </button>

        <button
          className="role-button explorer-button"
          onClick={() => router.push('/ExplorerView/Explorer_dashboard')}
        >
          <span className="title">I’m an Explorer</span>
          <span className="subtitle">I want to connect with a voice</span>
        </button>
      </div>
    </div>
  );
}
