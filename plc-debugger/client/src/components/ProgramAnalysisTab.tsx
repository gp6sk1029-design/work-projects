import { useState } from 'react';
import FlowchartRenderer from './FlowchartRenderer';
import type { FlowchartElement } from '../types';

// === 型定義 ===
interface ProgramSection {
  name: string;
  language: string;
  description: string;
  explanation: string;
  flowchartSteps: FlowchartElement[];
  keyVariables: { name: string; type: string; description: string }[];
  designPatterns: string[];
}

interface Props {
  overview: string;
  sections: ProgramSection[];
}

export default function ProgramAnalysisTab({ overview, sections }: Props) {
  // 最初のセクションだけ展開した状態で初期化
  const [openSections, setOpenSections] = useState<Set<number>>(
    () => new Set(sections.length > 0 ? [0] : [])
  );

  // アコーディオンの開閉トグル
  const toggleSection = (index: number) => {
    setOpenSections((prev) => {
      const next = new Set(prev);
      if (next.has(index)) {
        next.delete(index);
      } else {
        next.add(index);
      }
      return next;
    });
  };

  return (
    <div className="space-y-4">
      {/* === 全体概要カード === */}
      <div className="bg-dark-surface border border-dark-border rounded-lg p-5">
        <h2 className="flex items-center gap-2 text-base font-semibold text-white mb-3">
          <span className="bg-white rounded p-1 text-sm leading-none">📋</span>
          プログラム概要
        </h2>
        <p className="text-gray-300 text-sm whitespace-pre-wrap leading-relaxed">
          {overview}
        </p>
      </div>

      {/* === セクション一覧（アコーディオン） === */}
      {sections.map((section, idx) => {
        const isOpen = openSections.has(idx);

        return (
          <div
            key={idx}
            className="bg-dark-surface border border-dark-border rounded-lg overflow-hidden"
          >
            {/* --- ヘッダー（クリックで展開/折りたたみ） --- */}
            <button
              type="button"
              className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-white/5 transition-colors"
              onClick={() => toggleSection(idx)}
            >
              {/* セクション番号バッジ */}
              <span className="flex-shrink-0 w-7 h-7 flex items-center justify-center rounded-full bg-blue-600 text-white text-xs font-bold">
                {idx + 1}
              </span>

              {/* セクション名 + description */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-white font-bold text-sm">
                    {section.name}
                  </span>
                  {/* 言語タグ */}
                  <span className="text-[10px] font-semibold px-2 py-0.5 rounded bg-gray-700 text-gray-300 uppercase">
                    {section.language}
                  </span>
                </div>
                {section.description && (
                  <p className="text-gray-500 text-xs mt-0.5 truncate">
                    {section.description}
                  </p>
                )}
              </div>

              {/* 展開/折りたたみアイコン */}
              <span className="flex-shrink-0 text-gray-400 text-xs transition-transform duration-200">
                {isOpen ? '▼' : '▶'}
              </span>
            </button>

            {/* --- 展開コンテンツ --- */}
            {isOpen && (
              <div className="px-4 pb-4 space-y-4 border-t border-dark-border pt-4">
                {/* a. 動作説明 */}
                <div>
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-white mb-2">
                    <span>📝</span> 動作説明
                  </h3>
                  <p className="text-gray-300 text-sm whitespace-pre-wrap leading-relaxed">
                    {section.explanation}
                  </p>
                </div>

                {/* b. フローチャート */}
                <div>
                  <h3 className="flex items-center gap-2 text-sm font-semibold text-white mb-2">
                    <span>📊</span> フローチャート
                  </h3>
                  {section.flowchartSteps && section.flowchartSteps.length > 0 ? (
                    <FlowchartRenderer
                      steps={section.flowchartSteps}
                      title={section.name}
                    />
                  ) : (
                    <p className="text-gray-500 text-sm italic">
                      フローチャートデータがありません
                    </p>
                  )}
                </div>

                {/* c. 主要変数テーブル */}
                {section.keyVariables && section.keyVariables.length > 0 && (
                  <div>
                    <h3 className="flex items-center gap-2 text-sm font-semibold text-white mb-2">
                      <span>🔧</span> 主要変数
                    </h3>
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm text-left">
                        <thead>
                          <tr className="border-b border-dark-border text-gray-400 text-xs uppercase">
                            <th className="py-2 px-3">変数名</th>
                            <th className="py-2 px-3">データ型</th>
                            <th className="py-2 px-3">用途</th>
                          </tr>
                        </thead>
                        <tbody>
                          {section.keyVariables.map((v, vIdx) => (
                            <tr
                              key={vIdx}
                              className="border-b border-dark-border/50 hover:bg-white/5"
                            >
                              <td className="py-2 px-3 text-blue-400 font-mono text-xs">
                                {v.name}
                              </td>
                              <td className="py-2 px-3 text-gray-400 font-mono text-xs">
                                {v.type}
                              </td>
                              <td className="py-2 px-3 text-gray-300">
                                {v.description}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* d. 設計パターン */}
                {section.designPatterns && section.designPatterns.length > 0 && (
                  <div>
                    <h3 className="flex items-center gap-2 text-sm font-semibold text-white mb-2">
                      <span>🏗️</span> 使用設計パターン
                    </h3>
                    <div className="flex flex-wrap gap-2">
                      {section.designPatterns.map((pattern, pIdx) => (
                        <span
                          key={pIdx}
                          className="bg-blue-600/20 text-blue-400 rounded-full px-3 py-1 text-xs font-medium"
                        >
                          {pattern}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        );
      })}

      {/* セクションが空の場合 */}
      {sections.length === 0 && (
        <div className="text-center text-gray-500 py-12">
          <p className="text-lg">解析対象のセクションがありません</p>
        </div>
      )}
    </div>
  );
}
