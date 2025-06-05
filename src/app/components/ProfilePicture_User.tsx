'use client';

import { useEffect, useRef, useState } from 'react';
import {
  getAuthenticatedUser,
  getUSERProfile,
  generateUSERProfilePicSignedUrl,
  uploadToUSERProfilePics
} from './db_funcs/db_funcs';

export default function ProfilePicture_user() {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const fetchProfilePic = async () => {
      const user = await getAuthenticatedUser();
      if (!user) return;

      const userData = await getUSERProfile(user.id);
      const userProfilePicUrl = userData?.profile_pic_url;
      if (!userProfilePicUrl) return;

      const signedUrl = await generateUSERProfilePicSignedUrl(userProfilePicUrl, 60);
      if (!signedUrl) return;

      setImageUrl(signedUrl);
    };

    fetchProfilePic();
  }, []);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMsg(null); // Clear previous errors
    const file = event.target.files?.[0];
    if (!file) return;

    // Check file size (max 1MB = 1,048,576 bytes)
    if (file.size > 1048576) {
      setErrorMsg('File size exceeds 1MB. Please upload a smaller image.');
      return;
    }

    const user = await getAuthenticatedUser();
    if (!user) return;

    const filePath = `${user.id}/${Date.now()}-${file.name}`;

    const success = await uploadToUSERProfilePics(user.id, filePath, file);
    if (!success) {
      setErrorMsg('Failed to update profile picture info.');
      return;
    }

    const signedUrl = await generateUSERProfilePicSignedUrl(filePath, 60);
    if (!signedUrl) return;

    setImageUrl(signedUrl);
  };

  return (
    <>
      <div
        className="profile-pic-upload"
        onClick={() => fileInputRef.current?.click()}
        style={{ position: 'relative' }}
      >
        {imageUrl ? (
          <img src={imageUrl} alt="Profile" className="profile-pic-image" />
        ) : (
          '+'
        )}
      </div>
      <input
        type="file"
        accept="image/*"
        style={{ display: 'none' }}
        ref={fileInputRef}
        onChange={handleUpload}
      />
      {errorMsg && (
        <p style={{ color: 'red', marginTop: '0.5rem', fontWeight: '600' }}>
          {errorMsg}
        </p>
      )}
    </>
  );
}