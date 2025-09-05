'use client'

import { useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  getAuthenticatedUser,
  initLORA,
  updateLORAProfilePic,
} from '../../components/db_funcs/db_funcs'
import ProfilePicture_lora from '../../components/ProfilePicture_Lora'
import '../../../../styles/CreatorViewStyles.css'

export default function CreateVoice() {
  const [name, setName] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  const [loraId, setLoraId] = useState<string | null>(null)
  const router = useRouter()
  const creator_dashboard_navigation = '../../CreatorView/Creator_dashboard'

  const handleCreateLora = async () => {
    setErrorMsg('')
    if (!name.trim()) {
      setErrorMsg('Voice name is required.')
      return
    }

    const user = await getAuthenticatedUser()
    if (!user) return

    const initID = await initLORA(user.id, name.trim())
    if (!initID) {
      setErrorMsg('Error creating voice. Try again.')
      return
    }

    setLoraId(initID)
  }

  const handleSaveProfilePic = async () => {
    if (!loraId) return
    const success = await updateLORAProfilePic(loraId, imageUrl)
    if (!success) {
      setErrorMsg('Failed to save profile picture.')
    } else {
      router.push(creator_dashboard_navigation)
    }
  }

  return (
    <div className="creator-voice-section">
      <div className="create-voice-container">
        {/* Page Title */}
        <h2 className="create-voice-title">Create a New Voice</h2>
        <p className="create-voice-subtitle">
          Set up a display name and profile picture for your voice identity.
        </p>

        {/* Phase 1: Voice Name */}
        {!loraId && (
          <div className="voice-step">
            <label htmlFor="voice-name" className="voice-label">
              Display Name
            </label>
            <input
              id="voice-name"
              type="text"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. MyStageVoice"
              className="voice-name-input"
            />
            <p className="voice-name-note">
              ⚠️ This voice cannot be renamed once created.
            </p>

            {errorMsg && <p className="voice-error-message">{errorMsg}</p>}

            <button onClick={handleCreateLora} className="voice-save-button">
              Create Voice
            </button>
          </div>
        )}

        {/* Phase 2: Profile Picture Upload */}
        {loraId && (
          <div className="voice-step">
            <p className="voice-name-note">
              Upload a profile picture to personalize this voice.
            </p>

            <ProfilePicture_lora
              loraId={loraId}
              currentProfilePicPath={imageUrl}
              onUploadSuccess={(filePath) => setImageUrl(filePath)}
            />

            {errorMsg && <p className="voice-error-message">{errorMsg}</p>}

            <button onClick={handleSaveProfilePic} className="voice-save-button">
              Save & Continue
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
