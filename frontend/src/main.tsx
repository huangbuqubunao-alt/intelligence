import React from "react";
import ReactDOM from "react-dom/client";
import { App } from "./workspace/App";
import "./workspace/styles.css";

interface ErrorBoundaryState {
  error: Error | null;
}

class WorkspaceErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  state: ErrorBoundaryState = { error: null };

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { error };
  }

  override render(): React.ReactNode {
    if (!this.state.error) return this.props.children;
    return (
      <main className="workspace-error-fallback" role="alert">
        <h1>界面遇到了意外错误</h1>
        <p className="muted">本地已保存的内容、证据与洞察不受影响，刷新页面即可恢复。</p>
        <p className="mono">{this.state.error.message}</p>
        <div className="button-row">
          <button
            type="button"
            className="button button-primary"
            onClick={() => {
              this.setState({ error: null });
              window.location.reload();
            }}
          >
            刷新恢复
          </button>
        </div>
      </main>
    );
  }
}

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <WorkspaceErrorBoundary>
      <App />
    </WorkspaceErrorBoundary>
  </React.StrictMode>
);
