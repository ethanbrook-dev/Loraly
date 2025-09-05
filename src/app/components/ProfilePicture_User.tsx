'use client'

// React imports
import { useEffect, useRef, useState } from 'react'
import Image from 'next/image'

// Supabase helpers
import {
  getAuthenticatedUser,
  getUSERProfile,
  generateUSERProfilePicSignedUrl,
  uploadToUSERProfilePics
} from './db_funcs/db_funcs'

const default_image_url = '/default-user-profile-pic.png'

export default function ProfilePicture_user() {
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [currentProfilePath, setCurrentProfilePath] = useState<string | null>(null)
  const [errorMsg, setErrorMsg] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement | null>(null)
  const [userId, setUserId] = useState<string | null>(null)

  useEffect(() => {
    const fetchProfilePic = async () => {
      const user = await getAuthenticatedUser()
      if (!user) return

      setUserId(user.id)

      const userData = await getUSERProfile(user.id)
      const userProfilePicUrl = userData?.profile_pic_url

      if (!userProfilePicUrl) {
        // No profile pic uploaded → fall back to local default
        setImageUrl(default_image_url)
        return
      }

      setCurrentProfilePath(userProfilePicUrl)

      const signedUrl = await generateUSERProfilePicSignedUrl(userProfilePicUrl, 60)
      if (!signedUrl) {
        // If signed URL fails, fallback too
        setImageUrl(default_image_url)
        return
      }

      setImageUrl(signedUrl)
    }

    fetchProfilePic()
  }, [])

  const handleUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    setErrorMsg(null)
    const file = event.target.files?.[0]
    if (!file || !userId) return

    if (file.size > 1048576) {
      setErrorMsg('File size exceeds 1MB. Please upload a smaller image.')
      return
    }

    const newPath = `${userId}/${Date.now()}-${file.name}`

    const success = await uploadToUSERProfilePics(userId, newPath, file, currentProfilePath || undefined)
    if (!success) {
      setErrorMsg('Failed to update profile picture.')
      return
    }

    const signedUrl = await generateUSERProfilePicSignedUrl(newPath, 60)
    if (!signedUrl) {
      setErrorMsg('Failed to generate profile picture URL.')
      return
    }

    setImageUrl(signedUrl)
    setCurrentProfilePath(newPath)
  }

  return (
    <>
      <div
        className="profile-pic-upload"
        onClick={() => fileInputRef.current?.click()}
        style={{ position: 'relative', cursor: 'pointer' }}
      >
        <Image
          src={imageUrl || default_image_url}
          alt="Profile"
          fill
          style={{ objectFit: 'cover' }}
          className="profile-pic-image"
        />
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
  )
}
