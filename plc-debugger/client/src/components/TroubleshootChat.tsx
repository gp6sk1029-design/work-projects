import { useState, useRef, useEffect } from 'react';
import type { ChatMessage } from '../types';

interface Props {
  messages: ChatMessage[];
  onSendMessage: (message: string, images?: string[]) => void;
  hasProject: boolean;
}

// 簡易マークダウンをHTMLに変換
function renderMarkdown(text: string): string {
  return text
    // コードブロック
    .replace(/```([\s\S]*?)```/g, '<pre class="bg-dark-bg rounded p-2 my-2 text-xs overflow-x-auto"><code>$1</code></pre>')
    // インラインコード
    .replace(/`([^`]+)`/g, '<code class="bg-dark-bg px-1 rounded text-xs">$1</code>')
    // 見出し
    .replace(/^### (.+)$/gm, '<h4 class="font-bold text-white mt-3 mb-1 text-sm">$1</h4>')
    .replace(/^## (.+)$/gm, '<h3 class="font-bold text-white mt-3 mb-1">$1</h3>')
    // 太字
    .replace(/\*\*(.+?)\*\*/g, '<strong class="text-white">$1</strong>')
    // リスト項目（ネスト対応）
    .replace(/^(\s{2,})[*-] (.+)$/gm, '<div class="ml-4 pl-2 border-l border-dark-border my-0.5 text-xs">$2</div>')
    .replace(/^[*-] (.+)$/gm, '<div class="flex gap-1.5 my-0.5"><span class="text-plc mt-0.5">•</span><span>$1</span></div>')
    // 番号付きリスト
    .replace(/^(\d+)\. (.+)$/gm, '<div class="flex gap-1.5 my-0.5"><span class="text-plc font-bold">$1.</span><span>$2</span></div>')
    // 水平線
    .replace(/^---$/gm, '<hr class="border-dark-border my-2" />')
    // 改行
    .replace(/\n/g, '<br />');
}

export default function TroubleshootChat({ messages, onSendMessage, hasProject }: Props) {
  const [input, setInput] = useState('');
  const [attachedImages, setAttachedImages] = useState<string[]>([]);
  const bottomRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = () => {
    if (!input.trim() && attachedImages.length === 0) return;
    onSendMessage(input, attachedImages.length > 0 ? attachedImages : undefined);
    setInput('');
    setAttachedImages([]);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleImageAttach = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (!files) return;
    Array.from(files).forEach((file) => {
      const reader = new FileReader();
      reader.onload = () => {
        setAttachedImages((prev) => [...prev, reader.result as string]);
      };
      reader.readAsDataURL(file);
    });
    e.target.value = '';
  };

  return (
    <aside className="w-96 flex-shrink-0 bg-dark-surface flex flex-col">
      {/* ヘッダー */}
      <div className="p-4 border-b border-dark-border">
        <h2 className="text-sm font-semibold text-white">トラブルシュート</h2>
        <p className="text-xs text-gray-400 mt-1">不具合の現象を入力してください</p>
      </div>

      {/* メッセージ一覧 */}
      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 text-xs py-8">
            {hasProject
              ? '不具合の現象を入力すると、アップロード済みデータをもとに原因を分析します。画面キャプチャも貼付できます。'
              : 'まずファイルをアップロードしてください'}
          </div>
        )}
        {messages.map((msg) => (
          <div key={msg.id}>
            {/* ロールラベル */}
            <div className="flex items-center gap-1.5 mb-1">
              <span className={`w-5 h-5 rounded-full flex items-center justify-center text-[10px] font-bold ${
                msg.role === 'user' ? 'bg-plc text-white' : 'bg-green-600 text-white'
              }`}>
                {msg.role === 'user' ? 'Q' : 'A'}
              </span>
              <span className="text-[10px] text-gray-500">
                {msg.role === 'user' ? 'あなた' : 'AI'}
                {' · '}
                {new Date(msg.timestamp).toLocaleTimeString('ja-JP')}
              </span>
            </div>

            {/* メッセージ本体 */}
            <div
              className={`rounded-lg p-3 text-sm leading-relaxed ${
                msg.role === 'user'
                  ? 'bg-plc/15 text-gray-100 ml-6'
                  : 'bg-dark-bg text-gray-200 ml-6 border border-dark-border'
              }`}
            >
              {msg.images && msg.images.length > 0 && (
                <div className="flex gap-2 mb-2">
                  {msg.images.map((img, i) => (
                    <img key={i} src={img} alt="添付画像" className="w-20 h-20 object-cover rounded" />
                  ))}
                </div>
              )}
              {msg.role === 'assistant' ? (
                <div
                  className="chat-markdown"
                  dangerouslySetInnerHTML={{ __html: renderMarkdown(msg.content) }}
                />
              ) : (
                <p className="whitespace-pre-wrap">{msg.content}</p>
              )}
            </div>
          </div>
        ))}
        <div ref={bottomRef} />
      </div>

      {/* 添付画像プレビュー */}
      {attachedImages.length > 0 && (
        <div className="px-4 py-2 flex gap-2 border-t border-dark-border">
          {attachedImages.map((img, i) => (
            <div key={i} className="relative">
              <img src={img} alt="" className="w-12 h-12 object-cover rounded" />
              <button
                onClick={() => setAttachedImages((prev) => prev.filter((_, j) => j !== i))}
                className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full text-[10px] text-white leading-none flex items-center justify-center"
              >
                x
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 入力エリア */}
      <div className="p-3 border-t border-dark-border">
        <div className="flex gap-2">
          <input type="file" ref={fileInputRef} onChange={handleImageAttach} accept="image/*" multiple className="hidden" />
          <button
            onClick={() => fileInputRef.current?.click()}
            className="flex-shrink-0 w-9 h-9 bg-dark-hover hover:bg-dark-border rounded flex items-center justify-center text-gray-400 transition"
            title="画像を添付"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
            </svg>
          </button>
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="現象を入力..."
            rows={2}
            className="flex-1 bg-dark-bg border border-dark-border rounded px-3 py-2 text-sm text-white placeholder-gray-500 resize-none focus:outline-none focus:border-plc"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() && attachedImages.length === 0}
            className="flex-shrink-0 w-9 h-9 bg-plc hover:bg-plc/80 disabled:opacity-30 rounded flex items-center justify-center text-white transition self-end"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  );
}
