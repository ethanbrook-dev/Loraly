// The chat interface and UI

'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import '../../../../styles/ChatInterfaceStyles.css';

const MAX_CHARS = 4000; // safe approximation (adjust based on model, e.g. 2048 tokens ≈ 4000 chars)

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

        // Create updated history with the new user message
        const updatedHistory = trimHistory([...chatHistory, { sender: 'You', message: input }]);
        setChatHistory(updatedHistory);
        
        setIsLoading(true);

        const response = await fetch(`${process.env.NEXT_PUBLIC_PYTHON_BACKEND_URL}/chat`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                loraid,
                chatHistory: updatedHistory,
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

    function trimHistory(history: { sender: string; message: string }[]) {
        let totalChars = 0;
        const trimmed: { sender: string; message: string }[] = [];

        // iterate backwards (most recent first)
        for (let i = history.length - 1; i >= 0; i--) {
            const msg = history[i];
            totalChars += msg.message.length;
            if (totalChars > MAX_CHARS) break;
            trimmed.unshift(msg); // prepend so order stays intact
        }

        return trimmed;
    }

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
