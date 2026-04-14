import { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '../types';

interface Props {
  recordingId: string;
  messages: ChatMessage[];
  onMessagesUpdate: (messages: ChatMessage[]) => void;
}

const quickQuestions = [
  'この会議の結論は？',
  '重要な数字やデータは？',
  '次のアクションは？',
  '未解決の課題は？',
];

export default function ChatPanel({ recordingId, messages, onMessagesUpdate }: Props) {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const sendMessage = async (text: string) => {
    if (!text.trim() || loading) return;

    const userMsg: ChatMessage = {
      id: `temp-${Date.now()}`,
      recording_id: recordingId,
      role: 'user',
      content: text.trim(),
      created_at: new Date().toISOString(),
    };

    const updatedMessages = [...messages, userMsg];
    onMessagesUpdate(updatedMessages);
    setInput('');
    setLoading(true);

    try {
      const history = messages.map(m => ({ role: m.role, content: m.content }));

      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ recordingId, message: text.trim(), history }),
      });

      if (res.ok) {
        const reply = await res.json();
        onMessagesUpdate([...updatedMessages, reply]);
      }
    } catch (err) {
      console.error('チャットエラー:', err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      {/* ヘッダー */}
      <div className="px-4 py-3 border-b border-dark-border">
        <h3 className="text-sm font-bold">AI Q&A</h3>
        <p className="text-xs text-gray-500">録音内容について質問できます</p>
      </div>

      {/* メッセージ一覧 */}
      <div className="flex-1 overflow-auto p-4 space-y-3">
        {messages.length === 0 && (
          <div className="space-y-2">
            <p className="text-xs text-gray-500 mb-3">クイック質問:</p>
            {quickQuestions.map((q) => (
              <button
                key={q}
                onClick={() => sendMessage(q)}
                className="w-full text-left px-3 py-2 text-xs bg-dark-surface border border-dark-border rounded-lg hover:border-accent-blue/50 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        )}

        {messages.map((msg) => (
          <div
            key={msg.id}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[85%] px-3 py-2 rounded-lg text-sm ${
                msg.role === 'user'
                  ? 'bg-accent-blue text-white'
                  : 'bg-dark-surface border border-dark-border'
              }`}
            >
              <p className="whitespace-pre-wrap">{msg.content}</p>
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-dark-surface border border-dark-border px-3 py-2 rounded-lg">
              <div className="flex gap-1">
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* 入力 */}
      <div className="p-3 border-t border-dark-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && !e.shiftKey && sendMessage(input)}
            placeholder="質問を入力..."
            className="flex-1 px-3 py-2 bg-dark-surface border border-dark-border rounded-lg text-sm focus:outline-none focus:border-accent-blue"
            disabled={loading}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={!input.trim() || loading}
            className="btn-primary px-3 disabled:opacity-50"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
