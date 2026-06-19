import { defineConfig } from 'vite'
import AdmZip from 'adm-zip'
import react from '@vitejs/plugin-react'

export default defineConfig({
  base: '/react-ui/',
  plugins: [react(), {
      name: 'zip-dist',
      closeBundle() {
        const zip = new AdmZip()
        zip.addLocalFolder('dist')
        zip.writeZip('dist/catalog.zip')
      }
  }],
  server: {
    proxy: {
      '/stock': 'http://localhost:4004',
      '/odata': 'http://localhost:4004'
    }
  }
})
