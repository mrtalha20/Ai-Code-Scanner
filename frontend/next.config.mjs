/** @type {import('next').NextConfig} */
const nextConfig = {
  experimental: {
    typedRoutes: true,
  },
  // Add this if needed
  serverRuntimeConfig: {
    // Only available on the server side
  },
  publicRuntimeConfig: {
    // Available on both server and client
  },
};

export default nextConfig;
