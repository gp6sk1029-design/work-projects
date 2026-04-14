import { GoogleGenerativeAI } from '@google/generative-ai';
import type { Smc2Project } from './smc2Parser';

const MODEL = 'gemini-2.5-flash';

// バグ分析用システムプロンプト
const BUG_ANALYSIS_SYSTEM_PROMPT = `あなたはオムロン Sysmac Studio（NJ/NXシリーズ）専門のPLCプログラム＋HMI画面解析エンジニアです。
15年以上の制御設計経験を持ち、自動車・半導体・食品業界の生産設備を手掛けてきました。
PLCプログラムだけでなく、NA-series HMI画面設計にも精通しています。

【チェック観点 — PLC】
1. 論理エラー（条件の矛盾、到達不能コード、デッドロック）
2. タイミング問題（タスク周期との不整合、競合、優先度逆転）
3. エラーハンドリング不足（通信エラー、軸エラー、異常復帰）
4. 安全上の問題（非常停止処理、インターロック欠落）
5. モーション制御の状態遷移不備
6. 二重コイル・変数競合
7. データ型の不一致・オーバーフロー
8. 保守性の問題（マジックナンバー、命名規則違反）

【チェック観点 — HMI】
9. PLC↔HMI変数バインドの整合性（存在チェック、型一致、レンジ一致）
10. 画面遷移の完全性（到達不能画面、戻れない画面、異常時遷移）
11. 操作安全性（危険操作の確認UI、非常停止の全画面アクセス、権限設定）
12. アラーム網羅性（PLCエラーフラグとHMIアラームの対応漏れ）
13. 表示/UXの問題（スクリーンショット提供時のみ）
14. データログ設定の妥当性

【出力ルール】
- 結果は指定のJSON形式で出力
- 各issueに domain フィールド（"plc" / "hmi" / "hmi-plc-cross"）を付与
- 画面遷移図を screenTransitionDiagram フィールドに Mermaid 形式で出力
- PLC↔HMI クロスリファレンスサマリーを hmiAnalysis フィールドに出力
- 推測や仮定がある場合は必ず明記
- 問題がない場合は「問題なし」と明記（無理に問題を作らない）`;

// PLCプログラム生成用システムプロンプト
const GENERATE_PROGRAM_SYSTEM_PROMPT = `あなたはオムロン Sysmac Studio（NJ/NXシリーズ）専門のPLCプログラミングエキスパートです。
15年以上の制御設計経験を持ち、自動車・半導体・食品業界の生産設備向けPLCプログラムを多数開発してきました。
Structured Text（ST）言語とラダーダイアグラム（LD）の両方に精通しています。

【遵守規格】
- IEC 61131-3（国際規格）および JIS B 3503（日本産業規格）に厳密に準拠すること
- グローバルで通用する標準的なプログラミング作法を遵守すること

【設計原則】
- 基本回路の徹底：自己保持回路、インターロック回路、フリップフロップ回路をベースに構築
- ファンクション（FUN）およびファンクションブロック（FB）を適切に定義し、処理を単位ごとに分割
- 汎用性の高い処理は再利用可能な「オリジナルファンクションブロック」として設計
- 第三者が現場でモニタリングした際に直感的に動作の流れが把握できるシンプルなロジック構造
- 安全回路（非常停止、インターロック）を最優先で設計

【命名規則（IEC準拠）】
- グローバル変数: g_で始める（例: g_bSystemRun）
- 入力: i_で始める（例: i_bStartPB）
- 出力: o_で始める（例: o_bMotorRun）
- 内部: m_で始める（例: m_bStep01）
- タイマー: t_で始める（例: t_tonTimeout）
- カウンター: c_で始める（例: c_ctuParts）
- データ型プレフィックス: b=BOOL, w=WORD, d=DINT, r=REAL, s=STRING, a=ARRAY

【ST言語生成ルール】
- 完全にコンパイル可能なSTコードを生成する
- ヘッダーコメントブロック（プログラム名、概要、IEC規格準拠、作成者、日付、バージョン）を含める
- セクションごとにコメントで説明を付ける
- 複雑なロジックにはインラインコメントを付ける
- オムロンNJ/NXシリーズの正しい構文を使用する
- FB定義がある場合は個別に記述する

【LD（ラダー）生成ルール】
- ラング単位で説明を記述する
- 接点・コイルの説明を付ける
- 変数テーブルを含める
- 各ラングのASCIIアート表現を含める
- 自己保持回路・インターロック回路を基本パターンとして使用

【フローチャート生成ルール — 最重要】
- フローチャートは産業用PLC設計書の品質で作成すること
- 上から下への整然とした流れを徹底（矢印は基本的に下向き）
- 条件分岐（decision）は菱形で表現し、「はい」は下へ、「いいえ/待ち」は右へ
- サブプロセスは二重枠で表現
- 各ステップにはデバイスID（例: [X101], [Y501]）を付与
- 並列処理は明確に2列に分けて描画
- 矢印が交差しない構成にすること

【共通ルール】
- 安全上の考慮事項を必ず含める
- エラーハンドリングの提案を含める
- 推奨テスト手順を含める
- 出力は指定のJSON形式で返す`;

