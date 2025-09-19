import React from 'react'
import { logEvent } from 'firebase/analytics'
import { analytics } from '../firebase'

interface ErrorBoundaryState {
  hasError: boolean
  error?: Error
}

interface ErrorBoundaryProps {
  children: React.ReactNode
}

export class ErrorBoundary extends React.Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props)
    this.state = { hasError: false }
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      error
    }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('ErrorBoundary caught an error:', error)
    console.error('Error info:', errorInfo)
    console.error('Stack:', error.stack)

    // Track error in Firebase Analytics
    if (analytics) {
      logEvent(analytics, 'exception', {
        description: error.message,
        fatal: true,
        error_boundary: true,
        component_stack: errorInfo.componentStack,
        error_stack: error.stack,
      })
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
          <h2 className="text-lg font-semibold text-red-800">Something went wrong</h2>
          <details className="mt-2">
            <summary className="cursor-pointer text-red-600">Error details</summary>
            <pre className="mt-2 text-sm text-red-700 bg-red-100 p-2 rounded overflow-auto">
              {this.state.error?.toString()}
              {'\n\n'}
              {this.state.error?.stack}
            </pre>
          </details>
        </div>
      )
    }

    return this.props.children
  }
}