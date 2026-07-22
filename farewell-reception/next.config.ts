import type { NextConfig } from "next";
import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";

const nextConfig: NextConfig = {
  // 開発中に左下へ出る「Route/Turbopack」インジケータを非表示（受付リストへの被り防止）
  devIndicators: false,
};

// `next dev` でも Cloudflare のバインディング（D1など）を使えるようにする
initOpenNextCloudflareForDev();

export default nextConfig;
