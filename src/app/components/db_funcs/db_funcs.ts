import { supabase } from "../../../../supabase/client";
import type { User } from '@supabase/supabase-js';

// USER variables:
const USER_TABLE_NAME = 'profiles';
const USER_TABLE_ID_COL = 'id';
const USER_TABLE_NAME_COL = 'username';
const USER_TABLE_PROFILE_PIC_COL = 'profile_pic_url';
const USER_TABLE_LORAS_SHARED_WITH_COL = 'loras_shared_w_me';
const USER_SHARING_INFO_SELECT = [
    USER_TABLE_ID_COL,
    USER_TABLE_NAME_COL,
    USER_TABLE_PROFILE_PIC_COL,
    USER_TABLE_LORAS_SHARED_WITH_COL,
].join(', ');
const USER_PROFILE_PIC_BUCKET_NAME = 'avatars';

// LORA variables:
const LORAS_TABLE_NAME = 'loras';
const LORAS_TABLE_ID_COL = 'id';
const LORAS_TABLE_CREATOR_COL = 'creator_id';
const LORAS_TABLE_PROFILE_PIC_COL = 'profile_pic_url';
const LORAS_TABLE_STATUS_COL = 'training_status'; //status is updated in backend
const LORA_PROFILE_PIC_BUCKET_NAME = 'lora-profile-pics';

type AudioFile = {
    name: string;
    text: string;
    duration: number;
};

type Lora = {
    id: string;
    creator_id: string;
    name: string;
    profile_pic_url: string | null;
    audio_files: AudioFile[];
    training_status: string;
};

type Recording = {
    name: string;
    duration: number;
    text: string;
};

type VoiceData = {
    id: string;
    creator_id: string;
    recordings: Recording[];
};

type ShareRecipient = {
    id: string;
    username: string;
    profile_pic_url: string | null;
    loras_shared_w_me: string[] | null;
};

function toShareRecipient(user: any): ShareRecipient {
    return {
        id: user[USER_TABLE_ID_COL],
        username: user[USER_TABLE_NAME_COL],
        profile_pic_url: user[USER_TABLE_PROFILE_PIC_COL],
        loras_shared_w_me: user[USER_TABLE_LORAS_SHARED_WITH_COL],
    };
}

export async function getAuthenticatedUser(): Promise<User | null> {
    const { data: { user }, error } = await supabase.auth.getUser();

    if (error || !user) {
        console.error('User not authenticated:', error);
        return null;
    }

    return user;
}

export async function getUSERProfile(
    userID: string
): Promise<any | null> {
    const { data, error } = await supabase
        .from(USER_TABLE_NAME)
        .select('*')
        .eq(USER_TABLE_ID_COL, userID)
        .single();

    if (error || !data) {
        console.error('Error fetching full user profile:', error);
        return null;
    }

    return data;
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

export async function fetchMatchingUsersBySimilarName(
    name: string
): Promise<ShareRecipient[]> {
    const { data, error } = await supabase
        .from(USER_TABLE_NAME)
        .select(USER_SHARING_INFO_SELECT)
        .ilike(USER_TABLE_NAME_COL, `${name}%`);

    if (error || !data) {
        console.error('Error fetching users:', error);
        return [];
    }

    return data.map(toShareRecipient);
}

export async function getLORAProfilePicUrl(
    loraId: string
): Promise<string | null> {
    const { data, error } = await supabase
        .from(LORAS_TABLE_NAME)
        .select(LORAS_TABLE_PROFILE_PIC_COL)
        .eq(LORAS_TABLE_ID_COL, loraId)
        .single();

    if (error || !data?.profile_pic_url) return null;

    return data.profile_pic_url;
}

export async function getLORAProfilesByCreator(
    creatorID: string
): Promise<any | null> {
    const { data, error } = await supabase
        .from(LORAS_TABLE_NAME)
        .select('*')
        .eq(LORAS_TABLE_CREATOR_COL, creatorID)

    if (error || !data) {
        console.error('Error fetching LORA(s): ', error);
        return null;
    }

    return data;
}

export async function getLORAProfileByID(
    loraID: string
): Promise<any | null> {
    const { data, error } = await supabase
        .from(LORAS_TABLE_NAME)
        .select('*')
        .eq(LORAS_TABLE_ID_COL, loraID)
        .single();

    if (error || !data) {
        console.error('Error fetching LORA: ', error);
        return null;
    }

    return data;
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
    file: File,
    oldFilePath?: string
): Promise<boolean> {
    // 1. Delete old profile pic if it exists
    if (oldFilePath) {
        const { error: deleteError } = await supabase.storage
            .from(LORA_PROFILE_PIC_BUCKET_NAME)
            .remove([oldFilePath]);

        if (deleteError) {
            console.error('Error deleting old profile pic:', deleteError);
            return false;
        }
    }

    // 2. Upload new profile pic
    const { error } = await supabase.storage
        .from(LORA_PROFILE_PIC_BUCKET_NAME)
        .upload(filePath, file, {
            cacheControl: '3600',
            upsert: true,
        });

    return !error;
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
                audio_files: [],
                training_status: 'untrained'
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

export async function deleteLORA(lora: Lora): Promise<boolean> {
    // Delete profile pic from storage if exists
    if (lora.profile_pic_url) {
        await supabase.storage
            .from(LORA_PROFILE_PIC_BUCKET_NAME)
            .remove([lora.profile_pic_url]);
    }

    // Delete LoRA from DB
    const { error } = await supabase
        .from(LORAS_TABLE_NAME)
        .delete()
        .eq(LORAS_TABLE_ID_COL, lora.id);

    return !error;
}

export async function updateLORAAudioFiles(
    updatedRecordings: Recording[],
    voiceData: VoiceData | null,
): Promise<boolean> {
    const { error } = await supabase
        .from(LORAS_TABLE_NAME)
        .update({ audio_files: updatedRecordings })
        .eq(LORAS_TABLE_ID_COL, voiceData?.id);

    return !error;
}

export async function updateLORATrainingStatus(
    loraID: string,
    status: string
): Promise<boolean> {
    const { error } = await supabase
        .from(LORAS_TABLE_NAME)
        .update({ training_status: status })
        .eq(LORAS_TABLE_ID_COL, loraID);

    return !error;
}