// プログラム解析用システムプロンプト
const PROGRAM_ANALYSIS_SYSTEM_PROMPT = `あなたはオムロン Sysmac Studio（NJ/NXシリーズ）専門のPLCプログラム解析エンジニアです。
プログラムのバグを検出するのではなく、プログラムの動作内容を第三者が理解できるように詳細に解説することが目的です。

【解析ルール】
1. プログラム全体の概要を最初に説明する
2. プログラムをセクション（機能単位）に分割して解説する
3. 各セクションについて以下を出力する：
   - セクション名と概要
   - 詳細な動作説明（日本語で丁寧に）
   - フローチャート（flowchartSteps形式、産業用設計書品質）
   - 主要変数の一覧と役割
   - 使用されている設計パターン（自己保持、インターロック等）
4. 現場のエンジニアが読んで即座に理解できる平易な日本語で記述する
5. IEC 61131-3の用語を正しく使用する

【フローチャート生成ルール】
- 各セクションのflowchartStepsは上から下への整然とした流れ
- type: "start", "end", "process", "decision", "subprocess" を使用
- 条件分岐のbranchYes（下方向）とbranchNo（右方向ループバック）を明記
- 各ステップにdeviceIdを付与してPLCアドレスとの対応を明確にする`;

// 総合診断用システムプロンプト
const COMPREHENSIVE_DIAGNOSIS_SYSTEM_PROMPT = `あなたはオムロン PLC + HMI の総合診断エキスパートです。
PLCプロジェクトデータと現場で撮影したエラー画面のスクリーンショットの両方を受け取り、総合的に何が起きているか診断します。

【診断プロセス】
1. スクリーンショットの読み取り: エラー表示、アラーム、状態表示、エラーコード、異常ランプ等をすべて抽出する
2. プログラムとの照合: 抽出したエラーに関連するプログラム箇所（変数、ロジック、条件分岐）を特定する
3. 原因の推定: 可能性の高い順に原因を列挙する（高/中/低）
4. 対策の提案: 優先度付きで具体的な対策を提示する（コード修正例を含む）

【重要ルール】
- スクリーンショットから読み取れる情報は可能な限り詳細に記述する
- エラーコードが見える場合は必ず記録する
- プロジェクトデータに該当箇所がない場合もその旨を明記する
- 推測がある場合は「推定」と明記する
- 対策は具体的に（「確認してください」だけで終わらせない）
- 安全に関わる問題は最優先（priority: 1）にする`;

const TROUBLESHOOT_SYSTEM_PROMPT = `あなたはオムロン PLC + HMI のトラブルシューティング専門家です。
現場での対応経験が豊富で、プログラム・HMI・電気・機械の全方面から原因を切り分けできます。

【回答ルール】
1. まず現象の整理と確認すべき前提条件を述べる
2. 原因候補を可能性の高い順に最大5つ列挙（高/中/低）
3. 各候補に対して確認手順と対策案を提示
4. HMI固有の問題も考慮する
5. プログラム以外の原因（配線、センサ故障、機械的問題）も必ず言及
6. 情報不足の場合は何を確認すべきか質問を返す`;

