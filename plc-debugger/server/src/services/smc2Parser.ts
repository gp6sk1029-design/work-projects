import JSZip from 'jszip';
import { XMLParser } from 'fast-xml-parser';

// === 型定義 ===
export interface Smc2Project {
  projectInfo: {
    name: string;
    controller: string;
    version: string;
    hasHmi: boolean;
  };
  programs: PlcProgram[];
  variables: PlcVariable[];
  tasks: { name: string; type: string; period?: string; priority: number }[];
  axes: { name: string; axisNumber: number; mcGroup: string }[];
  ethercat: { slaves: { name: string; vendor: string; nodeAddress: number }[] };
  io: { name: string; address: string; direction: string; dataType: string }[];
  hmi: {
    screens: HmiScreen[];
    alarms: HmiAlarm[];
    dataLogs: any[];
    globalObjects: any[];
    screenTransitions: HmiScreenTransition[];
    userAccounts: HmiUserAccount[];
  };
}

export interface PlcProgram {
  name: string;
  language: 'ST' | 'LD' | 'FB';
  source: string;
  taskAssignment: string;
}

export interface PlcVariable {
  name: string;
  dataType: string;
  scope: 'global' | 'local';
  initialValue?: string;
  comment?: string;
  address?: string;
  usedInHmi: boolean;
}

export interface HmiScreen {
  id: string;
  name: string;
  screenNumber: number;
  elements: HmiElement[];
  scripts?: string[];
}

export interface HmiElement {
  type: string;
  id: string;
  name?: string;
  variable?: string;
  action?: {
    type: string;
    targetVariable?: string;
    targetScreen?: string;
    script?: string;
  };
  position: { x: number; y: number; width: number; height: number };
}

export interface HmiAlarm {
  id: string;
  group: string;
  message: string;
  condition: string;
  severity: string;
  acknowledgeRequired: boolean;
  autoReset: boolean;
  plcVariable: string;
}

export interface HmiScreenTransition {
  fromScreen: string;
  toScreen: string;
  trigger: string;
}

export interface HmiUserAccount {
  level: number;
  name: string;
  description: string;
}

// === パーサー ===
const xmlParser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: '@_',
  textNodeName: '#text',
});

// ファイルの種類を判別
function classifyFile(content: string): string {
  const trimmed = content.trim();

  // JSON形式のHMI画面定義
  if (trimmed.startsWith('{') && trimmed.includes('PageElementIdentifier')) {
    return 'hmi-screen';
  }

  // JSON形式のラダー図（行ごとのJSON）
  if (trimmed.startsWith('{') && trimmed.includes('"CLs"')) {
    return 'ladder-json';
  }

  // SLWD形式のローカル変数定義
  if (trimmed.startsWith('[SLWD')) {
    return 'slwd-variables';
  }

  // XML形式
  if (trimmed.startsWith('<?xml') || trimmed.startsWith('<')) {
    // XMLパースしてルートタグで判別
    try {
      const parsed = xmlParser.parse(trimmed);
      if (parsed.Variables) return 'variables-xml';
      if (parsed.CodeEditorModel) return 'hmi-script';
      if (parsed.SecuritySettingsModel) return 'security-settings';
      if (parsed.ResourceReferences) return 'resource-references';
      if (parsed.CpuRack) return 'cpu-rack';
      if (parsed.EipConnectionSetting) return 'eip-settings';
      if (parsed.AssociatedProgramModel) return 'program-assignment';
      if (parsed.data) {
        const data = parsed.data;
        if (data.ModelName) return 'controller-info';
        if (data.SectionUsingMCOrMcr !== undefined) return 'plc-program-xml';
        if (data.Build) return 'build-info';
        if (data['Db.Section.ServiceSetting']) return 'service-settings';
        if (data.ControllerId) return 'controller-info';
        return 'data-xml';
      }
    } catch {
      // XMLパース失敗
    }
  }

  return 'unknown';
}

// ラダーJSONからプログラム情報を抽出
function parseLadderProgram(content: string, programName: string): PlcProgram {
  const lines = content.trim().split('\n');
  const sourceLines: string[] = [];

  for (const line of lines) {
    try {
      const rung = JSON.parse(line);
      const elements: string[] = [];

      if (rung.CMT) {
        elements.push(`// ${rung.CMT}`);
      }

      if (rung.CLs) {
        for (const cl of rung.CLs) {
          switch (cl.__type) {
            case 'LD':
              elements.push(`LD${cl.Not ? 'N' : ''} ${cl.Var}`);
              break;
            case 'ST':
              elements.push(`OUT${cl.S ? '(S)' : cl.R ? '(R)' : ''} ${cl.Var}`);
              break;
            case 'F':
              elements.push(`FUNC ${cl.Name}(${(cl.In || []).filter((i: any) => i.Var).map((i: any) => `${i.Arg}:=${i.Var}`).join(', ')})`);
              break;
            case 'FB':
              elements.push(`FB ${cl.Name} [${cl.Var || ''}](${(cl.In || []).filter((i: any) => i.Var).map((i: any) => `${i.Arg}:=${i.Var}`).join(', ')})`);
              break;
            case 'IST':
              elements.push(`INLINE_ST {\n${cl.TXT}\n}`);
              break;
          }
        }
      }

      sourceLines.push(elements.join('\n'));
    } catch {
      // JSONパース失敗行はスキップ
    }
  }

  return {
    name: programName,
    language: 'LD',
    source: sourceLines.join('\n---\n'),
    taskAssignment: '',
  };
}

