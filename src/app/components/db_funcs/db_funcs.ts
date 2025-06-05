import { supabase } from "../../../../supabase/client";
import type { User } from '@supabase/supabase-js';

// USER variables:
const USER_TABLE_NAME = 'profiles';
const USER_TABLE_ID_COL = 'id';
const USER_TABLE_PROFILE_PIC_COL = 'profile_pic_url';
const USER_PROFILE_PIC_BUCKET_NAME = 'avatars';


// LORA variables:
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

export async function getUSERProfilePicUrl(
    userID: string
): Promise<string | null> {
    const { data, error } = await supabase
        .from(USER_TABLE_NAME)
        .select(USER_TABLE_PROFILE_PIC_COL)
        .eq(USER_TABLE_ID_COL, userID)
        .single();

    if (error || !data?.profile_pic_url) {
        console.error('Error fetching ' + USER_TABLE_PROFILE_PIC_COL + ':', error);
        return null;
    }

    return data.profile_pic_url;
}

export async function generateUSERProfilePicSignedUrl(
    filePath: string,
    expiresInSeconds = 60 //default to 60 seconds
): Promise<string | null> {
    const { data, error } = await supabase
        .storage
        .from(USER_PROFILE_PIC_BUCKET_NAME)
        .createSignedUrl(filePath, expiresInSeconds);

    if (error || !data?.signedUrl) {
        console.error('Error creating signed URL:', error);
        return null;
    }

    return data.signedUrl;
}

export async function uploadToUSERProfilePics(
    userID: string,
    filePath: string,
    file: File
): Promise<boolean> {
    const { error } = await supabase.storage
        .from(USER_PROFILE_PIC_BUCKET_NAME)
        .upload(filePath, file, {
            cacheControl: '3600',
            upsert: true,
        });

    if (error) {
        console.error('Upload error:', error);
        return false;
    }

    const { error: updateError } = await supabase
        .from(USER_TABLE_NAME)
        .update({ profile_pic_url: filePath })
        .eq('id', userID);

    if (updateError) {
        console.error('DB update failed:', updateError);
        return false;
    }

    return true;
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

export async function generateLORAProfilePicSignedUrl(
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

export async function uploadToLORAProfilePics(
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

export async function initLORA(
    userId: string,
    name: string
): Promise<string | null> {
    const { data, error } = await supabase
        .from(LORAS_TABLE_NAME)
        .insert([
            {
                creator_id: userId,
                name,
                profile_pic_url: null,
                audio_files: []
            }
        ])
        .select()
        .single();

    if (error || !data?.id) {
        return null;
    }

    return data.id;
}

export async function updateLORAProfilePic(
    loraID: string,
    imageUrl: string | null
): Promise<boolean> {
    const { error } = await supabase
        .from(LORAS_TABLE_NAME)
        .update({ profile_pic_url: imageUrl })
        .eq(LORAS_TABLE_ID_COL, loraID);

    if (error) return false;

    return true;
}