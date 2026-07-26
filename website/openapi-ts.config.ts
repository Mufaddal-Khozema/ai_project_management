import { defineConfig } from '@hey-api/openapi-ts';

export default defineConfig({
  input: 'openapi.json',
  output: {
    path: 'lib/api',
  },
  plugins: [
    '@hey-api/client-fetch',
    '@hey-api/sdk',
    {
      name: '@tanstack/react-query',
      mutationOptions: true,
    },
  ],
});
