import { useState, useRef } from 'react';
import Sidebar from './components/Sidebar';
import Header from './components/Header';
import DashboardTab from './components/DashboardTab';
import ChatTab from './components/ChatTab';

const AI_API_URL = 'http://localhost:8001';

export default function App() {
  const [activeTab, setActiveTab] = useState('dashboard');
  const [messages, setMessages] = useState([]);
  const [inputText, setInputText] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef(null);

  const handleNewChat = async () => {
    setMessages([]);
    try {
      await fetch(`${AI_API_URL}/api/chat/reset`, { method: 'POST' });
    } catch {
      /* ignore */
    }
  };

  const sendMessage = async (text) => {
    const content = text || inputText.trim();
    if (!content || isLoading) return;

    const timestamp = new Date().toLocaleTimeString('id-ID', {
      hour: '2-digit',
      minute: '2-digit',
    });

    setMessages((prev) => [...prev, { role: 'user', content, timestamp }]);
    setInputText('');
    setIsLoading(true);

    try {
      const resp = await fetch(`${AI_API_URL}/api/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: content }),
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      const data = await resp.json();
      const aiTimestamp = new Date().toLocaleTimeString('id-ID', {
        hour: '2-digit',
        minute: '2-digit',
      });

      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: data.response, timestamp: aiTimestamp },
      ]);
    } catch (err) {
      const aiTimestamp = new Date().toLocaleTimeString('id-ID', {
        hour: '2-digit',
        minute: '2-digit',
      });
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: `❌ **Koneksi Gagal**\n\nTidak dapat terhubung ke AI Backend. Pastikan API berjalan di \`${AI_API_URL}\`.\n\n\`\`\`\n${err.message}\n\`\`\``,
          timestamp: aiTimestamp,
        },
      ]);
    } finally {
      setIsLoading(false);
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  };

  return (
    <div className="app-layout">
      <Sidebar activeTab={activeTab} setActiveTab={setActiveTab} onNewChat={handleNewChat} />

      <div className="app-main">
        <Header activeTab={activeTab} />

        <div className="app-content">
          {activeTab === 'dashboard' ? (
            <DashboardTab />
          ) : (
            <ChatTab
              messages={messages}
              isLoading={isLoading}
              inputText={inputText}
              setInputText={setInputText}
              sendMessage={sendMessage}
              inputRef={inputRef}
            />
          )}
        </div>
      </div>
    </div>
  );
}
