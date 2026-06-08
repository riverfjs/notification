import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));

// 部署:Cloudflare(根路径),前面套 Cloudflare Access 做登录。
export default defineConfig({
  base: "/",
  plugins: [react(), tailwindcss()],
  resolve: { alias: { "@": "/src" } },   // shadcn 约定的 @/ 别名
  server: { fs: { allow: [path.resolve(here, "..")] } },
});
