// Sharing lora page (search like IG)

'use client';

import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import Image from 'next/image';

import {
  generateUSERProfilePicSignedUrl,
  fetchMatchingUsersBySimilarName,
  getAllLorasSharedWithUser,
  updateLorasSharedWithUser,
  getLORAProfilePicUrl,
  copyLORAProfilePicToSharedBucket,
  generateSharedLORAProfilePicSignedUrl
} from '../../components/db_funcs/db_funcs';

type ShareRecipient = {
  id: string;
  username: string;
  profile_pic_url: string | null;
};

type ShareLoraPageProps = {
  loraid: string;
  loraName: string;
  onShareComplete?: () => void;
};

export default function ShareLoraPage({ loraid, loraName, onShareComplete }: ShareLoraPageProps) {
  const router = useRouter();

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
    setShareStatus(null);

    const sharedLoras = await getAllLorasSharedWithUser(user);
    if (sharedLoras === null) {
      setShareStatus('Failed to fetch user data.');
      return;
    }

    if (sharedLoras.some((l) => l.id === loraid)) {
      setShareStatus(`${loraName} was already shared with ${user.username}`);
      return;
    }

    const picPath = await getLORAProfilePicUrl(loraid as string);
    let copiedPath = '';

    if (picPath) {
      const fileExt = picPath.split('.').pop() || 'png';
      copiedPath = `${user.id}/${loraid}.${fileExt}`;

      const copied = await copyLORAProfilePicToSharedBucket(picPath, copiedPath);
      if (!copied) {
        setShareStatus('Failed to copy profile picture.');
        return;
      }

      const url = await generateSharedLORAProfilePicSignedUrl(copiedPath);
      if (!url) {
        setShareStatus('Failed to generate signed URL.');
        return;
      }
    }

    const updatedLoras = [...sharedLoras, {
      id: loraid as string,
      name: loraName as string,
      shared_pic_url: copiedPath
    }];

    const success = await updateLorasSharedWithUser(user.id, updatedLoras);

    if (!success) {
      setShareStatus('Failed to share. Try again.');
      return;
    }

    setShareStatus(`${loraName} was successfully shared with ${user.username}!`);

    if (onShareComplete) onShareComplete();
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
              <div style={{ width: '100px', height: '100px', position: 'relative' }}>
                <Image
                  src={user.profile_pic_url || '/default-user-profile-pic.png'}
                  alt="Profile"
                  fill
                  style={{ objectFit: 'cover' }}
                  className="user-avatar"
                />
              </div>
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