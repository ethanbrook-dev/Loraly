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
};

export default function ShareLoraPage() {
  const router = useRouter();
  const params = useParams();
  const { loraid, loraName } = params;

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchUser[]>([]);
  const [isSearching, setIsSearching] = useState(false);

  useEffect(() => {
    if (query.trim() === '') {
      setResults([]);
      return;
    }

    fetchMatchingUsers(query);
  }, [query]);

  async function fetchMatchingUsers(search: string) {
    setIsSearching(true);

    const usersWithSimilarName = await fetchMatchingUsersBySimilarName(search);

    const signedUsers = await Promise.all(
      usersWithSimilarName.map(async (user) => {
        const signedUrl = user.profile_pic_url
          ? await generateUSERProfilePicSignedUrl(user.profile_pic_url)
          : null;
        return {
          id: user.id,
          username: user.username,
          profile_pic_url: signedUrl
        };
      })
    );

    setResults(signedUsers);
    setIsSearching(false);
  }

  function handleShare(user: SearchUser) {
    console.log("user clicked with details as follows:\nname: " + user.username + "\nid: " + user.id + "\n\nand the lora we want to share with him is:\nloraName: " + loraName + "\nloraid: " + loraid)
    
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

      {query.trim() !== '' && (
        <div className="search-results">
          {results.map((user) => (
            <div key={user.id}
              className="search-user-card"
              onClick={() => handleShare(user)}>
              <img
                src={user.profile_pic_url || ''}
                alt="Profile"
                className="user-avatar"
              />
              <span>{user.username}</span>
            </div>
          ))}
          {!isSearching && query.trim() !== '' && results.length === 0 && (
            <div className="text-gray-500 text-center mt-4 italic">
              No users match that name.
            </div>
          )}
        </div>
      )}

      <button className="share-back-button" onClick={() => router.back()}>
        Back to Dashboard
      </button>
    </main>
  );
}