'use client';

// React imports
import { useRef, useState, useEffect } from 'react';

// Database functions import
import {
  getLORAProfilePicUrl,
  generateLORAProfilePicSignedUrl,
  updateLORAProfilePic,
  getAuthenticatedUser,
  uploadToLORAProfilePics
} from './db_funcs/db_funcs';

type Props = {
  loraId: string;
  currentProfilePicPath?: string | null;
  onUploadSuccess: (url: string) => void;
};

export default function ProfilePicture_lora({ loraId, currentProfilePicPath, onUploadSuccess }: Props) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    async function fetchProfilePic() {
      if (!loraId) return;

      const loraProfilePicUrl = await getLORAProfilePicUrl(loraId);
      if (!loraProfilePicUrl) return;

      const signedUrl = await generateLORAProfilePicSignedUrl(loraProfilePicUrl, 60);
      if (!signedUrl) return;

      setImageUrl(signedUrl);
    }

    fetchProfilePic();
  }, [loraId]);

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMsg(null);
    const file = event.target.files?.[0];
    if (!file) return;

    if (file.size > 1048576) {
      setErrorMsg('File size exceeds 1MB. Please upload a smaller image.');
      return;
    }

    const user = await getAuthenticatedUser();
    if (!user) {
      setErrorMsg('User not authenticated.');
      return;
    }

    const filePath = `${user.id}/${Date.now()}-${file.name}`;

    const success = await uploadToLORAProfilePics(filePath, file, currentProfilePicPath || undefined);
    if (!success) {
      setErrorMsg('Failed to upload image.');
      return;
    }

    const dbUpdated = await updateLORAProfilePic(loraId, filePath);
    if (!dbUpdated) {
      setErrorMsg('Failed to update profile picture in DB.');
      return;
    }

    const signedUrl = await generateLORAProfilePicSignedUrl(filePath, 60);
    if (!signedUrl) return;

    setImageUrl(signedUrl);
    onUploadSuccess(filePath); // notify parent with the file path for DB update
  };

  return (
    <>
      <div
        className="profile-pic-upload"
        onClick={() => fileInputRef.current?.click()}
        style={{ position: 'relative', cursor: 'pointer' }}
      >
        {imageUrl ? (
          <img src={imageUrl} alt="Voice Profile" className="profile-pic-image" />
        ) : (
          <span style={{ fontSize: '2rem', lineHeight: 1 }}>+</span>
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