interface Props {
  code: string;
  language?: string;
}

export default function CodeBlock({ code, language = 'st' }: Props) {
  const handleCopy = () => {
    navigator.clipboard.writeText(code);
  };

  return (
    <div className="relative group">
      <div className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition">
        <button
          onClick={handleCopy}
          className="px-2 py-1 bg-dark-hover rounded text-xs text-gray-300 hover:text-white"
        >
          コピー
        </button>
      </div>
      <pre className="bg-dark-bg rounded p-4 overflow-x-auto text-sm font-mono text-gray-200">
        <code className={`language-${language}`}>{code}</code>
      </pre>
    </div>
  );
}
