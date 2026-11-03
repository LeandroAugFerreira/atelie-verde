import { Component, type ReactNode } from "react";
import { Leaf } from "lucide-react";

export class ErrorBoundary extends Component<
  { children: ReactNode },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  render() {
    return this.state.failed ? (
      <div className="app-loading" role="alert">
        <Leaf size={34} />
        <h2>Não foi possível exibir esta tela</h2>
        <p>Recarregue a aplicação para continuar.</p>
        <button
          className="button primary"
          onClick={() => window.location.reload()}
        >
          Recarregar aplicação
        </button>
      </div>
    ) : (
      this.props.children
    );
  }
}
