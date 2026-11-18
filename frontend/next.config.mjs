/** @type {import('next').NextConfig} */
const nextConfig = {
  agentRules: false,
  reactStrictMode: true,
  experimental: {
    // proxy.ts buffers request bodies up to this size and silently truncates the rest.
    // Resumes are capped at 4 MB (MAX_RESUME_SIZE_BYTES), so this leaves headroom.
    proxyClientMaxBodySize: "5mb",
  },
};

export default nextConfig;
