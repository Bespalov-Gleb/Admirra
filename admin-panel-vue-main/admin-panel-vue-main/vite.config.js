import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'
import fs from 'node:fs'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

function resolveAdmirraOrigin() {
  const deploy = (
    process.env.VITE_ADMIRRA_DEPLOY_ENV ||
    process.env.ADMIRRA_DEPLOY_ENV ||
    'prod'
  )
    .toString()
    .toLowerCase()
  const host =
    process.env.VITE_ADMIRRA_PUBLIC_HOST ||
    (deploy === 'dev' ? 'admirra.online' : 'admirra.ru')
  return `https://${host}`
}

/** После сборки подставляет правильный origin в статичные HTML лендинга (public/admirra). */
function admirraPublicHtmlOriginPlugin() {
  const origin = resolveAdmirraOrigin()
  return {
    name: 'admirra-public-html-origin',
    apply: 'build',
    closeBundle() {
      const distAdmirra = path.resolve(__dirname, 'dist/admirra')
      if (!fs.existsSync(distAdmirra)) return
      const files = ['personal-data.html', 'agreement.html', 'user-agreement.html']
      for (const name of files) {
        const p = path.join(distAdmirra, name)
        if (!fs.existsSync(p)) continue
        let html = fs.readFileSync(p, 'utf8')
        html = html.replace(/https:\/\/admirra\.(ru|online)/g, origin)
        fs.writeFileSync(p, html)
      }
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue(), admirraPublicHtmlOriginPlugin()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    proxy: {
      '/api': {
        target: process.env.VITE_DEV_API_PROXY || 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
      '/uploads': {
        target: process.env.VITE_DEV_API_PROXY || 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
})
