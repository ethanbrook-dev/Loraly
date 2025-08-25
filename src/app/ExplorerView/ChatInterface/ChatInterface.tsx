// The chat interface and UI

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import '../../../../styles/ChatInterfaceStyles.css';

type ChatInterfacePageProps = {
    loraid: string;
    loraName: string;
};

export default function ChatInterfacePage({ loraid, loraName }: ChatInterfacePageProps) {
    const router = useRouter();

    const [input, setInput] = useState('');
    const [chatHistory, setChatHistory] = useState<{ sender: string; message: string }[]>([]);
    const [isLoading, setIsLoading] = useState(false);

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

        console.log("Response status:", response.status); // e.g. 500
        const data = await response.json();
        console.log("Response data:", data);

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
                <button
                    className="back-button"
                    onClick={() => router.back()}
                >
                    ← Back to Dashboard
                </button>
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
