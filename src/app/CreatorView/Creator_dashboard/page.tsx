'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import {
  getAuthenticatedUser,
  getUSERProfile,
  generateUSERProfilePicSignedUrl,
  getLORAProfilesByCreator,
  deleteLORA,
  updateLORAProfilePic,
} from '../../components/db_funcs/db_funcs'

import ProfilePicture_lora from '../../components/ProfilePicture_Lora'
import UserHeader from '../../components/UserHeader'
import ShareLoraPage from '../ShareLora/ShareLora'
import UploadWhatsappChat from '../uploadWhatsappChat/uploadWhatsappChat'

import { LoraStatus } from '@/app/constants/loraStatus'

import '../../../../styles/CreatorViewStyles.css'
import '../../../../styles/LoraCardStyles.css'
import '../../../../styles/SharingLoraStyles.css'

type Lora = {
  id: string
  creator_id: string
  name: string
  profile_pic_url: string | null
  training_status: string
}

type SharedLora = {
  id: string
  name: string
  shared_pic_url: string
}

type UserProfile = {
  id: string
  username: string
  email: string | null
  profile_pic_url: string | null
  loras_created: string[]
  loras_shared_w_me: SharedLora[]
}

export default function CreatorDashboard() {
  const router = useRouter()

  const [userData, setUserData] = useState<UserProfile | null>(null)
  const [userProfilePicUrl, setUserProfilePicUrl] = useState<string | null>(null)
  const [loras, setLoras] = useState<Lora[]>([])
  const [userId, setUserId] = useState<string | null>(null)

  const [loadingLoraIDs, setLoadingLoraIDs] = useState<Record<string, boolean>>({})
  const [uploadingLoraId, setUploadingLoraId] = useState<string | null>(null)

  const [sharingLoraId, setSharingLoraId] = useState<string | null>(null)
  const [sharingLoraName, setSharingLoraName] = useState<string | null>(null)

  // Fetch user profile
  useEffect(() => {
    async function fetchUserProfile() {
      const user = await getAuthenticatedUser()
      if (!user) return
      setUserId(user.id)

      const userData = await getUSERProfile(user.id)
      if (!userData) {
        setUserData(null)
        return
      }

      setUserData(userData)

      if (userData.profile_pic_url) {
        const signedUrl = await generateUSERProfilePicSignedUrl(
          userData.profile_pic_url,
          60
        )
        if (!signedUrl) return
        setUserProfilePicUrl(signedUrl)
      }
    }

    fetchUserProfile()
  }, [])

  // Fetch LoRAs created by the user
  useEffect(() => {
    async function fetchLoras() {
      if (!userId) return
      const loraData = await getLORAProfilesByCreator(userId)
      if (loraData) setLoras(loraData)
    }

    fetchLoras()
  }, [userId])

  useEffect(() => {
    setLoadingLoraIDs({})
  }, [])

  // Delete handler
  const handleDeleteLora = async (lora: Lora) => {
    if (!confirm(`Delete voice "${lora.name}"? This cannot be undone.`)) return

    const loraWasDeleted = await deleteLORA(lora)

    if (loraWasDeleted) {
      setLoras((prev) => prev.filter((l) => l.id !== lora.id))
    } else {
      console.error('Error deleting LoRA')
    }
  }

  if (uploadingLoraId) {
    return <UploadWhatsappChat loraId={uploadingLoraId} />
  }

  if (sharingLoraId && sharingLoraName) {
    return (
      <ShareLoraPage
        loraid={sharingLoraId}
        loraName={sharingLoraName}
        onShareComplete={() => {
          setSharingLoraId(null)
          setSharingLoraName(null)
          router.push('../../../CreatorView/Creator_dashboard')
        }}
      />
    )
  }

  return (
    <main className="creator-dashboard">
      {/* Header */}
      <UserHeader
        role_of_user="Creator"
        username={userData?.username || 'Loading...'}
        profilePicUrl={userProfilePicUrl}
        onBackClick={() => router.push('../../../RoleSelect')}
      />

      {/* Voices Section */}
      <section className="creator-voice-section">
        <h2 className="section-title">Your Voices</h2>

        {loras.length === 0 ? (
          <p className="empty-state">✨ You haven’t created any voices yet.</p>
        ) : (
          <div className="loras-scroll-container">
            {loras.map((lora) => {
              const isTraining = lora.training_status === LoraStatus.TRAINING
              const isTrainingCompleted =
                lora.training_status === LoraStatus.TRAINING_COMPLETED

              return (
                <div key={lora.id} className="lora-card">
                  {/* Info */}
                  <div className="lora-info">
                    <ProfilePicture_lora
                      loraId={lora.id}
                      currentProfilePicPath={lora.profile_pic_url ?? null}
                      onUploadSuccess={async (newUrl) => {
                        if (isTraining || isTrainingCompleted) return
                        const wasUpdated = await updateLORAProfilePic(
                          lora.id,
                          newUrl
                        )
                        if (!wasUpdated) {
                          setLoras((prev) =>
                            prev.map((item) =>
                              item.id === lora.id
                                ? { ...item, profile_pic_url: newUrl }
                                : item
                            )
                          )
                        }
                      }}
                    />
                    <div className="lora-name">{lora.name}</div>
                  </div>

                  {/* Actions */}
                  <div className="lora-buttons">
                    {isTraining && (
                      <p className="generating-voice-text">⏳ Generating...</p>
                    )}

                    {isTrainingCompleted && (
                      <button
                        className="share-button"
                        onClick={() => {
                          setSharingLoraId(lora.id)
                          setSharingLoraName(lora.name)
                        }}
                      >
                        Share Voice
                      </button>
                    )}

                    {!isTraining && !isTrainingCompleted && (
                      <>
                        {loadingLoraIDs[lora.id] ? (
                          <div className="spinner" />
                        ) : (
                          <button
                            className="upload-chat-file-button"
                            onClick={() => setUploadingLoraId(lora.id)}
                          >
                            Upload WhatsApp Chat
                          </button>
                        )}
                      </>
                    )}
                  </div>

                  {/* Delete */}
                  {lora.training_status !== LoraStatus.TRAINING_COMPLETED && (
                    <button
                      className="delete-button"
                      onClick={() => handleDeleteLora(lora)}
                      title="Delete Voice"
                      disabled={
                        loadingLoraIDs[lora.id] ||
                        lora.training_status === LoraStatus.TRAINING
                      }
                    >
                      <div
                        style={{
                          width: '40px',
                          height: '40px',
                          position: 'relative',
                        }}
                      >
                        <Image
                          src="/delete-icon.svg"
                          alt="Delete"
                          fill
                          style={{ objectFit: 'contain' }}
                        />
                      </div>
                    </button>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </section>

      {/* Footer */}
      <footer className="creator-footer">
        <button
          className="create-voice-button"
          onClick={() => router.push('../../../CreatorView/CreateVoice')}
        >
          + Create New Voice
        </button>
      </footer>
    </main>
  )
}
