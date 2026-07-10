/** @type {import('next').NextConfig} */
const nextConfig = {
  // Pure static export — the page has no server features; Vercel still
  // detects + badges it as Next.js and serves the exported site.
  output: "export",
};

export default nextConfig;
