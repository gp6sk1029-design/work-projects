import type { NextConfig } from "next";
import { initOpenNextCloudflareForDev } from "@opennextjs/cloudflare";

const nextConfig: NextConfig = {};

// `next dev` でも Cloudflare のバインディング（D1など）を使えるようにする
initOpenNextCloudflareForDev();

export default nextConfig;
