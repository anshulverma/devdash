import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { DEVDASH_CONTRACT_VERSION } from '@devdash/ui'

// Placeholder host app. M1 mounts <DevDashboard tabs={[...]} /> here with a
// couple of placeholder tabs + one custom tab to exercise the plugin API.
function App() {
  return <main>devdash example host — contract v{DEVDASH_CONTRACT_VERSION}</main>
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
