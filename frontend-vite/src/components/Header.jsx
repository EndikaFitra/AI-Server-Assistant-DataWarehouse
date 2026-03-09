import { useState, useEffect } from 'react';
import './Header.css';

export default function Header({ activeTab }) {
    const [time, setTime] = useState('');

    useEffect(() => {
        const update = () => {
            setTime(new Date().toLocaleTimeString('id-ID', {
                hour: '2-digit',
                minute: '2-digit',
                second: '2-digit',
            }));
        };
        update();
        const id = setInterval(update, 1000);
        return () => clearInterval(id);
    }, []);

    const tabConfig = {
        dashboard: { icon: '📊', title: 'Infrastructure Dashboard', subtitle: 'Real-time Metrics' },
        chat: { icon: '💬', title: 'AI Reliability Chat', subtitle: 'Powered by RAG & MCP' },
    };

    const cfg = tabConfig[activeTab] || tabConfig.dashboard;

    return (
        <header className="header">
            <div className="header__left">
                <span className="header__icon">{cfg.icon}</span>
                <div className="header__title-group">
                    <h2 className="header__title">{cfg.title}</h2>
                    <span className="header__subtitle">{cfg.subtitle}</span>
                </div>
            </div>

            <div className="header__right">
                <div className="header__model-badge">
                    <span className="header__model-dot" />
                    QWEN3:4B-INSTRUCT
                </div>
                <span className="header__time">{time}</span>
            </div>
        </header>
    );
}
