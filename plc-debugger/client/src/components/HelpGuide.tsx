interface Props {
  onClose: () => void;
}

export default function HelpGuide({ onClose }: Props) {
  return (
    <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-8" onClick={onClose}>
      <div
        className="bg-dark-surface rounded-xl max-w-3xl w-full max-h-[85vh] overflow-y-auto p-6 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-lg font-bold text-white">使い方ガイド</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-xl">&times;</button>
        </div>

        {/* ワークフロー図 */}
        <div className="mb-8">
          <h3 className="font-semibold text-white mb-4 text-sm flex items-center gap-2">
            <span className="text-lg">🔄</span> ワークフロー概要
          </h3>
          <div className="flex items-center justify-between gap-1 px-2">
            {/* ステップ1 */}
            <div className="flex-1 bg-plc/15 border border-plc/30 rounded-lg p-3 text-center">
              <div className="w-8 h-8 rounded-full bg-plc text-white text-sm font-bold flex items-center justify-center mx-auto mb-2">1</div>
              <p className="text-xs text-white font-medium">アップロード</p>
              <p className="text-[10px] text-gray-400 mt-1">.smc2 / CSV / ST</p>
            </div>
            <span className="text-plc text-lg flex-shrink-0">→</span>
            {/* ステップ2 */}
            <div className="flex-1 bg-blue-500/15 border border-blue-500/30 rounded-lg p-3 text-center">
              <div className="w-8 h-8 rounded-full bg-blue-500 text-white text-sm font-bold flex items-center justify-center mx-auto mb-2">2</div>
              <p className="text-xs text-white font-medium">プログラム解析</p>
              <p className="text-[10px] text-gray-400 mt-1">プログラムの動作を解説</p>
            </div>
            <span className="text-blue-500 text-lg flex-shrink-0">→</span>
            {/* ステップ3 */}
            <div className="flex-1 bg-hmi/15 border border-hmi/30 rounded-lg p-3 text-center">
              <div className="w-8 h-8 rounded-full bg-hmi text-white text-sm font-bold flex items-center justify-center mx-auto mb-2">3</div>
              <p className="text-xs text-white font-medium">デバッグ解析</p>
              <p className="text-[10px] text-gray-400 mt-1">バグ・問題を検出</p>
            </div>
            <span className="text-hmi text-lg flex-shrink-0">→</span>
            {/* ステップ4 */}
            <div className="flex-1 bg-cross/15 border border-cross/30 rounded-lg p-3 text-center">
              <div className="w-8 h-8 rounded-full bg-cross text-white text-sm font-bold flex items-center justify-center mx-auto mb-2">4</div>
              <p className="text-xs text-white font-medium">結果確認</p>
              <p className="text-[10px] text-gray-400 mt-1">各タブで閲覧</p>
            </div>
            <span className="text-cross text-lg flex-shrink-0">→</span>
            {/* ステップ5 */}
            <div className="flex-1 bg-green-500/15 border border-green-500/30 rounded-lg p-3 text-center">
              <div className="w-8 h-8 rounded-full bg-green-600 text-white text-sm font-bold flex items-center justify-center mx-auto mb-2">5</div>
              <p className="text-xs text-white font-medium">トラブルシュート</p>
              <p className="text-[10px] text-gray-400 mt-1">AIチャットで深掘り</p>
            </div>
          </div>
        </div>

        <div className="space-y-6 text-sm text-gray-300">

          {/* ステップ1: ファイルアップロード */}
          <section className="bg-dark-bg rounded-lg p-4 border border-dark-border">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-plc text-white text-xs font-bold flex items-center justify-center">1</span>
              <span className="text-base">📁</span> ファイルアップロード
            </h3>
            <p className="mb-3 text-gray-400">中央のドロップエリアにファイルをドラッグ&ドロップ、またはクリックして選択します。複数ファイルを一括アップロード可能です。</p>
            <h4 className="text-xs font-semibold text-gray-300 mb-2">対応ファイル形式と優先度</h4>
            <div className="grid grid-cols-2 gap-2">
              <div className="bg-dark-surface rounded p-2 border border-plc/20">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-yellow-400 text-xs">★★★</span>
                  <code className="text-plc text-xs">.smc2</code>
                </div>
                <p className="text-[11px] text-gray-400">Sysmac Studio プロジェクトファイル。PLC+HMI全情報を含む。<strong className="text-white">最推奨</strong></p>
              </div>
              <div className="bg-dark-surface rounded p-2 border border-hmi/20">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-yellow-400 text-xs">★★★</span>
                  <span className="text-xs text-gray-300">画像ファイル</span>
                </div>
                <p className="text-[11px] text-gray-400">HMI画面のスクリーンショット。ビジュアルUX分析に使用</p>
              </div>
              <div className="bg-dark-surface rounded p-2 border border-cross/20">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-yellow-400 text-xs">★★☆</span>
                  <code className="text-cross text-xs">.csv / .st / .txt</code>
                </div>
                <p className="text-[11px] text-gray-400">変数テーブルCSVやSTプログラムテキスト。.smc2が使えない場合に</p>
              </div>
              <div className="bg-dark-surface rounded p-2 border border-red-500/20">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-yellow-400 text-xs">★☆☆</span>
                  <code className="text-red-400 text-xs">.pdf</code>
                </div>
                <p className="text-[11px] text-gray-400">ラダー図PDFは精度が落ちるため最終手段として使用</p>
              </div>
            </div>
          </section>

          {/* ステップ2: プログラム解析 */}
          <section className="bg-dark-bg rounded-lg p-4 border border-dark-border">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-blue-500 text-white text-xs font-bold flex items-center justify-center">2</span>
              <span className="text-base">📊</span> プログラム解析
            </h3>
            <p className="text-gray-400 mb-3">アップロードしたプログラムの動作内容をAIが詳細に解説します。セクションごとにフローチャートも自動生成されます。</p>
            <ul className="space-y-1.5 text-gray-400">
              <li className="flex gap-2">
                <span className="text-blue-400 flex-shrink-0">✓</span>
                <span>プログラム全体の概要を日本語で分かりやすく解説</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400 flex-shrink-0">✓</span>
                <span>セクション（機能単位）ごとに分割して動作を説明</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400 flex-shrink-0">✓</span>
                <span>各セクションのフローチャートを自動生成（産業用設計書品質）</span>
              </li>
              <li className="flex gap-2">
                <span className="text-blue-400 flex-shrink-0">✓</span>
                <span>主要変数の一覧と設計パターンの特定</span>
              </li>
            </ul>
          </section>

          {/* ステップ3: デバッグ解析 */}
          <section className="bg-dark-bg rounded-lg p-4 border border-dark-border">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-hmi text-white text-xs font-bold flex items-center justify-center">3</span>
              <span className="text-base">🐛</span> デバッグ解析の実行
            </h3>
            <ol className="space-y-2 text-gray-400 mb-4">
              <li className="flex gap-2">
                <span className="text-hmi font-bold flex-shrink-0">①</span>
                <span>ファイルをアップロードすると、左サイドバーにプロジェクト情報が表示されます</span>
              </li>
              <li className="flex gap-2">
                <span className="text-hmi font-bold flex-shrink-0">②</span>
                <span>サイドバー下部の<strong className="text-white">「🐛 デバッグ解析」</strong>ボタンをクリック</span>
              </li>
              <li className="flex gap-2">
                <span className="text-hmi font-bold flex-shrink-0">③</span>
                <span>AIがプログラム・変数・HMI画面を総合的に解析し、問題点を重要度別に一覧表示します</span>
              </li>
              <li className="flex gap-2">
                <span className="text-hmi font-bold flex-shrink-0">④</span>
                <span>各バグカードをクリックで展開すると詳細と改善提案が表示されます</span>
              </li>
            </ol>
            {/* トラブルシュート連携 */}
            <div className="bg-green-900/20 border border-green-500/30 rounded-lg p-3">
              <p className="text-xs font-bold text-green-400 mb-1.5 flex items-center gap-1.5">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
                </svg>
                トラブルシュート連携機能
              </p>
              <p className="text-[11px] text-gray-300">バグカード展開後に表示される <strong className="text-green-400">「この問題をAIに相談する」</strong> ボタンを押すと、そのバグの詳細情報が右側のトラブルシュートチャットに自動送信され、AIが即座に原因と対策を回答します。</p>
            </div>
          </section>

          {/* ステップ4: 分析タブ */}
          <section className="bg-dark-bg rounded-lg p-4 border border-dark-border">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-cross text-white text-xs font-bold flex items-center justify-center">4</span>
              <span className="text-base">📊</span> 各分析タブの説明
            </h3>
            <div className="space-y-2">
              <div className="flex items-start gap-3 bg-dark-surface rounded p-2.5">
                <span className="w-3 h-3 rounded-full bg-plc mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-white font-medium text-xs">PLC分析</p>
                  <p className="text-[11px] text-gray-400">PLCプログラムのバグ・ロジックエラー・安全性の問題を検出。変数の型不整合や未使用変数も報告します。</p>
                </div>
              </div>
              <div className="flex items-start gap-3 bg-dark-surface rounded p-2.5">
                <span className="w-3 h-3 rounded-full bg-hmi mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-white font-medium text-xs">HMI分析</p>
                  <p className="text-[11px] text-gray-400">HMI画面単体の問題点を分析。操作安全性・アラーム網羅性・UIデザインの一貫性をチェックします。</p>
                </div>
              </div>
              <div className="flex items-start gap-3 bg-dark-surface rounded p-2.5">
                <span className="w-3 h-3 rounded-full bg-cross mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-white font-medium text-xs">クロスリファレンス</p>
                  <p className="text-[11px] text-gray-400">PLC変数とHMI画面の紐付けを検証。未接続の変数や表示されていないアラームを検出します。</p>
                </div>
              </div>
              <div className="flex items-start gap-3 bg-dark-surface rounded p-2.5">
                <span className="w-3 h-3 rounded-full bg-hmi mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-white font-medium text-xs">画面遷移図</p>
                  <p className="text-[11px] text-gray-400">HMI画面間のナビゲーションをMermaid形式のダイアグラムで可視化。到達不能画面がないか確認できます。</p>
                </div>
              </div>
              <div className="flex items-start gap-3 bg-dark-surface rounded p-2.5">
                <span className="w-3 h-3 rounded-full bg-purple-400 mt-0.5 flex-shrink-0" />
                <div>
                  <p className="text-white font-medium text-xs">スクリーンショット</p>
                  <p className="text-[11px] text-gray-400">アップロードしたHMI画面キャプチャをAIがビジュアル分析。UIレイアウト・色使い・視認性を評価します。</p>
                </div>
              </div>
            </div>
          </section>

          {/* 重要度の説明 */}
          <section className="bg-dark-bg rounded-lg p-4 border border-dark-border">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
              <span className="text-base">⚠️</span> severity（重要度）の見方
            </h3>
            <div className="grid grid-cols-3 gap-2">
              <div className="bg-severity-critical/10 border border-severity-critical/30 rounded p-2 text-center">
                <p className="text-severity-critical font-bold text-xs">CRITICAL</p>
                <p className="text-[10px] text-gray-400 mt-1">安全性に関わる重大な問題</p>
              </div>
              <div className="bg-severity-warning/10 border border-severity-warning/30 rounded p-2 text-center">
                <p className="text-severity-warning font-bold text-xs">WARNING</p>
                <p className="text-[10px] text-gray-400 mt-1">潜在的な不具合・改善推奨</p>
              </div>
              <div className="bg-severity-info/10 border border-severity-info/30 rounded p-2 text-center">
                <p className="text-severity-info font-bold text-xs">INFO</p>
                <p className="text-[10px] text-gray-400 mt-1">保守性・可読性の改善提案</p>
              </div>
            </div>
          </section>

          {/* ステップ5: トラブルシュート */}
          <section className="bg-dark-bg rounded-lg p-4 border border-dark-border">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
              <span className="w-6 h-6 rounded bg-green-600 text-white text-xs font-bold flex items-center justify-center">5</span>
              <span className="text-base">💬</span> トラブルシュートチャット
            </h3>
            <p className="text-gray-400 mb-3">画面右側のチャットパネルで、不具合の現象をAIに自由に質問できます。<strong className="text-white">アップロードしたプログラムの内容を常に把握した上で</strong>回答します。</p>
            <ul className="space-y-1.5 text-gray-400 mb-3">
              <li className="flex gap-2">
                <span className="text-green-400 flex-shrink-0">✓</span>
                <span>不具合の現象をテキストで自由に質問（例：「コンベアが止まらない原因は？」）</span>
              </li>
              <li className="flex gap-2">
                <span className="text-green-400 flex-shrink-0">✓</span>
                <span>HMI画面のスクリーンショットを添付して質問可能（📷 ボタンで添付）</span>
              </li>
              <li className="flex gap-2">
                <span className="text-green-400 flex-shrink-0">✓</span>
                <span>アップロード済みプロジェクトのプログラム・変数・HMI画面すべてが文脈として渡される</span>
              </li>
              <li className="flex gap-2">
                <span className="text-green-400 flex-shrink-0">✓</span>
                <span>デバッグ解析のバグカードから「AIに相談」ボタンで直接連携可能</span>
              </li>
              <li className="flex gap-2">
                <span className="text-green-400 flex-shrink-0">✓</span>
                <span>Enter キーで送信 / Shift+Enter で改行</span>
              </li>
            </ul>
            <div className="bg-blue-900/20 border border-blue-500/30 rounded p-2.5 text-[11px] text-gray-300">
              💡 <strong className="text-blue-400">ポイント：</strong>ファイルをアップロードさえすれば、「この変数の使われ方を教えて」「このセクションのロジックを説明して」など、プログラムの内容に関するあらゆる質問に答えられます。
            </div>
          </section>

          {/* プログラム生成 */}
          <section className="bg-dark-bg rounded-lg p-4 border border-dark-border">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
              <span className="px-1.5 py-0.5 rounded bg-green-600 text-white text-[10px] font-bold">NEW</span>
              <span className="text-base">🔨</span> プログラム生成
            </h3>
            <p className="text-gray-400 mb-3">作りたいプログラムの動作を日本語で説明するだけで、AIがPLCプログラムを自動生成します。</p>
            <ul className="space-y-1.5 text-gray-400">
              <li className="flex gap-2">
                <span className="text-green-400 flex-shrink-0">✓</span>
                <span>ST言語またはラダー図（LD）を選択可能</span>
              </li>
              <li className="flex gap-2">
                <span className="text-green-400 flex-shrink-0">✓</span>
                <span>IEC 61131-3 / JIS B 3503 準拠のプロフェッショナルなコード生成</span>
              </li>
              <li className="flex gap-2">
                <span className="text-green-400 flex-shrink-0">✓</span>
                <span>自己保持回路・インターロック等の基本回路を自動適用</span>
              </li>
              <li className="flex gap-2">
                <span className="text-green-400 flex-shrink-0">✓</span>
                <span>ラダー図モードではフローチャート・ラダー図・テキストの3ビュー切替</span>
              </li>
              <li className="flex gap-2">
                <span className="text-green-400 flex-shrink-0">✓</span>
                <span>変数テーブル・安全上の注意・テスト手順も自動出力</span>
              </li>
              <li className="flex gap-2">
                <span className="text-green-400 flex-shrink-0">✓</span>
                <span>サンプルプロンプトをクリックして簡単に開始</span>
              </li>
            </ul>
          </section>

          {/* CSV出力 */}
          <section className="bg-dark-bg rounded-lg p-4 border border-dark-border">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
              <span className="text-base">📥</span> CSV出力
            </h3>
            <p className="text-gray-400 mb-2">デバッグ解析の結果をCSVファイルとしてダウンロードできます。</p>
            <ol className="space-y-1.5 text-gray-400">
              <li className="flex gap-2">
                <span className="text-plc font-bold flex-shrink-0">①</span>
                <span>🐛 デバッグ解析を実行して結果を表示</span>
              </li>
              <li className="flex gap-2">
                <span className="text-plc font-bold flex-shrink-0">②</span>
                <span>画面上部の<strong className="text-white">「CSV出力」</strong>ボタンをクリック</span>
              </li>
              <li className="flex gap-2">
                <span className="text-plc font-bold flex-shrink-0">③</span>
                <span>バグID・重要度・カテゴリ・説明・対策が含まれたCSVがダウンロードされます</span>
              </li>
            </ol>
            <p className="text-[11px] text-gray-500 mt-2">※ Excel等で開いてチーム共有やバグトラッキングに活用できます</p>
          </section>

          {/* 機能一覧サマリー */}
          <section className="bg-dark-bg rounded-lg p-4 border border-dark-border">
            <h3 className="font-semibold text-white mb-3 flex items-center gap-2">
              <span className="text-base">⚡</span> 全機能サマリー
            </h3>
            <div className="grid grid-cols-2 gap-2 text-[11px]">
              <div className="bg-dark-surface rounded p-2 border border-blue-500/20">
                <p className="text-blue-400 font-bold mb-1">📊 プログラム解析</p>
                <p className="text-gray-400">何をするプログラムか解説・フローチャート生成</p>
              </div>
              <div className="bg-dark-surface rounded p-2 border border-orange-500/20">
                <p className="text-orange-400 font-bold mb-1">🐛 デバッグ解析</p>
                <p className="text-gray-400">バグ・安全問題・HMI問題を重要度別に検出</p>
              </div>
              <div className="bg-dark-surface rounded p-2 border border-green-500/20">
                <p className="text-green-400 font-bold mb-1">🔨 プログラム生成</p>
                <p className="text-gray-400">自然言語 → ST/LD コード自動生成（IEC準拠）</p>
              </div>
              <div className="bg-dark-surface rounded p-2 border border-green-500/20">
                <p className="text-green-400 font-bold mb-1">💬 トラブルシュート</p>
                <p className="text-gray-400">プログラム内容を踏まえたAIチャット</p>
              </div>
              <div className="bg-dark-surface rounded p-2 border border-plc/20">
                <p className="text-plc font-bold mb-1">🔗 デバッグ×AI連携</p>
                <p className="text-gray-400">バグカードから1クリックでAIに相談</p>
              </div>
              <div className="bg-dark-surface rounded p-2 border border-gray-500/20">
                <p className="text-gray-300 font-bold mb-1">📥 CSV出力</p>
                <p className="text-gray-400">解析結果をExcelで共有・管理</p>
              </div>
            </div>
          </section>

        </div>
      </div>
    </div>
  );
}
