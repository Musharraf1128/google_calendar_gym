import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      }
    }
  },
  build: {
    // Optimize chunk splitting for better caching
    rollupOptions: {
      output: {
        manualChunks: {
          'vendor-react': ['react', 'react-dom'],
          'vendor-utils': ['axios'],
        },
      },
    },
    // Increase chunk size warning limit (default 500kb)
    chunkSizeWarningLimit: 600,
    // Enable sourcemaps for production debugging (optional)
    sourcemap: false,
    // Use esbuild for faster minification (default)
    minify: 'esbuild',
    target: 'es2015',
  },
})
