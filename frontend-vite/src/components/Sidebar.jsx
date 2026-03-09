import './Sidebar.css';

const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'chat', label: 'AI Assistant', icon: '💬' },
];

export default function Sidebar({ activeTab, setActiveTab, onNewChat }) {
    return (
        <aside className="sidebar">
            {/* Logo */}
            <div className="sidebar__logo">
                <div className="sidebar__logo-icon">
                    <svg viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round">
                        <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5" />
                    </svg>
                </div>
                <div className="sidebar__logo-text">
                    <h1>AIOps</h1>
                    <p>Reliability Agent</p>
                </div>
            </div>

            {/* New Chat */}
            <button className="sidebar__new-chat" onClick={onNewChat} title="Chat Baru">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                    <line x1="12" y1="5" x2="12" y2="19" />
                    <line x1="5" y1="12" x2="19" y2="12" />
                </svg>
                <span className="sidebar__label">Chat Baru</span>
            </button>

            {/* Navigation */}
            <nav className="sidebar__nav">
                {navItems.map((item) => (
                    <button
                        key={item.id}
                        onClick={() => setActiveTab(item.id)}
                        className={`sidebar__nav-item ${activeTab === item.id ? 'sidebar__nav-item--active' : ''}`}
                        title={item.label}
                    >
                        <span className="sidebar__nav-icon">{item.icon}</span>
                        <span className="sidebar__label">{item.label}</span>
                    </button>
                ))}
            </nav>

            {/* Status Footer */}
            <div className="sidebar__footer">
                <div className="sidebar__status">
                    <span className="sidebar__status-dot" />
                    <span className="sidebar__label">System Online</span>
                </div>
            </div>
        </aside>
    );
}
