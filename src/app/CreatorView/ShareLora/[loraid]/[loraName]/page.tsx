'use client';

import { useRouter, useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import {
  generateUSERProfilePicSignedUrl,
  fetchMatchingUsersBySimilarName
} from '../../../../components/db_funcs/db_funcs';
import { supabase } from '../../../../../../supabase/client';

type SearchUser = {
    id: string;
    username: string;
    profile_pic_url: string | null;
    loras_shared_w_me: string[] | null;
};

export default function ShareLoraPage() {
  const router = useRouter();
  const params = useParams();
  const { loraid, loraName } = params;

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchUser[]>([]);

  useEffect(() => {
    const delayDebounce = setTimeout(() => {
      if (query.trim() === '') {
        setResults([]);
        return;
      }
      fetchMatchingUsers(query);
    }, 100); // Debounce for 100ms

    return () => clearTimeout(delayDebounce);
  }, [query]);

  async function fetchMatchingUsers(search: string) {
    const usersWithSimilarName = await fetchMatchingUsersBySimilarName(search);

    const signedUsers = await Promise.all(
      usersWithSimilarName.map(async (user) => {
        const signedUrl = user.profile_pic_url
          ? await generateUSERProfilePicSignedUrl(user.profile_pic_url)
          : null;
        return {
          id: user.id,
          username: user.username,
          profile_pic_url: signedUrl,
          loras_shared_w_me: user.loras_shared_w_me
        };
      })
    );

    setResults(signedUsers);

  }

  return (
    <main className="share-container">
      <h1 className="share-title">Share &quot;{loraName}&quot; with ... ?</h1>

      <input
        type="text"
        placeholder="Search usernames..."
        className="share-search-input"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />

      <div className="search-results">
        {results.map((user) => (
          <div key={user.id} className="search-user-card">
            <img
              src={user.profile_pic_url || ''}
              alt="Profile"
              className="user-avatar"
            />
            <span>{user.username}</span>
          </div>
        ))}
      </div>

      <button className="share-back-button" onClick={() => router.back()}>
        Back to Dashboard
      </button>
    </main>
  );
}