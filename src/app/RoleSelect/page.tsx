// Role select: Creator or Explorer

'use client';

// React imports
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';

// Supabase import
import { supabase } from '../../../supabase/client';

// Component import
import ProfilePicture_user from '../components/ProfilePicture_User';

export default function RoleSelect() {
  const router = useRouter();
  const [username, setUsername] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      const { data: { user } } = await supabase.auth.getUser();
      if (user) {
        const { data: profile } = await supabase
          .from('profiles')
          .select('username')
          .eq('id', user.id)
          .single();

        if (profile) {
          setUsername(profile.username);
        }
      }
    })();
  }, []);

  return (
    <div className="role-select-container">
      <ProfilePicture_user />

      <h1 className="role-select-question">
        What brings you here {username}?
      </h1>

      <div className="role-select-buttons">
        <button
          className="role-button creator-button"
          onClick={() => router.push('/CreatorView/Creator_dashboard')}
        >
          <span className="title">I’m a Creator</span>
          <span className="subtitle">I want to share a voice</span>
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