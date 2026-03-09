import './QuickActions.css';

const actions = [
    { label: 'Status Infrastruktur', icon: '📊', query: 'Apa status semua service saat ini?' },
    { label: 'Cek Anomali', icon: '🔍', query: 'Apakah ada anomali di infrastruktur dalam 1 jam terakhir?' },
    { label: 'SOP CPU Tinggi', icon: '📋', query: 'Bagaimana cara menangani CPU usage yang tinggi pada container?' },
    { label: 'Nginx Troubleshooting', icon: '🌐', query: 'Bagaimana cara troubleshoot Nginx yang tidak merespons?' },
];

export default function QuickActions({ onSelect }) {
    return (
        <div className="quick-actions">
            {actions.map((action, i) => (
                <button
                    key={i}
                    className="quick-actions__btn animate-fade-in-up"
                    style={{ animationDelay: `${i * 0.06}s` }}
                    onClick={() => onSelect(action.query)}
                >
                    <span className="quick-actions__btn-icon">{action.icon}</span>
                    <span>{action.label}</span>
                </button>
            ))}
        </div>
    );
}
