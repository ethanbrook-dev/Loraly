'use client'

import React, { useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
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
      const { error } = await supabase.auth.signInWithPassword({ email, password })
      if (error) {
        setErrorMsg(error.message)
      } else {
        setSuccessMsg('Login successful! Redirecting...')
        setTimeout(() => router.push('/RoleSelect'), 1500)
      }
    } else {
      const { data: emailExists } = await supabase
        .from('profiles')
        .select('email')
        .eq('email', email)
        .single()

      if (emailExists) {
        setErrorMsg('Email is already in use.')
      } else {
        const { data: existingUsers } = await supabase
          .from('profiles')
          .select('username')
          .eq('username', username)
          .single()

        if (existingUsers) {
          setErrorMsg('Username already taken')
        } else {
          const { error: signUpError } = await supabase.auth.signUp({
            email,
            password,
            options: {
              data: { username },
              emailRedirectTo: `${process.env.NEXT_PUBLIC_FRONTEND_URL}/confirmEmailForSignup`
            },
          })
          if (signUpError) {
            setErrorMsg('Something went wrong. Please try again.')
          } else {
            setSuccessMsg('Account created! Please check your email to confirm.')
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
    <div className="loraly-container">
      <div className="loraly-wrapper">
        {/* Logo + Title */}
        <div className="loraly-logo">
          <div className="logo-icon">
            <div style={{ width: '100%', height: '100px', position: 'relative' }}>
              <Image
                src="/loraly-logo.png"
                alt="Loraly Logo"
                fill
                style={{ objectFit: 'contain' }}
              />
            </div>
          </div>
          <h1 className="loraly-title">
            {isLoginView ? 'Welcome Back' : 'Join Loraly'}
          </h1>
          <p className="loraly-subtitle">
            {isLoginView
              ? 'Login to continue to your account'
              : 'Create an account to get started'}
          </p>
        </div>

        {/* Card */}
        <div className="loraly-card">
          <div className="card-body">
            <form onSubmit={handleSubmit} className="loraly-form">
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
                  <span className="loading-text">
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
                        d="M4 12a8 8 0 018-8V0C5.373 0 
                        0 5.373 0 12h4zm2 5.291A7.962 
                        7.962 0 014 12H0c0 3.042 1.135 
                        5.824 3 7.938l3-2.647z"
                      />
                    </svg>
                    Processing...
                  </span>
                ) : isLoginView ? (
                  'Login'
                ) : (
                  'Create Account'
                )}
              </button>
            </form>

            {/* Footer toggle */}
            <div className="form-footer">
              {isLoginView ? (
                <>
                  <span>Don&apos;t have an account?</span>
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
                  <span>Already registered?</span>
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
