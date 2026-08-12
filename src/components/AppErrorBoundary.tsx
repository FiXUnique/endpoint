import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  failed: boolean;
}

export class AppErrorBoundary extends Component<Props, State> {
  state: State = { failed: false };

  static getDerivedStateFromError(): State {
    return { failed: true };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error("[endpoint:ui] application crashed", error, info.componentStack);
  }

  render() {
    if (this.state.failed) {
      return (
        <main className="fatal-error" role="alert">
          <div className="fatal-error-card">
            <span>Endpoint recovered a display error</span>
            <h1>The investigation page could not be rendered.</h1>
            <p>Your saved evidence was not deleted. Reload the local app to load a matching interface bundle.</p>
            <button onClick={() => window.location.reload()}>Reload Endpoint</button>
          </div>
        </main>
      );
    }
    return this.props.children;
  }
}
