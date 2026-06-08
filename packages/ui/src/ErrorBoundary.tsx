import { Component, type ErrorInfo, type ReactNode } from 'react'

interface Props {
  /** Label of the boundary's subject (e.g. the tab), for the fallback message. */
  label: string
  children: ReactNode
}

interface State {
  error: Error | null
}

/**
 * Per-tab error boundary. One tab crashing must not blank the operator
 * dashboard — the failed tab renders a contained error panel while the shell
 * and other tabs keep working.
 */
export class TabErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  componentDidCatch(error: Error, info: ErrorInfo): void {
    // Surface to the console; hosts can wrap with their own logging.
    console.error(`[devdash] tab "${this.props.label}" crashed:`, error, info)
  }

  componentDidUpdate(prev: Props): void {
    // Reset when the boundary is reused for a different tab.
    if (prev.label !== this.props.label && this.state.error) {
      this.setState({ error: null })
    }
  }

  render(): ReactNode {
    if (this.state.error) {
      return (
        <div
          role="alert"
          style={{
            padding: '1.5rem',
            color: 'var(--devdash-color-danger)',
            fontFamily: 'var(--devdash-font-sans)',
          }}
        >
          <strong>This tab crashed.</strong>
          <div style={{ marginTop: '0.5rem', opacity: 0.8, fontSize: '0.9em' }}>
            {this.state.error.message}
          </div>
        </div>
      )
    }
    return this.props.children
  }
}