export class ClaudeService {
  private genAI: GoogleGenerativeAI;

  constructor(apiKey: string) {
    this.genAI = new GoogleGenerativeAI(apiKey);
  }

  // バグ分析
  async analyzeBugs(project: Smc2Project): Promise<any> {
    const context = this.buildProjectContext(project);

    const model = this.genAI.getGenerativeModel({
      model: MODEL,
      systemInstruction: BUG_ANALYSIS_SYSTEM_PROMPT,
    });

    const prompt = `以下のPLC + HMIプロジェクトを分析し、バグ・潜在的問題を検出してください。

${context}

以下のJSON形式で結果を出力してください:
{
  "projectSummary": {
    "controller": "コントローラ型番",
    "programCount": 数値,
    "variableCount": 数値,
    "axisCount": 数値,
    "taskCount": 数値,
    "hmiScreenCount": 数値,
    "hmiAlarmCount": 数値,
    "sourceTypes": ["smc2"],
    "analysisConfidence": "high"
  },
  "issues": [
    {
      "id": "ISS-001",
      "severity": "critical|warning|info",
      "category": "カテゴリ名",
      "domain": "plc|hmi|hmi-plc-cross",
      "location": "場所",
      "variable": "変数名",
      "description": "問題の説明",
      "suggestion": "改善提案",
      "relatedVariables": ["変数1"],
      "relatedScreens": ["画面名"],
      "reference": "参照規格"
    }
  ],
  "hmiAnalysis": {
    "screenTransitionDiagram": "graph TD\\n  A[画面A] --> B[画面B]",
    "crossReference": {
      "plcVariablesUsedInHmi": 数値,
      "plcVariablesNotInHmi": 数値,
      "hmiVariablesNotInPlc": 数値,
      "unmatchedTypes": 数値
    },
    "alarmCoverage": {
      "plcErrorFlags": 数値,
      "hmiAlarmsDefined": 数値,
      "uncoveredErrors": ["変数名"]
    }
  },
  "statistics": {
    "critical": 数値,
    "warning": 数値,
    "info": 数値,
    "byDomain": {
      "plc": {"critical": 0, "warning": 0, "info": 0},
      "hmi": {"critical": 0, "warning": 0, "info": 0},
      "hmi-plc-cross": {"critical": 0, "warning": 0, "info": 0}
    }
  }
}

JSONのみ出力してください。`;

    const result = await model.generateContent(prompt);
    const text = result.response.text();

    try {
      let cleaned = text.replace(/^```json\s*/i, '').replace(/\s*```\s*$/i, '');
      const jsonMatch = cleaned.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        let jsonStr = jsonMatch[0];
        jsonStr = jsonStr.replace(/\\([^"\\\/bfnrtu])/g, '\\\\$1');
        return JSON.parse(jsonStr);
      }
    } catch (err) {
      console.error('Gemini API レスポンスのJSONパース失敗:', err);
    }

    return {
      projectSummary: {
        controller: project.projectInfo.controller,
        programCount: project.programs.length,
        variableCount: project.variables.length,
        axisCount: project.axes.length,
        taskCount: project.tasks.length,
        hmiScreenCount: project.hmi.screens.length,
        hmiAlarmCount: project.hmi.alarms.length,
        sourceTypes: ['smc2'],
        analysisConfidence: 'low',
      },
      issues: [],
      statistics: { critical: 0, warning: 0, info: 0, byDomain: {} },
    };
  }

  // プログラム内容解析（バグ検出ではなく、プログラムの動作説明）
  async analyzeProgram(project: Smc2Project): Promise<any> {
    const context = this.buildProjectContext(project);

    const model = this.genAI.getGenerativeModel({
      model: MODEL,
      systemInstruction: PROGRAM_ANALYSIS_SYSTEM_PROMPT,
    });

    const prompt = `以下のPLCプロジェクトのプログラム内容を解析し、動作を詳細に解説してください。

${context}

以下のJSON形式で結果を出力してください:
{
  "overview": "プログラム全体の概要説明",
  "sections": [
    {
      "name": "セクション名",
      "language": "ST|LD",
      "description": "セクションの概要（1-2行）",
      "explanation": "詳細な動作説明（複数段落可）",
      "flowchartSteps": [
        { "type": "start", "label": "開始" },
        { "type": "decision", "label": "条件", "deviceId": "X001", "branchYes": "ON", "branchNo": "OFF" },
        { "type": "process", "label": "動作", "deviceId": "Y001" },
        { "type": "end", "label": "終了" }
      ],
      "keyVariables": [
        { "name": "変数名", "type": "BOOL", "description": "用途" }
      ],
      "designPatterns": ["自己保持回路", "インターロック"]
    }
  ]
}

JSONのみ出力してください。`;

    const result = await model.generateContent(prompt);
    const text = result.response.text();

    try {
      let cleaned = text.replace(/^```json\s*/i, '').replace(/\s*```\s*$/i, '');
      const jsonMatch = cleaned.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        let jsonStr = jsonMatch[0];
        jsonStr = jsonStr.replace(/\\([^"\\\/bfnrtu])/g, '\\\\$1');
        return JSON.parse(jsonStr);
      }
    } catch (err) {
      console.error('Gemini API レスポンスのJSONパース失敗（プログラム解析）:', err);
    }

    return {
      overview: 'プログラム解析結果の取得に失敗しました。',
      sections: [],
    };
  }

  // トラブルシュート
  async troubleshoot(
    message: string,
    project: Smc2Project | null,
    history: { role: 'user' | 'assistant'; content: string }[],
    images?: string[],
  ): Promise<string> {
    const model = this.genAI.getGenerativeModel({
      model: MODEL,
      systemInstruction: TROUBLESHOOT_SYSTEM_PROMPT,
    });

    // 会話履歴を構築
    const chatHistory: { role: 'user' | 'model'; parts: { text: string }[] }[] = [];

    // プロジェクトコンテキスト（常に会話の先頭に注入）
    if (project) {
      const context = this.buildProjectContext(project);
      chatHistory.push({
        role: 'user',
        parts: [{ text: `以下のPLCプロジェクトデータを参考にトラブルシューティングしてください:\n\n${context}` }],
      });
      chatHistory.push({
        role: 'model',
        parts: [{ text: 'プロジェクトデータを確認しました。不具合の現象を教えてください。' }],
      });
    }

    // 過去の会話
    for (const msg of history) {
      chatHistory.push({
        role: msg.role === 'assistant' ? 'model' : 'user',
        parts: [{ text: msg.content }],
      });
    }

    const chat = model.startChat({ history: chatHistory });

    // 画像付きメッセージ対応
    const parts: any[] = [];
    if (images) {
      for (const img of images) {
        const base64Match = img.match(/^data:image\/(png|jpeg|jpg);base64,(.+)$/);
        if (base64Match) {
          parts.push({
            inlineData: {
              mimeType: base64Match[1] === 'jpg' ? 'image/jpeg' : `image/${base64Match[1]}`,
              data: base64Match[2],
            },
          });
        }
      }
    }
    parts.push({ text: message });

    const result = await chat.sendMessage(parts);
    return result.response.text() || '応答を生成できませんでした。';
  }

  // PLCプログラム生成
  async generateProgram(
    description: string,
    language: 'ST' | 'LD',
    controllerType: string = 'NX102',
  ): Promise<any> {
    const model = this.genAI.getGenerativeModel({
      model: MODEL,
      systemInstruction: GENERATE_PROGRAM_SYSTEM_PROMPT,
    });

    const languageInstruction =
      language === 'ST'
        ? `ST（Structured Text）言語で完全にコンパイル可能なプログラムを生成してください。
ヘッダーコメントブロック、セクションコメント、インラインコメント、変数宣言コメントを含めてください。
オムロンNJ/NXシリーズの正しい構文を使用してください。`
        : `LD（ラダーダイアグラム）のプログラムを生成してください。
ラング単位の説明、接点・コイルの記述、変数テーブルを含めてください。

【重要】以下の3つのフィールドは必須です。必ず出力してください:
1. "ladderRungs" — 構造化ラダーデータ（配列形式、各ラングにelements配列とcoilオブジェクト）
2. "flowchartSteps" — 構造化フローチャートデータ（配列形式、各ステップにtype/label/deviceId等）
3. "flowchart" — Mermaid形式のフローチャート（graph TD形式、日本語ラベル）— 後方互換用
これらのフィールドが欠落したJSONは無効です。必ずすべてを含めてください。`;

    const ldExtraFields = language === 'LD' ? `,
  "ladderRungs": [
    {
      "number": 1,
      "comment": "// ラングの説明コメント",
      "elements": [
        { "type": "NO", "variable": "変数名", "label": "日本語ラベル" },
        { "type": "NC", "variable": "変数名", "label": "日本語ラベル" }
      ],
      "coil": { "type": "OUT", "variable": "変数名", "label": "日本語ラベル" }
    }
  ],
  "flowchartSteps": [
    { "type": "start", "label": "自動運転開始" },
    { "type": "decision", "label": "初期条件確認", "branchYes": "条件OK", "branchNo": "条件待ち" },
    { "type": "process", "label": "動作内容", "deviceId": "Y501" },
    { "type": "decision", "label": "完了確認", "deviceId": "X101", "branchYes": "完了", "branchNo": "動作中" },
    { "type": "subprocess", "label": "サブプロセス名" },
    { "type": "end", "label": "完了" }
  ],
  "flowchart": "graph TD\\n  A[開始] --> B{条件?}\\n  ..."` : '';

    const ldElementNote = language === 'LD' ? `

【ladderRungs の elements.type】
- "NO": A接点（ノーマルオープン）
- "NC": B接点（ノーマルクローズ）
- "TIMER": タイマー接点（valueにプリセット値を設定、例: "T#3s"）
- "COUNTER": カウンタ接点（valueにプリセット値を設定、例: "10"）
- "FB": ファンクションブロック
- "COMPARE": 比較命令（valueに比較式を設定）

【ladderRungs の coil.type】
- "OUT": 通常出力コイル
- "SET": セットコイル（自己保持）
- "RESET": リセットコイル
- "TIMER": タイマー出力
- "COUNTER": カウンタ出力
- "FB_CALL": ファンクションブロック呼出

【flowchartSteps — 構造化フローチャート（必須）】
- type: "start"（楕円）, "end"（楕円）, "process"（四角）, "decision"（菱形）, "subprocess"（二重枠）
- label: ノードに表示するテキスト（日本語）
- deviceId: デバイスID（例: "X101", "Y501"）— process/decision に付与
- branchYes: decision の「はい」ラベル（下方向に進む）
- branchNo: decision の「いいえ/待ち」ラベル（ループまたは右分岐）
- description: 追加説明テキスト（省略可）

【フローチャート設計指針】
- 上から下への順序で記述（開始→条件確認→動作→完了確認→...→終了）
- decisionのbranchNoは「待ち」パターン（条件成立まで待機するループ）として表現
- 並列処理がある場合は type: "parallel" と branches フィールドを使用
- 各ステップにdeviceIdを付けてPLCアドレスとの対応を明確にする` : '';

    const prompt = `以下の要件に基づいて、オムロン ${controllerType} コントローラ向けのPLCプログラムを生成してください。

【要件】
${description}

【言語】
${languageInstruction}
${ldElementNote}

以下のJSON形式で結果を出力してください:
{
  "code": "生成されたプログラムコード全文（テキスト形式のラダー図説明またはSTコード）",
  "language": "${language}",
  "explanation": "プログラムの全体説明（日本語）",
  "variables": [
    {
      "name": "変数名",
      "type": "データ型",
      "description": "用途説明",
      "initialValue": "初期値"
    }
  ],
  "safetyNotes": [
    "安全上の考慮事項1",
    "安全上の考慮事項2"
  ],
  "testProcedures": [
    "テスト手順1",
    "テスト手順2"
  ]${ldExtraFields}
}

JSONのみ出力してください。`;

    const result = await model.generateContent(prompt);
    const text = result.response.text();

    try {
      // ```json ... ``` ラッパーを除去
      let cleaned = text.replace(/^```json\s*/i, '').replace(/\s*```\s*$/i, '');
      const jsonMatch = cleaned.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        let jsonStr = jsonMatch[0];
        // Geminiが生成する不正なエスケープシーケンスを修復
        // \* \/ \# 等のJSON無効エスケープを修正
        jsonStr = jsonStr.replace(/\\([^"\\\/bfnrtu])/g, '\\\\$1');
        const parsed = JSON.parse(jsonStr);
        // LD言語の場合、ladderRungs と flowchart がレスポンスに含まれているか確認
        if (language === 'LD') {
          console.log('LD生成結果チェック — ladderRungs:', !!parsed.ladderRungs, 'flowchartSteps:', !!parsed.flowchartSteps, 'flowchart:', !!parsed.flowchart);
        }
        return parsed;
      }
    } catch (err) {
      console.error('Gemini API レスポンスのJSONパース失敗（プログラム生成）:', err);
      console.error('レスポンステキスト（先頭500文字）:', text.substring(0, 500));
      // 2回目の試行: より積極的な修復
      try {
        let cleaned = text.replace(/^```json\s*/i, '').replace(/\s*```\s*$/i, '');
        const jsonMatch = cleaned.match(/\{[\s\S]*\}/);
        if (jsonMatch) {
          // すべての不正バックスラッシュをダブルバックスラッシュに
          let jsonStr = jsonMatch[0];
          // 文字列値内の改行をエスケープ
          jsonStr = jsonStr.replace(/(?<=: "(?:[^"\\]|\\.)*)\\(?!["\\/bfnrtu])/g, '\\\\');
          const parsed = JSON.parse(jsonStr);
          if (language === 'LD') {
            console.log('LD生成結果チェック（2回目試行）— ladderRungs:', !!parsed.ladderRungs, 'flowchart:', !!parsed.flowchart);
          }
          return parsed;
        }
      } catch (err2) {
        console.error('2回目のJSONパースも失敗:', err2);
      }
    }

    // パース失敗時のフォールバック
    return {
      code: text,
      language,
      explanation: 'JSONパースに失敗したため、生テキストを返しています。',
      variables: [],
      safetyNotes: [],
      testProcedures: [],
    };
  }

  // 総合診断（プロジェクト + エラースクリーンショット）
  async comprehensiveDiagnosis(project: Smc2Project, images: string[]): Promise<any> {
    const context = this.buildProjectContext(project);

    const model = this.genAI.getGenerativeModel({
      model: MODEL,
      systemInstruction: COMPREHENSIVE_DIAGNOSIS_SYSTEM_PROMPT,
    });

    // parts配列：画像 → テキストの順
    const parts: any[] = [];

    // スクリーンショット画像をinlineDataで追加
    for (let i = 0; i < images.length; i++) {
      const img = images[i];
      const base64Match = img.match(/^data:image\/(png|jpeg|jpg|webp);base64,(.+)$/);
      if (base64Match) {
        parts.push({
          inlineData: {
            mimeType: base64Match[1] === 'jpg' ? 'image/jpeg' : `image/${base64Match[1]}`,
            data: base64Match[2],
          },
        });
      }
    }

    // テキストプロンプト
    parts.push({
      text: `以下のPLCプロジェクトデータと、添付された${images.length}枚のエラー画面スクリーンショットを総合的に分析してください。

## PLCプロジェクトデータ
${context}

## 指示
1. 各スクリーンショットからエラー表示・アラーム・異常状態を読み取ってください
2. プロジェクトのプログラムと照合し、原因となる箇所を特定してください
3. 優先度付きの対策案を提示してください

以下のJSON形式で結果を出力してください:
{
  "summary": "総合所見（全体的に何が起きているかの説明）",
  "phenomena": [
    {
      "id": "PHN-001",
      "screenshotIndex": 0,
      "errorType": "エラー種別（通信エラー、軸異常、インターロック、アラーム等）",
      "description": "スクリーンショットから読み取った内容の詳細説明",
      "errorCode": "エラーコード（読み取れた場合）",
      "affectedDevice": "影響デバイス（モータ、センサ等）"
    }
  ],
  "rootCauseAnalysis": [
    {
      "id": "RCA-001",
      "relatedPhenomena": ["PHN-001"],
      "location": "プログラム上の該当箇所（プログラム名、セクション、行番号等）",
      "description": "原因の詳細説明",
      "probability": "high|medium|low",
      "relatedVariables": ["変数名1", "変数名2"]
    }
  ],
  "countermeasures": [
    {
      "id": "FIX-001",
      "priority": 1,
      "relatedCauses": ["RCA-001"],
      "title": "対策タイトル",
      "description": "対策の説明",
      "implementation": "具体的な実装手順・修正内容",
      "risk": "対策実施時のリスク・注意点"
    }
  ]
}

priority: 1=最優先（安全/停止に関わる）, 2=推奨（品質・安定性）, 3=余裕があれば（改善）

JSONのみ出力してください。`,
    });

    const result = await model.generateContent(parts);
    const text = result.response.text();

    try {
      let cleaned = text.replace(/^```json\s*/i, '').replace(/\s*```\s*$/i, '');
      const jsonMatch = cleaned.match(/\{[\s\S]*\}/);
      if (jsonMatch) {
        let jsonStr = jsonMatch[0];
        jsonStr = jsonStr.replace(/\\([^"\\\/bfnrtu])/g, '\\\\$1');
        return JSON.parse(jsonStr);
      }
    } catch (err) {
      console.error('Gemini API レスポンスのJSONパース失敗（総合診断）:', err);
    }

    // フォールバック
    return {
      summary: text || '診断結果の取得に失敗しました。',
      phenomena: [],
      rootCauseAnalysis: [],
      countermeasures: [],
    };
  }

  // プロジェクトデータをテキスト化
  private buildProjectContext(project: Smc2Project): string {
    const sections: string[] = [];

    sections.push(`## プロジェクト情報
- コントローラ: ${project.projectInfo.controller}
- バージョン: ${project.projectInfo.version}
- HMI含有: ${project.projectInfo.hasHmi ? 'はい' : 'いいえ'}`);

    // プログラム一覧
    if (project.programs.length > 0) {
      sections.push(`## プログラム一覧 (${project.programs.length}個)`);
      for (const p of project.programs) {
        const source = p.source.length > 3000 ? p.source.substring(0, 3000) + '\n... (省略)' : p.source;
        sections.push(`### ${p.name} (${p.language})\n\`\`\`\n${source}\n\`\`\``);
      }
    }

    // グローバル変数（先頭100件）
    const globalVars = project.variables.filter((v) => v.scope === 'global');
    if (globalVars.length > 0) {
      sections.push(`## グローバル変数 (${globalVars.length}個、先頭100件表示)`);
      const displayVars = globalVars.slice(0, 100);
      sections.push('| 名前 | データ型 | アドレス | コメント | HMI使用 |');
      sections.push('|------|---------|---------|---------|---------|');
      for (const v of displayVars) {
        sections.push(`| ${v.name} | ${v.dataType} | ${v.address || ''} | ${v.comment || ''} | ${v.usedInHmi ? 'O' : ''} |`);
      }
    }

    // HMI画面
    if (project.hmi.screens.length > 0) {
      sections.push(`## HMI画面 (${project.hmi.screens.length}画面)`);
      for (const s of project.hmi.screens) {
        const elements = s.elements.map((e) => `  - ${e.type}: ${e.name || e.id}${e.variable ? ` [${e.variable}]` : ''}${e.action ? ` → ${e.action.type}` : ''}`);
        sections.push(`### ${s.name} (No.${s.screenNumber})\n要素数: ${s.elements.length}\n${elements.join('\n')}`);
      }
    }

    // 画面遷移
    if (project.hmi.screenTransitions.length > 0) {
      sections.push(`## 画面遷移`);
      for (const t of project.hmi.screenTransitions) {
        sections.push(`- ${t.fromScreen} → ${t.toScreen} (${t.trigger})`);
      }
    }

    return sections.join('\n\n');
  }
}
