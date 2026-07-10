/**
 * 設備翻訳タブ（日⇄英＋略語提案＋社内用語辞書）
 */
import { useState, useEffect } from 'react';
import type {
  TranslationDirection,
  TranslationMode,
  TranslationResult,
  GlossaryEntry,
} from '../types';

export default function TranslationTab() {
  const [text, setText] = useState('');
  const [direction, setDirection] = useState<TranslationDirection>('auto');
  const [mode, setMode] = useState<TranslationMode>('sentence');
  const [result, setResult] = useState<TranslationResult | null>(null);
  const [isTranslating, setIsTranslating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 辞書
  const [glossary, setGlossary] = useState<GlossaryEntry[]>([]);
  const [showGlossary, setShowGlossary] = useState(false);
  const [copied, setCopied] = useState<string>('');

  useEffect(() => {
    void loadGlossary();
  }, []);

  const loadGlossary = async () => {
    try {
      const res = await fetch('/api/translate/glossary');
      if (res.ok) {
        setGlossary(await res.json());
      }
    } catch (err) {
      console.error('辞書取得エラー:', err);
    }
  };

  const handleTranslate = async () => {
    if (!text.trim()) {
      setError('テキストを入力してください');
      return;
    }
    setError(null);
    setIsTranslating(true);
    setResult(null);
    try {
      const res = await fetch('/api/translate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.trim(), direction, mode }),
      });
      if (!res.ok) {
        const err = await res.json();
        setError(err.error || '翻訳エラー');
        return;
      }
      setResult(await res.json());
    } catch (err) {
      setError(`通信エラー: ${String(err)}`);
    } finally {
      setIsTranslating(false);
    }
  };

  const handleCopy = (s: string) => {
    void navigator.clipboard.writeText(s);
    setCopied(s);
    setTimeout(() => setCopied(''), 1500);
  };

  const handleSaveToGlossary = async () => {
    if (!result || !text.trim()) return;
    const isJa = result.detectedLanguage === 'ja';
    const term_ja = isJa ? text.trim() : result.translation;
    const term_en = isJa ? result.translation : text.trim();
    const abbr = result.abbreviations[0]?.abbr || '';

    const category =
      window.prompt('カテゴリを入力（電気/機械/制御/安全/その他）', 'その他') || 'その他';
    const note = window.prompt('メモ（任意）', result.contextNote || '') || '';

    try {
      const res = await fetch('/api/translate/glossary', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ term_ja, term_en, abbr, category, note }),
      });
      if (res.ok) {
        await loadGlossary();
        alert('辞書に登録しました');
      } else {
        alert('登録失敗');
      }
    } catch (err) {
      alert(`通信エラー: ${String(err)}`);
    }
  };

  const handleDeleteGlossary = async (id: number) => {
    if (!window.confirm('この用語を削除しますか？')) return;
    try {
      const res = await fetch(`/api/translate/glossary/${id}`, { method: 'DELETE' });
      if (res.ok) {
        await loadGlossary();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
      void handleTranslate();
    }
  };

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h2 className="text-2xl font-bold text-white">🌐 設備翻訳</h2>
          <p className="text-sm text-gray-400 mt-1">
            生産設備・PLC・電気制御に特化した日⇄英翻訳。略語と変数名候補も提案します。
          </p>
        </div>
        <button
          onClick={() => setShowGlossary(!showGlossary)}
          className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white text-sm rounded-lg transition"
        >
          📚 社内用語辞書 ({glossary.length})
        </button>
      </div>

      {/* オプション選択 */}
      <div className="flex flex-wrap gap-4 mb-4 p-4 bg-dark-surface rounded-lg border border-dark-border">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-300">方向:</label>
          <select
            value={direction}
            onChange={(e) => setDirection(e.target.value as TranslationDirection)}
            className="px-3 py-1.5 bg-dark-bg border border-dark-border rounded text-sm text-white"
          >
            <option value="auto">🔄 自動判定</option>
            <option value="ja-en">🇯🇵→🇺🇸 日→英</option>
            <option value="en-ja">🇺🇸→🇯🇵 英→日</option>
          </select>
        </div>
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-300">モード:</label>
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as TranslationMode)}
            className="px-3 py-1.5 bg-dark-bg border border-dark-border rounded text-sm text-white"
          >
            <option value="sentence">📝 文章・フレーズ</option>
            <option value="variable">🔤 PLC変数名候補</option>
            <option value="abbr-lookup">🔍 略語の逆引き</option>
          </select>
        </div>
      </div>

      {/* 入力エリア */}
      <div className="mb-4">
        <textarea
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="翻訳したいテキストを入力（例：「主軸モーターの非常停止入力」）  Ctrl+Enterで実行"
          className="w-full h-32 p-4 bg-dark-surface border border-dark-border rounded-lg text-white text-sm font-mono resize-y focus:border-plc focus:outline-none"
        />
        <div className="flex items-center justify-between mt-2">
          <span className="text-xs text-gray-500">{text.length} 文字 / 5000</span>
          <button
            onClick={handleTranslate}
            disabled={isTranslating || !text.trim()}
            className="px-6 py-2 bg-green-600 hover:bg-green-500 disabled:bg-green-600/30 disabled:text-gray-500 text-white font-semibold rounded-lg transition"
          >
            {isTranslating ? (
              <span className="flex items-center gap-2">
                <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                翻訳中...
              </span>
            ) : (
              '翻訳実行 (Ctrl+Enter)'
            )}
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 p-3 bg-red-900/30 border border-red-700 rounded text-red-300 text-sm">
          {error}
        </div>
      )}

      {/* 結果 */}
      {result && (
        <div className="space-y-4">
          {/* 主翻訳 */}
          <div className="p-4 bg-dark-surface border-2 border-green-600 rounded-lg">
            <div className="flex items-center justify-between mb-2">
              <h3 className="text-sm font-semibold text-green-400">
                ✅ 翻訳結果（検出言語: {result.detectedLanguage === 'ja' ? '日本語' : 'English'}）
              </h3>
              <div className="flex gap-2">
                <button
                  onClick={() => handleCopy(result.translation)}
                  className="px-3 py-1 bg-dark-bg hover:bg-dark-hover text-xs text-gray-300 rounded"
                >
                  {copied === result.translation ? '✓ コピー済' : '📋 コピー'}
                </button>
                <button
                  onClick={handleSaveToGlossary}
                  className="px-3 py-1 bg-blue-600 hover:bg-blue-500 text-xs text-white rounded"
                >
                  📚 辞書登録
                </button>
              </div>
            </div>
            <p className="text-white text-lg font-medium">{result.translation}</p>
            {result.contextNote && (
              <p className="mt-2 text-xs text-gray-400 italic">💡 {result.contextNote}</p>
            )}
          </div>

          {/* 別案 */}
          {result.alternatives.length > 0 && (
            <div className="p-4 bg-dark-surface border border-dark-border rounded-lg">
              <h3 className="text-sm font-semibold text-gray-300 mb-2">📋 別の表現候補</h3>
              <ul className="space-y-1">
                {result.alternatives.map((a, i) => (
                  <li key={i} className="flex items-center justify-between gap-2 text-sm text-gray-200">
                    <span>{a}</span>
                    <button
                      onClick={() => handleCopy(a)}
                      className="px-2 py-0.5 bg-dark-bg hover:bg-dark-hover text-xs text-gray-400 rounded"
                    >
                      {copied === a ? '✓' : '📋'}
                    </button>
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* 略語候補 */}
          {result.abbreviations.length > 0 && (
            <div className="p-4 bg-dark-surface border border-dark-border rounded-lg">
              <h3 className="text-sm font-semibold text-yellow-400 mb-2">🔤 略語候補</h3>
              <div className="grid gap-2">
                {result.abbreviations.map((a, i) => (
                  <div key={i} className="flex items-start gap-3 p-2 bg-dark-bg rounded">
                    <button
                      onClick={() => handleCopy(a.abbr)}
                      className="flex-shrink-0 px-3 py-1 bg-yellow-600 hover:bg-yellow-500 text-white font-mono font-bold text-sm rounded"
                    >
                      {copied === a.abbr ? '✓' : a.abbr}
                    </button>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white">
                        <span className="text-gray-400">→</span> {a.expansion}
                      </p>
                      <p className="text-xs text-gray-500 mt-0.5">{a.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* 変数名候補 */}
          {result.variableNames.length > 0 && (
            <div className="p-4 bg-dark-surface border border-dark-border rounded-lg">
              <h3 className="text-sm font-semibold text-purple-400 mb-2">
                🔤 PLC変数名候補（3スタイル）
              </h3>
              <div className="grid gap-2">
                {result.variableNames.map((v, i) => (
                  <div key={i} className="flex items-start gap-3 p-2 bg-dark-bg rounded">
                    <button
                      onClick={() => handleCopy(v.name)}
                      className="flex-shrink-0 px-3 py-1 bg-purple-600 hover:bg-purple-500 text-white font-mono text-sm rounded"
                    >
                      {copied === v.name ? '✓' : v.name}
                    </button>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm text-white">{v.style}</p>
                      <p className="text-xs text-gray-500 mt-0.5">{v.reason}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* 辞書パネル */}
      {showGlossary && (
        <div className="mt-6 p-4 bg-dark-surface border border-blue-700 rounded-lg">
          <h3 className="text-lg font-semibold text-blue-400 mb-3">📚 社内用語辞書</h3>
          {glossary.length === 0 ? (
            <p className="text-sm text-gray-500">
              まだ登録された用語はありません。翻訳結果の「📚 辞書登録」ボタンから追加してください。
            </p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead className="text-left text-xs text-gray-400 border-b border-dark-border">
                  <tr>
                    <th className="py-2 px-2">日本語</th>
                    <th className="py-2 px-2">English</th>
                    <th className="py-2 px-2">略語</th>
                    <th className="py-2 px-2">分類</th>
                    <th className="py-2 px-2">使用回数</th>
                    <th className="py-2 px-2">メモ</th>
                    <th className="py-2 px-2"></th>
                  </tr>
                </thead>
                <tbody>
                  {glossary.map((g) => (
                    <tr key={g.id} className="border-b border-dark-border/50 hover:bg-dark-hover/30">
                      <td className="py-2 px-2 text-white">{g.term_ja}</td>
                      <td className="py-2 px-2 text-white font-mono">{g.term_en}</td>
                      <td className="py-2 px-2 text-yellow-400 font-mono font-bold">{g.abbr}</td>
                      <td className="py-2 px-2 text-gray-300">{g.category}</td>
                      <td className="py-2 px-2 text-center text-gray-400">{g.hit_count}</td>
                      <td className="py-2 px-2 text-gray-400 text-xs max-w-xs truncate" title={g.note}>{g.note}</td>
                      <td className="py-2 px-2">
                        <button
                          onClick={() => void handleDeleteGlossary(g.id)}
                          className="text-xs text-red-400 hover:text-red-300"
                        >
                          削除
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
