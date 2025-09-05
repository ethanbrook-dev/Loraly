'use client'

export default function EmailVerified() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <div className="bg-white rounded-2xl shadow-lg p-12 max-w-md text-center">
        <div className="w-24 h-24 mx-auto mb-6 relative">
        </div>
        <h1 className="text-2xl font-bold mb-4 text-gray-800">
          Email Verified!
        </h1>
        <p className="text-gray-600 mb-6">
          Your account is now active. Welcome to Loraly! <br />
          You can exit this page and return to the web app.
        </p>
      </div>
    </div>
  )
}
