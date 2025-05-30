'use client';

import { useRef, useState, useEffect } from 'react';
import { supabase } from '../../../supabase/client';

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

      const { data, error } = await supabase
        .from('loras')
        .select('profile_pic_url')
        .eq('id', loraId)
        .single();

      if (error || !data?.profile_pic_url) return;

      const { data: signedUrlData, error: signedUrlError } = await supabase
        .storage
        .from('lora-profile-pics')
        .createSignedUrl(data.profile_pic_url, 60);

      if (signedUrlError || !signedUrlData?.signedUrl) return;

      setImageUrl(signedUrlData.signedUrl);
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

    const { data: { user }, error: userError } = await supabase.auth.getUser();
    if (!user || userError) {
      setErrorMsg('User not authenticated.');
      return;
    }

    const filePath = `${user.id}/${Date.now()}-${file.name}`;

    const { error: uploadError } = await supabase.storage
      .from('lora-profile-pics')
      .upload(filePath, file, {
        cacheControl: '3600',
        upsert: true,
      });

    if (uploadError) {
      console.error('Upload failed:', uploadError);
      setErrorMsg('Upload failed. Please try again.');
      return;
    }

    const { data: signedUrlData, error: signedUrlError } = await supabase
      .storage
      .from('lora-profile-pics')
      .createSignedUrl(filePath, 60);

    if (signedUrlError || !signedUrlData?.signedUrl) {
      setErrorMsg('Could not generate preview.');
      return;
    }

    setImageUrl(signedUrlData.signedUrl);
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