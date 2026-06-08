import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The bundle is served as static assets by the devdash standalone runner under
// the dashboard's base_path (e.g. /dev), so use relative asset URLs.
export default defineConfig({
  base: './',
  plugins: [react()],
  build: { outDir: 'dist', emptyOutDir: true },
})
