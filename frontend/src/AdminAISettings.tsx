import { useGreen } from "./context";
import { RafinhaConnection } from "./RafinhaConnection";

export function AdminAISettings() {
  const { user } = useGreen();
  if (user.role !== "admin") return null;
  return (
    <section className="admin-ai" aria-label="Inteligência Artificial">
      <h3>Inteligência Artificial</h3>
      <p>
        O Rafinha conversa usando a conta ChatGPT autorizada nesta instalação.
      </p>
      <RafinhaConnection />
      <p className="muted">
        O executável do portfólio começa sem conexão. Quem instalar precisa
        autorizar sua própria conta; nenhuma credencial do desenvolvedor
        acompanha o aplicativo.
      </p>
    </section>
  );
}
