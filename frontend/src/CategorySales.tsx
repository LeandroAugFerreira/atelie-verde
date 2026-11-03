import { useGreen } from "./context";
import { categories } from "./Forms";

export function CategorySales({ values }: { values: Record<string, number> }) {
  const { go } = useGreen();
  const rows = categories
    .map((name) => ({ name, quantity: values[name] || 0 }))
    .sort((a, b) => b.quantity - a.quantity);
  const total = rows.reduce((sum, row) => sum + row.quantity, 0);
  return (
    <div
      className="category-sales"
      aria-label="Vendas por categoria em unidades"
    >
      <div className="category-sales-total">
        <strong>{total.toLocaleString("pt-BR")}</strong>
        <span>unidades vendidas no período</span>
      </div>
      <ol>
        {rows.map(({ name, quantity }) => {
          const percent = total ? (quantity * 100) / total : 0;
          return (
            <li key={name}>
              <button
                aria-label={`${name}: ${quantity} unidades, ${percent.toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% do total. Ver produtos.`}
                title="Ver produtos desta categoria"
                onClick={() => go("inventory", categories.indexOf(name) + 1)}
              >
                <span className="category-sales-name">{name}</span>
                <span className="category-sales-value">
                  <b>{quantity.toLocaleString("pt-BR")}</b>
                  <small>
                    {percent.toLocaleString("pt-BR", {
                      maximumFractionDigits: 1,
                    })}
                    %
                  </small>
                </span>
                <span className="category-sales-track">
                  <i style={{ width: `${percent}%` }} />
                </span>
              </button>
            </li>
          );
        })}
      </ol>
      {!total && (
        <span className="category-sales-empty">
          Nenhuma venda registrada neste período.
        </span>
      )}
    </div>
  );
}
