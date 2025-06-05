import { supabase } from "../../../../supabase/client";
import type { User } from '@supabase/supabase-js';

const LORAS_TABLE_NAME = 'loras';
const LORAS_TABLE_ID_COL = 'id';
const LORAS_TABLE_PROFILE_PIC_COL = 'profile_pic_url';
const LORA_PROFILE_PIC_BUCKET_NAME = 'lora-profile-pics';

export async function getAuthenticatedUser(): Promise<User | null> {
  const { data: { user }, error } = await supabase.auth.getUser();

  if (error || !user) {
    console.error('User not authenticated:', error);
    return null;
  }

  return user;
}

export async function getLORAProfilePicUrl(
    loraId: string
): Promise<string | null> {
    const { data, error } = await supabase
        .from(LORAS_TABLE_NAME)
        .select(LORAS_TABLE_PROFILE_PIC_COL)
        .eq(LORAS_TABLE_ID_COL, loraId)
        .single();

    if (error || !data?.profile_pic_url) {
        console.error('Error fetching ' + LORAS_TABLE_PROFILE_PIC_COL + ':', error);
        return null;
    }

    return data.profile_pic_url;
}

export async function generateLoraProfilePicSignedUrl(
    filePath: string,
    expiresInSeconds = 60 //default to 60 seconds
): Promise<string | null> {
    const { data, error } = await supabase
        .storage
        .from(LORA_PROFILE_PIC_BUCKET_NAME)
        .createSignedUrl(filePath, expiresInSeconds);

    if (error || !data?.signedUrl) {
        console.error('Error creating signed URL:', error);
        return null;
    }

    return data.signedUrl;
}

export async function uploadToLoraProfilePics(
  filePath: string,
  file: File
): Promise<boolean> {
  const { error } = await supabase.storage
    .from(LORA_PROFILE_PIC_BUCKET_NAME)
    .upload(filePath, file, {
      cacheControl: '3600',
      upsert: true,
    });

  if (error) {
    console.error('Upload error:', error);
    return false;
  }

  return true;
}
