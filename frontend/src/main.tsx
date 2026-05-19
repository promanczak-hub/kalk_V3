import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import axios from 'axios'
import 'ag-grid-community/styles/ag-grid.css'
import 'ag-grid-community/styles/ag-theme-quartz.css'
import './index.css'
import App from './App.tsx'
import { initSentry } from './lib/sentryInit'

// Initialise Sentry before the React tree mounts so render errors are caught.
// No-op when VITE_SENTRY_DSN is unset (i.e. local dev).
initSentry()

// Globalnie zablokuj agresywne keszowanie przeglądarek dla wszystkich zapytań GET
axios.defaults.headers.get['Cache-Control'] = 'no-cache, no-store, must-revalidate'
axios.defaults.headers.get['Pragma'] = 'no-cache'
axios.defaults.headers.get['Expires'] = '0'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </StrictMode>,
)
