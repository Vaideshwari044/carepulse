import { Component, ErrorInfo, ReactNode } from "react";
import { AlertTriangle, RotateCcw } from "lucide-react";

interface Props {
  children?: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  public state: State = {
    hasError: false,
    error: null,
  };

  public static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  public componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("Uncaught error:", error, errorInfo);
  }

  public render() {
    if (this.state.hasError) {
      return (
        <div className="p-8 text-center bg-gray-900 border border-red-900/50 rounded-xl my-4">
          <AlertTriangle className="w-12 h-12 mx-auto text-red-500 mb-3" />
          <h2 className="text-lg font-bold text-gray-100">Something went wrong</h2>
          <p className="text-xs text-red-400 font-mono mt-1 mb-4">{this.state.error?.message}</p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg text-xs font-semibold inline-flex items-center gap-2"
          >
            <RotateCcw className="w-4 h-4" /> Try again
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
