'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import '../../../../styles/ChatInterfaceStyles.css';

const MAX_CHARS = 4000;

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

        const updatedHistory = trimHistory([...chatHistory, { sender: 'You', message: input }]);
        setChatHistory(updatedHistory);
        
        setIsLoading(true);

        try {
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
        } catch {
            setChatHistory(prev => [...prev, { sender: loraName, message: '[Connection error]' }]);
        }

        setInput('');
        setIsLoading(false);
    };

    function trimHistory(history: { sender: string; message: string }[]) {
        let totalChars = 0;
        const trimmed: { sender: string; message: string }[] = [];

        for (let i = history.length - 1; i >= 0; i--) {
            const msg = history[i];
            totalChars += msg.message.length;
            if (totalChars > MAX_CHARS) break;
            trimmed.unshift(msg);
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
                        <strong>{msg.sender}:</strong>
                        <div className="message-content">{msg.message}</div>
                    </div>
                ))}
                {isLoading && (
                    <div className="chat-message bot">
                        <strong>{loraName}:</strong>
                        <div className="typing-indicator">
                            <div className="typing-dot"></div>
                            <div className="typing-dot"></div>
                            <div className="typing-dot"></div>
                        </div>
                    </div>
                )}
            </div>

            <div className="chat-input-container">
                <input
                    type="text"
                    value={input}
                    placeholder="Type your message..."
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                    disabled={isLoading}
                />
                <button onClick={handleSend} disabled={isLoading || !input.trim()}>
                    {isLoading ? '...' : 'Send'}
                </button>
            </div>
        </div>
    );
}