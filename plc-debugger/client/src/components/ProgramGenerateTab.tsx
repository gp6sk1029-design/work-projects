import { useState, useRef, useCallback } from 'react';
import type { GeneratedProgram } from '../types';
import LadderDiagramRenderer from './LadderDiagramRenderer';
import FlowchartRenderer from './FlowchartRenderer';

type LdViewMode = 'ladder' | 'flowchart' | 'text';

const EXAMPLE_PROMPTS = [
  'コンベア制御：センサで検知したワークを3つのステーションに搬送',
  'シリンダ往復動作：前進端・後退端センサ付き、タイムアウトエラー検出',
  '温度PID制御：ヒーター出力、上下限アラーム付き',
  'ロボットピック&プレース：5軸、原点復帰→ピック→プレース→待機',
];

const CONTROLLERS = [
  { value: 'NX102', label: 'NX102' },
  { value: 'NJ501', label: 'NJ501' },
  { value: 'NX1P2', label: 'NX1P2' },
];

// ST言語のキーワードに色を付ける簡易ハイライター
function highlightST(code: string): JSX.Element[] {
  const lines = code.split('\n');
  return lines.map((line, i) => {
    // コメント行
    if (line.trimStart().startsWith('//') || line.trimStart().startsWith('(*')) {
      return (
        <div key={i} className="table-row">
          <span className="table-cell pr-4 text-right text-gray-600 select-none w-12">{i + 1}</span>
          <span className="table-cell text-green-400">{line}</span>
        </div>
      );
    }

    // キーワードハイライト
    const parts: JSX.Element[] = [];
    let remaining = line;
    let partIdx = 0;

    // 正規表現でトークンを分割
    const regex = /(\bIF\b|\bTHEN\b|\bELSE\b|\bELSIF\b|\bEND_IF\b|\bFOR\b|\bTO\b|\bDO\b|\bEND_FOR\b|\bWHILE\b|\bEND_WHILE\b|\bCASE\b|\bOF\b|\bEND_CASE\b|\bREPEAT\b|\bUNTIL\b|\bEND_REPEAT\b|\bRETURN\b|\bEXIT\b|\bNOT\b|\bAND\b|\bOR\b|\bXOR\b|\bMOD\b|\bTRUE\b|\bFALSE\b|\bVAR\b|\bVAR_GLOBAL\b|\bVAR_INPUT\b|\bVAR_OUTPUT\b|\bVAR_IN_OUT\b|\bEND_VAR\b|\bPROGRAM\b|\bEND_PROGRAM\b|\bFUNCTION\b|\bEND_FUNCTION\b|\bFUNCTION_BLOCK\b|\bEND_FUNCTION_BLOCK\b|\bBOOL\b|\bINT\b|\bDINT\b|\bLINT\b|\bREAL\b|\bLREAL\b|\bSTRING\b|\bTIME\b|\bWORD\b|\bDWORD\b|\bBYTE\b|\bUSINT\b|\bUINT\b|\bUDINT\b|\bULINT\b|\bSINT\b|\bDATE\b|\bTON\b|\bTOF\b|\bTP\b|\bCTU\b|\bCTD\b|\bR_TRIG\b|\bF_TRIG\b)|('.*?')|(".*?")|(\(\*[\s\S]*?\*\))|(\/\/.*$)/g;

    const tokens: { index: number; length: number; text: string; type: string }[] = [];
    let match;
    while ((match = regex.exec(remaining)) !== null) {
      let type = 'keyword';
      if (match[1]) {
        // キーワード分類
        const kw = match[1];
        if (/^(VAR|VAR_GLOBAL|VAR_INPUT|VAR_OUTPUT|VAR_IN_OUT|END_VAR|PROGRAM|END_PROGRAM|FUNCTION|END_FUNCTION|FUNCTION_BLOCK|END_FUNCTION_BLOCK)$/.test(kw)) {
          type = 'declaration';
        } else if (/^(BOOL|INT|DINT|LINT|REAL|LREAL|STRING|TIME|WORD|DWORD|BYTE|USINT|UINT|UDINT|ULINT|SINT|DATE)$/.test(kw)) {
          type = 'type';
        } else if (/^(TRUE|FALSE)$/.test(kw)) {
          type = 'literal';
        } else if (/^(TON|TOF|TP|CTU|CTD|R_TRIG|F_TRIG)$/.test(kw)) {
          type = 'function';
        }
      } else if (match[2] || match[3]) {
        type = 'string';
      } else if (match[4] || match[5]) {
        type = 'comment';
      }
      tokens.push({ index: match.index, length: match[0].length, text: match[0], type });
    }

    if (tokens.length === 0) {
      return (
        <div key={i} className="table-row">
          <span className="table-cell pr-4 text-right text-gray-600 select-none w-12">{i + 1}</span>
          <span className="table-cell">{line}</span>
        </div>
      );
    }

    let lastEnd = 0;
    for (const token of tokens) {
      if (token.index > lastEnd) {
        parts.push(<span key={partIdx++}>{remaining.slice(lastEnd, token.index)}</span>);
      }
      const colorClass =
        token.type === 'keyword' ? 'text-blue-400' :
        token.type === 'declaration' ? 'text-purple-400' :
        token.type === 'type' ? 'text-cyan-400' :
        token.type === 'literal' ? 'text-yellow-400' :
        token.type === 'function' ? 'text-blue-300' :
        token.type === 'string' ? 'text-orange-400' :
        token.type === 'comment' ? 'text-green-400' :
        '';
      parts.push(<span key={partIdx++} className={colorClass}>{token.text}</span>);
      lastEnd = token.index + token.length;
    }
    if (lastEnd < remaining.length) {
      parts.push(<span key={partIdx++}>{remaining.slice(lastEnd)}</span>);
    }

    return (
      <div key={i} className="table-row">
        <span className="table-cell pr-4 text-right text-gray-600 select-none w-12">{i + 1}</span>
        <span className="table-cell">{...parts}</span>
      </div>
    );
  });
}

