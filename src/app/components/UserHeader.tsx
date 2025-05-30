import React from 'react';

type UserHeaderProps = {
  role_of_user: string;
  username: string;
  profilePicUrl: string | null;
  onBackClick: () => void;
};

export default function UserHeader({
  role_of_user,
  username,
  profilePicUrl,
  onBackClick,
}: UserHeaderProps) {
  return (
    <div className="user-top-profile">
      {profilePicUrl != null ? (
        <img
          src={profilePicUrl}
          alt="Profile"
          className="user-pic top-center"
        />
      ) : (
        <div className="user-pic placeholder top-center" />
      )}
      <h2 className="welcome-text">
        Welcome {role_of_user} {username}
      </h2>

      {/* Back Button */}
      <button className="back-btn" onClick={onBackClick}>
        ← Back to role selection
      </button>
    </div>
  );
}