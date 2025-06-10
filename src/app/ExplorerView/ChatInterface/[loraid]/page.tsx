'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { getLORAProfileByID } from '@/app/components/db_funcs/db_funcs';
import '../../../../../styles/ChatInterfaceStyles.css';

export default function ChatInterfacePage() {
    const { loraid } = useParams();
    const [loraName, setLoraName] = useState<string>('Loading...');
    const [input, setInput] = useState('');
    const [chatHistory, setChatHistory] = useState<{ sender: string; message: string }[]>([]);
    const [isLoading, setIsLoading] = useState(false);

    useEffect(() => {
        async function fetchLoraName() {
            const loraData = await getLORAProfileByID(loraid as string);
            if (loraData) setLoraName(loraData.name);
        }

        fetchLoraName();
    }, [loraid]);

    const handleSend = async () => {
        if (!input.trim()) return;
        setChatHistory(prev => [...prev, { sender: 'You', message: input }]);
        setIsLoading(true);

        const response = await fetch(`${process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                loraid,
                prompt: input,
            }),
        });

        const data = await response.json();

        if (response.ok && data?.response) {
            setChatHistory(prev => [...prev, { sender: loraName, message: data.response }]);
        } else {
            setChatHistory(prev => [...prev, { sender: loraName, message: '[Error getting response]' }]);
        }


        setInput('');
        setIsLoading(false);
    };

    return (
        <div className="chat-interface-wrapper">
            <div className="chat-header">
                <h2 className="lora-name-title">{loraName}</h2>
            </div>

            <div className="chat-messages">
                {chatHistory.map((msg, i) => (
                    <div key={i} className={`chat-message ${msg.sender === 'You' ? 'user' : 'bot'}`}>
                        <strong>{msg.sender}:</strong> {msg.message}
                    </div>
                ))}
            </div>

            <div className="chat-input-container">
                <input
                    type="text"
                    value={input}
                    placeholder="Type your message..."
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                />
                <button onClick={handleSend} disabled={isLoading}>
                    {isLoading ? '...' : 'Send'}
                </button>
            </div>
        </div>
    );
}
