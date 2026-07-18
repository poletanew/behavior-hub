import { useEffect, useState } from "react";
import { apiRequest } from "../api/client";
import { DeletedItem } from "../types";

const ENTITY_LABELS: Record<string, string> = {
  patient: "Paciente",
  objective: "Objetivo do plano",
  resource: "Recurso terapêutico",
};

export default function DeletedDataPage() {
  const [items, setItems] = useState<DeletedItem[]>([]);
  const [loading, setLoading] = useState(true);

  function load() {
    setLoading(true);
    apiRequest<DeletedItem[]>("/deleted-data")
      .then(setItems)
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleRestore(item: DeletedItem) {
    await apiRequest(`/deleted-data/${item.entity_type}/${item.id}/restore`, { method: "POST" });
    load();
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-2">Dados Excluídos</h1>
      <p className="text-sm text-neutralState mb-6">
        Registros excluídos ficam disponíveis para restauração por 60 dias antes da remoção definitiva.
      </p>

      {loading ? (
        <p className="text-neutralState">Carregando...</p>
      ) : items.length === 0 ? (
        <div className="bg-white rounded-card shadow-sm p-10 text-center text-neutralState">
          Nenhum registro em Dados Excluídos.
        </div>
      ) : (
        <div className="bg-white rounded-card shadow-sm overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-brand-navy text-white">
              <tr>
                <th className="text-left px-4 py-3">Tipo</th>
                <th className="text-left px-4 py-3">Nome</th>
                <th className="text-left px-4 py-3">Excluído em</th>
                <th className="text-left px-4 py-3">Dias restantes</th>
                <th className="text-right px-4 py-3">Ações</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item, idx) => (
                <tr key={`${item.entity_type}-${item.id}`} className={idx % 2 === 1 ? "bg-slate-50" : undefined}>
                  <td className="px-4 py-3">{ENTITY_LABELS[item.entity_type]}</td>
                  <td className="px-4 py-3">{item.label}</td>
                  <td className="px-4 py-3">{new Date(item.deleted_at).toLocaleDateString("pt-BR")}</td>
                  <td className="px-4 py-3">{item.days_remaining}</td>
                  <td className="px-4 py-3 text-right">
                    <button onClick={() => handleRestore(item)} className="text-brand-blue hover:underline">
                      Restaurar
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
