import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import {
  DevDashboard,
  logsTab,
  httpLogsClient,
  phasesTab,
  httpPhasesClient,
} from '@devdash/ui'

// The runner serves this bundle at the dashboard's base_path, so the API lives
// at the same prefix — derive it from the current path (e.g. "/dev").
const base = window.location.pathname.replace(/\/+$/, '') || ''

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <DevDashboard
      branding={{ wordmark: 'devdash' }}
      tabs={[
        logsTab({ client: httpLogsClient({ baseUrl: base }) }),
        phasesTab({ client: httpPhasesClient({ baseUrl: base }) }),
      ]}
    />
  </StrictMode>,
)
