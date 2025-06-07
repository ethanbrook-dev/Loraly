'use client';

import { useRouter, useParams } from 'next/navigation';
import { useEffect, useState } from 'react';

import {
  generateUSERProfilePicSignedUrl,
  fetchMatchingUsersBySimilarName,
  getAllLorasSharedWithUser,
  updateLorasSharedWithUser
} from '../../../../components/db_funcs/db_funcs';

type ShareRecipient = {
  id: string;
  username: string;
  profile_pic_url: string | null;
};

export default function ShareLoraPage() {
  const router = useRouter();
  const params = useParams();
  const { loraid, loraName } = params;

  const [query, setQuery] = useState('');
  const [results, setResults] = useState<ShareRecipient[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [shareStatus, setShareStatus] = useState<string | null>(null);

  useEffect(() => {
    if (query.trim() === '') {
      setResults([]);
      return;
    }

    fetchMatchingUsers(query);
  }, [query]);

  useEffect(() => {
    if (shareStatus) {
      const timeout = setTimeout(() => setShareStatus(null), 3000);
      return () => clearTimeout(timeout);
    }
  }, [shareStatus]);

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

  async function handleShare(user: ShareRecipient) {
    setShareStatus(null); // clear previous status

    const loras_shared_w_me = await getAllLorasSharedWithUser(user);

    if (loras_shared_w_me == null) {
      setShareStatus('Failed to fetch user data.');
      return;
    }

    if (loras_shared_w_me.includes(loraid as string)) {
      setShareStatus(`${loraName} was already shared with ${user.username}`);
      return;
    }

    const updatedLoras = [...loras_shared_w_me, loraid as string];

    const updateSuccessfull = await updateLorasSharedWithUser(user.id, updatedLoras);
    if (!updateSuccessfull) {
      setShareStatus('Failed to share. Try again.');
      return;
    }

    setShareStatus(`${loraName} was successfully shared with ${user.username}!`);
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
      {shareStatus && (
        <div className="share-status-message">
          {shareStatus}
        </div>
      )}
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