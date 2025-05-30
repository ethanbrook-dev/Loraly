'use client';

import { useRouter } from 'next/navigation';
import UserHeader from '@/app/components/UserHeader';
import '../../../../styles/ExplorerViewStyles.css'

export default function ExplorerDashboard() {
  const router = useRouter();

  return (
    <UserHeader
      role_of_user={'Explorer'}
      username={'placeholder' /*username*/}
      profilePicUrl={'placeholder' /*profilePicUrl*/}
      onBackClick={() => router.push('../../../RoleSelect')}
    />
  );
}