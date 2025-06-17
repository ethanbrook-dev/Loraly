// Login and Signup:

'use client'

// React and Next.js imports
import React, { useState } from 'react'
import { useRouter } from 'next/navigation'

// Supabase client import
import { supabase } from '../../supabase/client'

export default function LoginANDSignup() {
  const router = useRouter()

  const [isLoginView, setIsLoginView] = useState(true)
  const [email, setEmail] = useState('')
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [errorMsg, setErrorMsg] = useState('')
  const [successMsg, setSuccessMsg] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setErrorMsg('')
    setSuccessMsg('')
    setIsLoading(true)

    if (isLoginView) {
      const { error } = await supabase.auth.signInWithPassword({
        email,
        password,
      })
      if (error) {
        setErrorMsg(error.message)
      } else {
        setSuccessMsg('Login successful! Redirecting...')
        setTimeout(() => {
          router.push('/RoleSelect')
        }, 1500)
      }
    } else {

      const { data: emailExists, error: e } = await supabase
        .from('profiles')
        .select('email')
        .eq('email', email)
        .single()

      if (emailExists) {
        setErrorMsg('Email is already in use.')
      } else {
        const { data: existingUsers, error: fetchError } = await supabase
          .from('profiles')
          .select('username')
          .eq('username', username)
          .single()

        if (existingUsers) {
          setErrorMsg('Username already taken')
        } else {
          const { data, error: signUpError } = await supabase.auth.signUp({
            email,
            password,
            options: {
              data: { username },
            },
          })
          if (signUpError) {
            setErrorMsg("Missing email");
          } else {
            setSuccessMsg(
              'Account created successfully! Please check your email to confirm. You can close this page.'
            )
            setIsLoginView(true)
            setEmail('')
            setUsername('')
            setPassword('')
          }
        }
      }
    }

    setIsLoading(false)
  }

  return (
    <div className="aftervoice-container">
      <div className="aftervoice-wrapper">
        <div className="aftervoice-logo">
          <div className="logo-icon">
            <img
              src="/AfterVoiceAI-logo.png"
              alt="AfterVoiceAI Logo"
              style={{ width: '100%', height: '100%', objectFit: 'contain' }}
            />
          </div>
          <h1 className="aftervoice-title">AfterVoiceAI</h1>
          <div className="aftervoice-subtitle">
            {isLoginView ? 'Login to your account' : 'Create new account'}
          </div>
        </div>

        <div className="aftervoice-card">
          <div className="card-body">
            <form onSubmit={handleSubmit} className="aftervoice-form">
              {!isLoginView && (
                <div className="form-group">
                  <label htmlFor="username" className="form-label">
                    Username
                  </label>
                  <input
                    id="username"
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    className="form-input"
                    required
                  />
                </div>
              )}

              <div className="form-group">
                <label htmlFor="email" className="form-label">
                  Email
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="form-input"
                  required
                />
              </div>

              <div className="form-group">
                <label htmlFor="password" className="form-label">
                  Password
                </label>
                <input
                  id="password"
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="form-input"
                  required
                  minLength={6}
                />
              </div>

              {errorMsg && <p className="error-message">{errorMsg}</p>}
              {successMsg && <p className="success-message">{successMsg}</p>}

              <button
                type="submit"
                className="submit-button"
                disabled={isLoading}
              >
                {isLoading ? (
                  <span
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <svg
                      className="loading-spinner"
                      xmlns="http://www.w3.org/2000/svg"
                      fill="none"
                      viewBox="0 0 24 24"
                      width="20"
                      height="20"
                    >
                      <circle
                        className="opacity-25"
                        cx="12"
                        cy="12"
                        r="10"
                        stroke="currentColor"
                        strokeWidth="4"
                      />
                      <path
                        className="opacity-75"
                        fill="currentColor"
                        d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Processing...
                  </span>
                ) : isLoginView ? (
                  'Login'
                ) : (
                  'Create My Account'
                )}
              </button>
            </form>

            <div className="form-footer">
              {isLoginView ? (
                <>
                  Don't have an account?
                  <button
                    onClick={() => {
                      setErrorMsg('')
                      setSuccessMsg('')
                      setIsLoginView(false)
                      setPassword('')
                      setEmail('')
                      setUsername('')
                    }}
                    className="toggle-link"
                  >
                    Sign up
                  </button>
                </>
              ) : (
                <>
                  Already have an account?
                  <button
                    onClick={() => {
                      setErrorMsg('')
                      setSuccessMsg('')
                      setIsLoginView(true)
                      setPassword('')
                      setEmail('')
                      setUsername('')
                    }}
                    className="toggle-link"
                  >
                    Login
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}