export default function ProgramGenerateTab() {
  const [description, setDescription] = useState('');
  const [language, setLanguage] = useState<'ST' | 'LD'>('ST');
  const [controllerType, setControllerType] = useState('NX102');
  const [result, setResult] = useState<GeneratedProgram | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [ldViewMode, setLdViewMode] = useState<LdViewMode>('ladder');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleGenerate = useCallback(async () => {
    if (!description.trim()) return;
    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ description, language, controllerType }),
      });
      if (!res.ok) {
        const errData = await res.json().catch(() => ({}));
        throw new Error(errData.error || `サーバーエラー (${res.status})`);
      }
      const data: GeneratedProgram = await res.json();
      setResult(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'プログラム生成中にエラーが発生しました');
    } finally {
      setIsLoading(false);
    }
  }, [description, language, controllerType]);

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleGenerate();
    }
  };

  const handleClear = () => {
    setDescription('');
    setResult(null);
    setError(null);
    textareaRef.current?.focus();
  };

  const handleCopyCode = () => {
    if (result) {
      navigator.clipboard.writeText(result.code);
    }
  };

  const handleDownloadCode = () => {
    if (!result) return;
    const ext = result.language === 'ST' ? '.st' : '.txt';
    const blob = new Blob([result.code], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `generated_program${ext}`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-6">
      {/* === 入力セクション === */}
      <div className="bg-dark-surface rounded-lg border border-dark-border p-5">
        <h3 className="text-lg font-bold text-white mb-4 flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-green-500" />
          プログラム生成
        </h3>

        {/* サンプルプロンプト */}
        <div className="mb-3">
          <p className="text-xs text-gray-400 mb-2">サンプル（クリックで入力）:</p>
          <div className="flex flex-wrap gap-2">
            {EXAMPLE_PROMPTS.map((prompt) => (
              <button
                key={prompt}
                onClick={() => {
                  setDescription(prompt);
                  textareaRef.current?.focus();
                }}
                className="px-3 py-1.5 bg-dark-hover border border-dark-border rounded-full text-xs text-gray-300 hover:text-white hover:border-green-500/50 transition"
              >
                {prompt}
              </button>
            ))}
          </div>
        </div>

        {/* テキストエリア */}
        <textarea
          ref={textareaRef}
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="作りたいプログラムの動作を日本語で説明してください...&#10;&#10;例：コンベアのセンサでワークを検知したら、シリンダを前進させて押し出す。前進端センサがONになったら後退させる。タイムアウトは3秒。"
          rows={4}
          className="w-full bg-dark-bg border border-dark-border rounded-lg p-3 text-sm text-gray-200 placeholder-gray-500 resize-y focus:outline-none focus:border-green-500/50 transition"
        />

        {/* オプション行 */}
        <div className="flex items-center gap-4 mt-3 flex-wrap">
          {/* 言語セレクタ */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">言語:</span>
            <div className="flex rounded-lg overflow-hidden border border-dark-border">
              <button
                onClick={() => setLanguage('ST')}
                className={`px-3 py-1.5 text-xs font-medium transition ${
                  language === 'ST'
                    ? 'bg-green-600 text-white'
                    : 'bg-dark-hover text-gray-400 hover:text-white'
                }`}
              >
                ST言語
              </button>
              <button
                onClick={() => setLanguage('LD')}
                className={`px-3 py-1.5 text-xs font-medium transition ${
                  language === 'LD'
                    ? 'bg-green-600 text-white'
                    : 'bg-dark-hover text-gray-400 hover:text-white'
                }`}
              >
                ラダー図
              </button>
            </div>
          </div>

          {/* コントローラセレクタ */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-gray-400">コントローラ:</span>
            <select
              value={controllerType}
              onChange={(e) => setControllerType(e.target.value)}
              className="bg-dark-bg border border-dark-border rounded-lg px-3 py-1.5 text-xs text-gray-200 focus:outline-none focus:border-green-500/50"
            >
              {CONTROLLERS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>

          {/* ボタン群 */}
          <div className="ml-auto flex items-center gap-2">
            <button
              onClick={handleClear}
              className="px-4 py-1.5 bg-dark-hover border border-dark-border rounded-lg text-xs text-gray-400 hover:text-white transition"
            >
              クリア
            </button>
            <button
              onClick={handleGenerate}
              disabled={!description.trim() || isLoading}
              className="px-5 py-1.5 bg-green-600 hover:bg-green-500 disabled:bg-green-600/30 disabled:text-green-400/50 rounded-lg text-sm font-bold text-white transition"
            >
              {isLoading ? (
                <span className="flex items-center gap-2">
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  生成中...
                </span>
              ) : (
                'プログラム生成'
              )}
            </button>
          </div>
        </div>

        {/* ヒントテキスト */}
        <p className="text-xs text-gray-500 mt-2">
          Enter で送信 / Shift+Enter で改行
        </p>
      </div>

      {/* === エラー表示 === */}
      {error && (
        <div className="bg-red-900/20 border border-red-500/30 rounded-lg p-4 text-sm text-red-400">
          <span className="font-bold">エラー:</span> {error}
        </div>
      )}

      {/* === ローディング状態 === */}
      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center">
            <div className="w-10 h-10 border-3 border-green-500/30 border-t-green-500 rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-400 text-sm">Claude AI がプログラムを生成中...</p>
            <p className="text-gray-500 text-xs mt-1">しばらくお待ちください</p>
          </div>
        </div>
      )}

      {/* === 結果セクション === */}
      {result && !isLoading && (
        <div className="space-y-4">
          {/* 生成コード */}
          <div className="bg-dark-surface rounded-lg border border-dark-border overflow-hidden">
            <div className="flex items-center justify-between px-4 py-2 bg-dark-hover border-b border-dark-border">
              <span className="text-xs text-gray-400 font-mono">
                {result.language === 'ST' ? 'Structured Text' : 'Ladder Diagram'} — {controllerType}
              </span>
              <div className="flex items-center gap-2">
                {/* LD言語の場合、表示モード切替ボタン */}
                {result.language === 'LD' && (
                  <div className="flex rounded-lg overflow-hidden border border-dark-border mr-2">
                    <button
                      onClick={() => setLdViewMode('ladder')}
                      className={`px-2 py-1 text-[11px] font-medium transition ${
                        ldViewMode === 'ladder'
                          ? 'bg-blue-600 text-white'
                          : 'bg-dark-bg text-gray-400 hover:text-white'
                      }`}
                    >
                      ラダー図表示
                    </button>
                    <button
                      onClick={() => setLdViewMode('flowchart')}
                      className={`px-2 py-1 text-[11px] font-medium transition ${
                        ldViewMode === 'flowchart'
                          ? 'bg-blue-600 text-white'
                          : 'bg-dark-bg text-gray-400 hover:text-white'
                      }`}
                    >
                      フローチャート表示
                    </button>
                    <button
                      onClick={() => setLdViewMode('text')}
                      className={`px-2 py-1 text-[11px] font-medium transition ${
                        ldViewMode === 'text'
                          ? 'bg-blue-600 text-white'
                          : 'bg-dark-bg text-gray-400 hover:text-white'
                      }`}
                    >
                      テキスト表示
                    </button>
                  </div>
                )}
                <button
                  onClick={handleCopyCode}
                  className="px-2 py-1 bg-dark-bg hover:bg-dark-border rounded text-xs text-gray-300 hover:text-white transition"
                >
                  コピー
                </button>
                <button
                  onClick={handleDownloadCode}
                  className="px-2 py-1 bg-dark-bg hover:bg-dark-border rounded text-xs text-gray-300 hover:text-white transition"
                >
                  ダウンロード
                </button>
              </div>
            </div>
            {/* LD言語の表示モード切替 */}
            {result.language === 'LD' && ldViewMode === 'ladder' ? (
              result.ladderRungs && result.ladderRungs.length > 0 ? (
                <div className="p-4 overflow-x-auto max-h-[600px] overflow-y-auto">
                  <LadderDiagramRenderer rungs={result.ladderRungs} />
                </div>
              ) : (
                <div className="p-4">
                  <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-4 text-sm text-yellow-400 mb-4">
                    ラダー図データを取得できませんでした。テキスト表示で確認してください。
                  </div>
                  <pre className="text-sm font-mono text-gray-200">
                    <div className="table w-full">{highlightST(result.code)}</div>
                  </pre>
                </div>
              )
            ) : result.language === 'LD' && ldViewMode === 'flowchart' ? (
              result.flowchartSteps && result.flowchartSteps.length > 0 ? (
                <div className="p-4 overflow-x-auto max-h-[700px] overflow-y-auto">
                  <FlowchartRenderer steps={result.flowchartSteps} title={`${controllerType} フローチャート`} />
                </div>
              ) : result.flowchart ? (
                <div className="p-4 overflow-x-auto max-h-[600px] overflow-y-auto">
                  <div className="bg-dark-bg rounded-lg p-4">
                    <h3 className="text-xs font-semibold text-gray-400 mb-2">フローチャート（テキスト）</h3>
                    <pre className="text-xs text-gray-300 font-mono whitespace-pre-wrap">{result.flowchart}</pre>
                  </div>
                </div>
              ) : (
                <div className="p-4">
                  <div className="bg-yellow-900/20 border border-yellow-500/30 rounded-lg p-4 text-sm text-yellow-400 mb-4">
                    フローチャートデータを取得できませんでした。テキスト表示で確認してください。
                  </div>
                  <pre className="text-sm font-mono text-gray-200">
                    <div className="table w-full">{highlightST(result.code)}</div>
                  </pre>
                </div>
              )
            ) : (
              <div className="p-4 overflow-x-auto max-h-[500px] overflow-y-auto">
                <pre className="text-sm font-mono text-gray-200">
                  <div className="table w-full">
                    {highlightST(result.code)}
                  </div>
                </pre>
              </div>
            )}
          </div>

          {/* 解説 */}
          <div className="bg-dark-surface rounded-lg border border-dark-border p-5">
            <h4 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
              <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              解説
            </h4>
            <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap">
              {result.explanation}
            </div>
          </div>

          {/* 変数テーブル */}
          {result.variables.length > 0 && (
            <div className="bg-dark-surface rounded-lg border border-dark-border overflow-hidden">
              <div className="px-5 py-3 border-b border-dark-border">
                <h4 className="text-sm font-bold text-white flex items-center gap-2">
                  <svg className="w-4 h-4 text-cyan-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2 1 3 3 3h10c2 0 3-1 3-3V7c0-2-1-3-3-3H7C5 4 4 5 4 7z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 4v16M4 9h16M4 14h16" />
                  </svg>
                  変数テーブル
                </h4>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="bg-dark-hover text-gray-400 text-xs">
                      <th className="px-4 py-2 text-left font-medium">変数名</th>
                      <th className="px-4 py-2 text-left font-medium">データ型</th>
                      <th className="px-4 py-2 text-left font-medium">説明</th>
                      <th className="px-4 py-2 text-left font-medium">初期値</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.variables.map((v, i) => (
                      <tr key={i} className="border-t border-dark-border hover:bg-dark-hover/50 transition">
                        <td className="px-4 py-2 font-mono text-green-400">{v.name}</td>
                        <td className="px-4 py-2 font-mono text-cyan-400">{v.type}</td>
                        <td className="px-4 py-2 text-gray-300">{v.description}</td>
                        <td className="px-4 py-2 font-mono text-yellow-400">{v.initialValue || '-'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* 安全上の注意 */}
          {result.safetyNotes.length > 0 && (
            <div className="bg-dark-surface rounded-lg border border-dark-border p-5">
              <h4 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                <svg className="w-4 h-4 text-yellow-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4.5c-.77-.833-2.694-.833-3.464 0L3.34 16.5c-.77.833.192 2.5 1.732 2.5z" />
                </svg>
                安全上の注意
              </h4>
              <ul className="space-y-2">
                {result.safetyNotes.map((note, i) => (
                  <li key={i} className="flex items-start gap-2 text-sm text-gray-300">
                    <svg className="w-4 h-4 text-yellow-500 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                    </svg>
                    {note}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* テスト手順 */}
          {result.testProcedures.length > 0 && (
            <div className="bg-dark-surface rounded-lg border border-dark-border p-5">
              <h4 className="text-sm font-bold text-white mb-3 flex items-center gap-2">
                <svg className="w-4 h-4 text-green-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                テスト手順
              </h4>
              <ol className="space-y-2">
                {result.testProcedures.map((proc, i) => (
                  <li key={i} className="flex items-start gap-3 text-sm text-gray-300">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-green-600/20 text-green-400 flex items-center justify-center text-xs font-bold">
                      {i + 1}
                    </span>
                    {proc}
                  </li>
                ))}
              </ol>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
