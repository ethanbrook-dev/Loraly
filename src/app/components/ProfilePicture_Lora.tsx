'use client';

import { useRef, useState, useEffect } from 'react';
import {
  getLORAProfilePicUrl,
  generateLoraProfilePicSignedUrl,
  getAuthenticatedUser,
  uploadToLoraProfilePics
} from './db_funcs/db_funcs';

type Props = {
  loraId: string;
  onUploadSuccess: (url: string) => void;
};

export default function ProfilePicture_lora({ loraId, onUploadSuccess }: Props) {
  const [imageUrl, setImageUrl] = useState<string | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    async function fetchProfilePic() {
      if (!loraId) return;

      const loraProfilePicUrl = await getLORAProfilePicUrl(loraId);
      if (!loraProfilePicUrl) return;

      const signedUrl = await generateLoraProfilePicSignedUrl(loraProfilePicUrl, 60);
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

    const success = await uploadToLoraProfilePics(filePath, file);
    if (!success) {
      setErrorMsg('Failed to upload image.');
      return;
    }

    const signedUrl = await generateLoraProfilePicSignedUrl(filePath, 60);
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
          <img src={imageUrl} alt="LoRA Profile" className="profile-pic-image" />
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