// PLCプログラムXMLからラダー情報を抽出
function parsePlcProgramXml(content: string): { variables: PlcVariable[]; programName: string } {
  const parsed = xmlParser.parse(content);
  const data = parsed.data;
  const variables: PlcVariable[] = [];
  let programName = data['@_ProgramBlockName'] || '';

  // CxilVariable（一時変数）の抽出
  const cxilVars = Array.isArray(data.CxilVariable) ? data.CxilVariable : data.CxilVariable ? [data.CxilVariable] : [];
  for (const v of cxilVars) {
    if (v['@_CxilVariableType'] === 'FunctionResult' || v['@_CxilVariableType'] === 'PowerFlow') continue;
    variables.push({
      name: v['@_Name'] || '',
      dataType: v['@_DataType'] || '',
      scope: 'local',
      usedInHmi: false,
    });
  }

  // ProgramBlockName取得を試みる
  if (!programName) {
    // XMLの属性から探す
    const match = content.match(/ProgramBlockName="([^"]+)"/);
    if (match) programName = match[1];
  }

  return { variables, programName };
}

// グローバル変数XMLのパース
function parseVariablesXml(content: string): PlcVariable[] {
  const parsed = xmlParser.parse(content);
  const variables: PlcVariable[] = [];

  const varGroups = parsed.Variables?.VariableGroup;
  const groups = Array.isArray(varGroups) ? varGroups : varGroups ? [varGroups] : [];

  for (const group of groups) {
    const vars = Array.isArray(group.Variable) ? group.Variable : group.Variable ? [group.Variable] : [];
    for (const v of vars) {
      variables.push({
        name: v['@_Name'] || '',
        dataType: v['@_DataTypeName'] || '',
        scope: 'global',
        initialValue: v['@_InitialValue'] || undefined,
        comment: v['@_Comment'] || undefined,
        address: v['@_Address'] || undefined,
        usedInHmi: false,
      });
    }
  }

  return variables;
}

// HMI画面JSONのパース
function parseHmiScreen(content: string): HmiScreen | null {
  try {
    const page = JSON.parse(content);
    if (!page.PageElementIdentifier) return null;

    const elements: HmiElement[] = [];
    const scripts: string[] = [];

    // ChildControlsから要素を抽出
    if (page.ChildControls) {
      for (const ctrl of page.ChildControls) {
        const el = parseHmiControl(ctrl);
        if (el) elements.push(el);

        // ボタンのイベントからスクリプト情報を抽出
        if (ctrl.Events) {
          for (const evt of ctrl.Events) {
            if (evt.Actions) {
              for (const action of evt.Actions) {
                if (action.SubroutineName) {
                  scripts.push(action.SubroutineName);
                }
              }
            }
          }
        }
      }
    }

    return {
      id: page.PageElementIdentifier,
      name: page.Name || `Screen_${page.PageIndex}`,
      screenNumber: page.PageIndex || 0,
      elements,
      scripts: scripts.length > 0 ? scripts : undefined,
    };
  } catch {
    return null;
  }
}

