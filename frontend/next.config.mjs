/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    typedRoutes: true,
  },
  serverRuntimeConfig: {
    // Only available on the server side
  },
  publicRuntimeConfig: {
    // Available on both server and client
  },
};

export default nextConfig;
