// Cloudflare バインディングの型定義
// `npx wrangler types` で再生成できるが、最小限を手書きで用意
declare global {
  interface CloudflareEnv {
    DB: D1Database;
  }
}

export {};
