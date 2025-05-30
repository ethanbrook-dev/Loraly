import { supabase } from '../../../supabase/client';

export async function uploadProfilePicture(file: File) {
  const { data: { user }, error: userError } = await supabase.auth.getUser();
  if (userError || !user) throw new Error('User not authenticated');

  const fileExt = file.name.split('.').pop();
  const filePath = `avatars/${user.id}.${fileExt}`;

  const { error: uploadError } = await supabase.storage
    .from('profile-pics')
    .upload(filePath, file, {
      cacheControl: '3600',
      upsert: true,
    });

  if (uploadError) throw uploadError;

  // Update the user's profile with the new path
  const { error: updateError } = await supabase
    .from('profiles')
    .update({ profile_pic_url: filePath })
    .eq('id', user.id);

  if (updateError) throw updateError;

  return filePath;
}

export async function getProfilePictureUrl(): Promise<string | null> {
  const { data: { user }, error } = await supabase.auth.getUser();
  if (error || !user) return null;

  const { data, error: profileError } = await supabase
    .from('profiles')
    .select('profile_pic_url')
    .eq('id', user.id)
    .single();

  if (profileError || !data?.profile_pic_url) return null;

  const { data: signedUrlData } = await supabase.storage
    .from('profile-pics')
    .createSignedUrl(data.profile_pic_url, 60 * 60); // 1 hour

  return signedUrlData?.signedUrl || null;
}