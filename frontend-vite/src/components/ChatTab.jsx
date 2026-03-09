import { useRef, useEffect } from 'react';
import ChatMessage, { TypingIndicator } from './ChatMessage';
import QuickActions from './QuickActions';
import './ChatTab.css';

export default function ChatTab({
    messages,
    isLoading,
    inputText,
    setInputText,
    sendMessage,
    inputRef,
}) {
    const messagesEndRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages, isLoading]);

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    };

    return (
        <div className="chat-tab">
            {/* Messages */}
            <div className="chat-tab__messages">
                <div className="chat-tab__messages-inner">
                    {messages.length === 0 ? (
                        <div className="chat-tab__empty">
                            <div className="chat-tab__empty-logo">🤖</div>
                            <h2 className="chat-tab__empty-title">AIOps Intelligence</h2>
                            <p className="chat-tab__empty-desc">
                                Asisten ahli infrastruktur Anda. Saya dapat menarik dari log datawarehouse,
                                membaca SOP teknis, dan memberikan analisis root-cause.
                            </p>
                            <QuickActions onSelect={sendMessage} />
                        </div>
                    ) : (
                        <>
                            {messages.map((msg, i) => (
                                <ChatMessage key={i} message={msg} />
                            ))}
                            {isLoading && <TypingIndicator />}
                            <div ref={messagesEndRef} style={{ height: 16 }} />
                        </>
                    )}
                </div>
            </div>

            {/* Input */}
            <div className="chat-tab__input-area">
                <div className="chat-tab__input-wrapper">
                    <div className="chat-tab__input-box">
                        <textarea
                            ref={inputRef}
                            value={inputText}
                            onChange={(e) => setInputText(e.target.value)}
                            onKeyDown={handleKeyDown}
                            placeholder="Ketik pertanyaan terkait infrastruktur… (Shift+Enter untuk baris baru)"
                            rows={1}
                            className="chat-tab__textarea"
                            disabled={isLoading}
                        />
                        <button
                            onClick={() => sendMessage()}
                            disabled={!inputText.trim() || isLoading}
                            className={`chat-tab__send-btn ${inputText.trim() && !isLoading
                                    ? 'chat-tab__send-btn--active'
                                    : 'chat-tab__send-btn--disabled'
                                }`}
                        >
                            <svg
                                width="16"
                                height="16"
                                viewBox="0 0 24 24"
                                fill="none"
                                stroke={inputText.trim() && !isLoading ? 'white' : '#5a5a5a'}
                                strokeWidth="2.5"
                                strokeLinecap="round"
                                strokeLinejoin="round"
                            >
                                <line x1="22" y1="2" x2="11" y2="13" />
                                <polygon points="22 2 15 22 11 13 2 9 22 2" />
                            </svg>
                        </button>
                    </div>
                    <p className="chat-tab__disclaimer">
                        AIOps Assistant dapat memberikan hasil yang kurang tepat. Selalu verifikasi dengan data asli dan SOP sebelum mengambil keputusan kritis.
                    </p>
                </div>
            </div>
        </div>
    );
}
