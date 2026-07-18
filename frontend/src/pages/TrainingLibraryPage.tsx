import { useEffect, useState } from "react";
import { apiRequest } from "../api/client";
import { Training, TrainingCategory } from "../types";

export default function TrainingLibraryPage() {
  const [categories, setCategories] = useState<TrainingCategory[]>([]);
  const [trainings, setTrainings] = useState<Training[]>([]);
  const [categoryId, setCategoryId] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Training | null>(null);

  useEffect(() => {
    apiRequest<TrainingCategory[]>("/training-categories").then(setCategories);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (categoryId) params.set("category_id", categoryId);
    if (search) params.set("search", search);
    apiRequest<Training[]>(`/trainings?${params.toString()}`).then(setTrainings);
  }, [categoryId, search]);

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-6">Training Library</h1>

      <div className="flex flex-wrap gap-3 mb-6">
        <input
          placeholder="Buscar por título ou objetivo..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="h-10 rounded-btn border border-slate-300 px-3 flex-1 min-w-[240px]"
        />
        <select
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className="h-10 rounded-btn border border-slate-300 px-3"
        >
          <option value="">Todas as categorias</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
          {trainings.map((training) => (
            <button
              key={training.id}
              onClick={() => setSelected(training)}
              className={`text-left bg-white rounded-card shadow-sm p-4 hover:ring-2 hover:ring-brand-turquoise transition ${
                selected?.id === training.id ? "ring-2 ring-brand-turquoise" : ""
              }`}
            >
              <div className="font-semibold text-brand-navy">{training.title}</div>
              <div className="text-xs text-neutralState mt-1 line-clamp-2">{training.objective}</div>
            </button>
          ))}
          {trainings.length === 0 && <p className="text-neutralState col-span-2">Nenhum treino encontrado.</p>}
        </div>

        <div>
          {selected ? (
            <div className="bg-white rounded-card shadow-sm p-6 sticky top-6 space-y-3 text-sm">
              <h2 className="font-bold text-brand-navy text-lg">{selected.title}</h2>
              <p>
                <span className="font-medium">Objetivo:</span> {selected.objective}
              </p>
              {selected.discriminative_instruction && (
                <p>
                  <span className="font-medium">Instrução discriminativa:</span> {selected.discriminative_instruction}
                </p>
              )}
              {selected.expected_response && (
                <p>
                  <span className="font-medium">Resposta esperada:</span> {selected.expected_response}
                </p>
              )}
              {selected.prompt_hierarchy && (
                <p>
                  <span className="font-medium">Hierarquia de ajuda:</span> {selected.prompt_hierarchy}
                </p>
              )}
              {selected.mastery_criteria && (
                <p>
                  <span className="font-medium">Critério de domínio:</span> {selected.mastery_criteria}
                </p>
              )}
            </div>
          ) : (
            <div className="bg-white rounded-card shadow-sm p-6 text-neutralState text-sm">
              Selecione um treino para ver os detalhes.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
