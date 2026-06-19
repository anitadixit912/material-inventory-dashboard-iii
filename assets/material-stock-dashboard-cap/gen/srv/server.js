'use strict'

const cds = require('@sap/cds')
const path = require('path')
const express = require('express')

// Serve the React UI at /react-ui/ in all environments (dev and production).
// Assets are referenced as /react-ui/assets/... in index.html so the mount
// point must be /react-ui in both environments.
cds.on('bootstrap', (app) => {
  const distPath = path.join(__dirname, 'app', 'react-ui', 'dist')
  // Serve static assets (JS, CSS, icons, etc.)
  app.use('/react-ui', express.static(distPath, { index: 'index.html' }))
  // SPA fallback — any /react-ui/* path returns index.html
  app.get('/react-ui/*splat', (_req, res) => {
    res.sendFile(path.join(distPath, 'index.html'))
  })
  // Redirect root / to /react-ui/
  app.get('/', (_req, res) => {
    res.redirect('/react-ui/')
  })
})

module.exports = cds.server