// HMIコントロールのパース
function parseHmiControl(ctrl: any): HmiElement | null {
  if (!ctrl.ResourceKey) return null;

  const resourceKey = ctrl.ResourceKey as string;
  let type = 'unknown';

  if (resourceKey.includes('Button')) type = 'button';
  else if (resourceKey.includes('TextBox')) type = 'stringDisplay';
  else if (resourceKey.includes('NumericBox') || resourceKey.includes('NumericUpDown')) type = 'numericDisplay';
  else if (resourceKey.includes('ImageBox')) type = 'image';
  else if (resourceKey.includes('Lamp') || resourceKey.includes('Indicator')) type = 'lamp';
  else if (resourceKey.includes('ToggleSwitch')) type = 'toggleSwitch';
  else if (resourceKey.includes('Meter') || resourceKey.includes('Gauge')) type = 'meter';
  else if (resourceKey.includes('Graph') || resourceKey.includes('Chart')) type = 'graph';
  else if (resourceKey.includes('Shape') || resourceKey.includes('Rectangle') || resourceKey.includes('Line')) type = 'shape';
  else if (resourceKey.includes('Page')) type = 'container';
  else type = resourceKey.split('.').pop() || 'unknown';

  // アクション抽出
  let action: HmiElement['action'] | undefined;
  if (ctrl.Events) {
    for (const evt of ctrl.Events) {
      if (evt.Actions) {
        for (const act of evt.Actions) {
          if (act.ResourceKey?.includes('ScreenChange') || act.ResourceKey?.includes('ChangePage')) {
            action = { type: 'screenChange', targetScreen: act.TargetPageName || act.PageName || '' };
          } else if (act.ResourceKey?.includes('CallSubroutine')) {
            action = { type: 'executeScript', script: act.SubroutineName || '' };
          } else if (act.ResourceKey?.includes('WriteVariable') || act.ResourceKey?.includes('SetBit')) {
            action = { type: 'writeValue', targetVariable: act.VariableName || '' };
          }
        }
      }
    }
  }

  return {
    type,
    id: ctrl.PageElementIdentifier || '',
    name: ctrl.Name || undefined,
    variable: ctrl.Variable || ctrl.VariableName || undefined,
    action,
    position: {
      x: ctrl.Left || 0,
      y: ctrl.Top || 0,
      width: ctrl.Width || 0,
      height: ctrl.Height || 0,
    },
  };
}

// HMIスクリプトのパース（CodeEditorModel）
function parseHmiScript(content: string): { className: string; code: string; variables: string[] } {
  const parsed = xmlParser.parse(content);
  const model = parsed.CodeEditorModel;

  const header = model?.HiddenHeader || '';
  const classMatch = header.match(/Class\s+(\w+)/);
  const className = classMatch ? classMatch[1] : '';

  const code = model?.Text || '';

  // SerialDataから変数情報を抽出
  const variables: string[] = [];
  try {
    const serialData = model?.SerialData?.['#text'] || model?.SerialData || '';
    if (serialData && serialData.startsWith('[')) {
      const items = JSON.parse(serialData);
      for (const item of items) {
        if (item.o?.Name) {
          variables.push(item.o.Name);
        }
      }
    }
  } catch {
    // パース失敗は無視
  }

  return { className, code, variables };
}

// コントローラ情報のパース
function parseControllerInfo(content: string): { controller: string; version: string } {
  const parsed = xmlParser.parse(content);
  const data = parsed.data;

  return {
    controller: data.ModelName || data.Family || 'Unknown',
    version: `${data.MajorVersion || '?'}.${data.MinorVersion || '?'}.${data.Revision || '0'}`,
  };
}

// セキュリティ設定のパース
function parseSecuritySettings(content: string): HmiUserAccount[] {
  const accounts: HmiUserAccount[] = [];
  // 簡易パース: AccessLevelを抽出
  const levelMatches = content.matchAll(/Level\s+(\d+)/g);
  let idx = 1;
  for (const m of levelMatches) {
    accounts.push({
      level: parseInt(m[1]),
      name: `Level ${m[1]}`,
      description: '',
    });
    idx++;
  }
  return accounts;
}

// プログラム割当のパース
function parseProgramAssignment(content: string): string {
  const parsed = xmlParser.parse(content);
  return parsed.AssociatedProgramModel?.PouInstanceName || '';
}

// 画面遷移の抽出
function extractScreenTransitions(screens: HmiScreen[]): HmiScreenTransition[] {
  const transitions: HmiScreenTransition[] = [];

  for (const screen of screens) {
    for (const element of screen.elements) {
      if (element.action?.type === 'screenChange' && element.action.targetScreen) {
        transitions.push({
          fromScreen: screen.name,
          toScreen: element.action.targetScreen,
          trigger: `${element.type}: ${element.name || element.id}`,
        });
      }
    }
  }

  return transitions;
}

// SLWD形式の変数パース
function parseSlwdVariables(content: string): PlcVariable[] {
  const variables: PlcVariable[] = [];
  const lines = content.split('\n');

  for (const line of lines) {
    if (line.startsWith('++D=') || line.startsWith('+D=')) {
      const parts: Record<string, string> = {};
      const matches = line.matchAll(/(\w+)=([^\t]*)/g);
      for (const m of matches) {
        parts[m[1]] = m[2];
      }
      if (parts.N) {
        variables.push({
          name: parts.N,
          dataType: parts.D || 'UNKNOWN',
          scope: 'local',
          comment: parts.Com || undefined,
          usedInHmi: false,
        });
      }
    }
  }

  return variables;
}

