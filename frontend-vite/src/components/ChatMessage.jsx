import './ChatMessage.css';

// ── Format Markdown Safely ──
function formatMarkdown(text) {
    if (!text) return '';
    let html = text
        .replace(/```(\w*)\n([\s\S]*?)```/g, '<div class="my-3"><pre><code class="language-$1">$2</code></pre></div>')
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/^### (.+)$/gm, '<h3>$1</h3>')
        .replace(/^## (.+)$/gm, '<h2>$1</h2>')
        .replace(/^# (.+)$/gm, '<h1>$1</h1>')
        .replace(
            /\|\s*([^|\n]*?)\s*\|\s*([^|\n]*?)\s*\|(?:\s*([^|\n]*?)\s*\|)?(?:\s*([^|\n]*?)\s*\|)?/gm,
            (match, p1, p2, p3, p4) => {
                if (p1.includes('---')) return '';
                const isHeader = p1.toUpperCase() === p1 && p1.length > 1 && !p1.includes(' ');
                const tag = isHeader ? 'th' : 'td';
                let row = `<tr><${tag}>${p1}</${tag}><${tag}>${p2}</${tag}>`;
                if (p3) row += `<${tag}>${p3}</${tag}>`;
                if (p4) row += `<${tag}>${p4}</${tag}>`;
                return row + '</tr>';
            }
        )
        .replace(/(<tr>.*<\/tr>\n?)+/g, '<div class="overflow-x-auto my-3"><table class="min-w-full">$&</table></div>')
        .replace(/^- (.+)$/gm, '<li>$1</li>')
        .replace(/^\d+\. (.+)$/gm, '<li>$1</li>')
        .replace(/(<li>.*<\/li>\n?)+/g, '<ul class="list-disc pl-5 my-2">$&</ul>')
        .replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>')
        .replace(/^(?!<[hlutpbd]|<\/|<code|<pre|<block|<tr|<li|<div)(.+)$/gm, '<p>$1</p>');

    return html;
}

// ── Typing Indicator ──
export function TypingIndicator() {
    return (
        <div className="typing">
            <div className="typing__avatar">🤖</div>
            <div className="typing__bubble">
                {[0, 1, 2].map((i) => (
                    <div
                        key={i}
                        className="typing__dot"
                        style={{ animation: `typingDot 1.4s ease-in-out ${i * 0.2}s infinite` }}
                    />
                ))}
            </div>
        </div>
    );
}

// ── Chat Message ──
export default function ChatMessage({ message }) {
    const isUser = message.role === 'user';
    const roleClass = isUser ? 'chat-msg--user' : 'chat-msg--ai';

    return (
        <div className={`chat-msg ${roleClass}`}>
            <div className="chat-msg__avatar">{isUser ? '👤' : '🤖'}</div>
            <div className="chat-msg__bubble">
                <div className="chat-msg__content">
                    {isUser ? (
                        <p style={{ whiteSpace: 'pre-wrap', margin: 0 }}>{message.content}</p>
                    ) : (
                        <div
                            className="markdown-content"
                            dangerouslySetInnerHTML={{ __html: formatMarkdown(message.content) }}
                        />
                    )}
                </div>
                <span className="chat-msg__time">{message.timestamp}</span>
            </div>
        </div>
    );
}
