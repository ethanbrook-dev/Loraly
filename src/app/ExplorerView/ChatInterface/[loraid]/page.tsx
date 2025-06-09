'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { 
    getLORAProfileByID
 } from '@/app/components/db_funcs/db_funcs';
import '../../../../../styles/ChatInterfaceStyles.css';

export default function ChatInterfacePage() {
  const { loraid } = useParams();
  const [loraName, setLoraName] = useState<string>('Loading...');
  
  useEffect(() => {
    async function fetchLoraName() {
      const loraData = await getLORAProfileByID(loraid as string);
      if (!loraData) {
        setLoraName('Loading...');
        return;
      }

      setLoraName(loraData.name);
    }

    fetchLoraName();
  }, [loraid]);

  return (
    <div className="chat-interface-wrapper">
      <div className="chat-header">
        <h2 className="lora-name-title">{loraName}</h2>
      </div>

      <div className="chat-placeholder-box">
        <p>🎙️ Voice chat UI coming soon.</p>
        <p>You can design this like iMessage, but optimized for sending/playing audio clips.</p>
      </div>
    </div>
  );
}