// メインパーサー
export async function parseSmc2(buffer: Buffer, fileName: string): Promise<Smc2Project> {
  const zip = await JSZip.loadAsync(buffer);

  const project: Smc2Project = {
    projectInfo: {
      name: fileName.replace('.smc2', ''),
      controller: 'Unknown',
      version: '',
      hasHmi: false,
    },
    programs: [],
    variables: [],
    tasks: [],
    axes: [],
    ethercat: { slaves: [] },
    io: [],
    hmi: {
      screens: [],
      alarms: [],
      dataLogs: [],
      globalObjects: [],
      screenTransitions: [],
      userAccounts: [],
    },
  };

  const hmiVariables = new Set<string>();
  const programAssignments: Record<string, string> = {};

  // 全ファイルを処理
  for (const [path, file] of Object.entries(zip.files)) {
    if (file.dir) continue;

    const ext = path.split('.').pop()?.toLowerCase() || '';

    // BookmarkGroup, HmiBreakpointGroup, NexBreakpointGroup等はスキップ
    if (['bookmarkgroup', 'hmibreakpointgroup', 'nexbreakpointgroup', 'nexbuildresults', 'nexbuildverifiergroup', 'nextransferinformation'].includes(ext.toLowerCase())) {
      continue;
    }

    // .dat ファイル（バイナリ EtherCATスレーブ等）はスキップ
    if (ext === 'dat') {
      // XML形式の.datファイルは試みる
      try {
        const content = await file.async('text');
        if (content.trim().startsWith('<?xml')) {
          // XML形式の.datは処理可能だが、現時点ではスキップ
        }
      } catch {
        // バ��ナリファイル
      }
      continue;
    }

    // CommunicationSetting
    if (ext === 'communicationsetting') continue;

    // XMLまたはJSONファイルを処理
    if (ext === 'xml' || ext === 'json') {
      try {
        const content = await file.async('text');
        const fileType = classifyFile(content);

        switch (fileType) {
          case 'controller-info': {
            const info = parseControllerInfo(content);
            project.projectInfo.controller = info.controller;
            project.projectInfo.version = info.version;
            break;
          }

          case 'variables-xml': {
            const vars = parseVariablesXml(content);
            project.variables.push(...vars);
            break;
          }

          case 'plc-program-xml': {
            const { variables: localVars, programName } = parsePlcProgramXml(content);

            // ラダー図のJSON部分を探す
            // XMLのテキストノード内にJSON行が埋め込まれている可能性がある
            // ただし実際のファイルでは別ファ��ルとしてラダーJSONが格納される
            if (programName) {
              // プログラム名だけ記録し、ラダーJSONは別ファイルから取得
              project.programs.push({
                name: programName,
                language: 'LD',
                source: `// ラダー図プログラム: ${programName}\n// 変数数: ${localVars.length}`,
                taskAssignment: '',
              });
            }

            project.variables.push(...localVars);
            break;
          }

          case 'hmi-screen': {
            const screen = parseHmiScreen(content);
            if (screen) {
              project.hmi.screens.push(screen);
              project.projectInfo.hasHmi = true;

              // HMIで使用されている変数を収集
              for (const el of screen.elements) {
                if (el.variable) hmiVariables.add(el.variable);
                if (el.action?.targetVariable) hmiVariables.add(el.action.targetVariable);
              }
            }
            break;
          }

          case 'hmi-script': {
            const script = parseHmiScript(content);
            for (const v of script.variables) {
              hmiVariables.add(v);
            }
            break;
          }

          case 'security-settings': {
            project.hmi.userAccounts = parseSecuritySettings(content);
            break;
          }

          case 'program-assignment': {
            const pouName = parseProgramAssignment(content);
            if (pouName) {
              programAssignments[path] = pouName;
            }
            break;
          }

          case 'ladder-json': {
            // 行ごとのJSONラダー図（.xml拡張子だがJSON内容）
            // ファイル名（GUID）からプログラム名は取得不可、後でマッチ
            break;
          }

          case 'slwd-variables': {
            const slwdVars = parseSlwdVariables(content);
            project.variables.push(...slwdVars);
            break;
          }
        }
      } catch (err) {
        console.warn(`ファイルパース失敗: ${path}`, err);
      }
    }
  }

  // HMI変数マーキング
  for (const v of project.variables) {
    if (hmiVariables.has(v.name)) {
      v.usedInHmi = true;
    }
  }

  // 画面遷移の抽出
  project.hmi.screenTransitions = extractScreenTransitions(project.hmi.screens);

  // 重複変数の除去（同名はglobal優先）
  const varMap = new Map<string, PlcVariable>();
  for (const v of project.variables) {
    const existing = varMap.get(v.name);
    if (!existing || (v.scope === 'global' && existing.scope === 'local')) {
      varMap.set(v.name, v);
    }
  }
  project.variables = Array.from(varMap.values());

  return project;
}
