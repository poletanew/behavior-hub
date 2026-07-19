import { FormEvent, useEffect, useState } from "react";
import { apiRequest } from "../api/client";
import { ResourceItem, ResourceLink, Training, TrainingCategory } from "../types";

export default function TrainingLibraryPage() {
  const [categories, setCategories] = useState<TrainingCategory[]>([]);
  const [trainings, setTrainings] = useState<Training[]>([]);
  const [categoryId, setCategoryId] = useState("");
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState<Training | null>(null);
  const [resources, setResources] = useState<ResourceItem[]>([]);
  const [resourceLinks, setResourceLinks] = useState<ResourceLink[]>([]);
  const [linkResourceId, setLinkResourceId] = useState("");
  const [linkRelevance, setLinkRelevance] = useState(3);

  useEffect(() => {
    apiRequest<TrainingCategory[]>("/training-categories").then(setCategories);
    apiRequest<ResourceItem[]>("/resources").then(setResources);
  }, []);

  useEffect(() => {
    const params = new URLSearchParams();
    if (categoryId) params.set("category_id", categoryId);
    if (search) params.set("search", search);
    apiRequest<Training[]>(`/trainings?${params.toString()}`).then(setTrainings);
  }, [categoryId, search]);

  function loadResourceLinks(trainingId: string) {
    apiRequest<ResourceLink[]>(`/trainings/${trainingId}/resource-links`).then(setResourceLinks);
  }

  function selectTraining(training: Training) {
    setSelected(training);
    loadResourceLinks(training.id);
  }

  async function handleLinkResource(e: FormEvent) {
    e.preventDefault();
    if (!selected || !linkResourceId) return;
    await apiRequest("/resource-links", {
      method: "POST",
      body: { resource_id: linkResourceId, training_id: selected.id, relevance_score: linkRelevance },
    });
    setLinkResourceId("");
    setLinkRelevance(3);
    loadResourceLinks(selected.id);
  }

  async function handleUnlinkResource(linkId: string) {
    if (!selected) return;
    await apiRequest(`/resource-links/${linkId}`, { method: "DELETE" });
    loadResourceLinks(selected.id);
  }

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
              onClick={() => selectTraining(training)}
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

              <div className="pt-3 border-t border-slate-100 mt-2">
                <div className="font-medium text-xs uppercase text-neutralState mb-2">
                  Recursos vinculados (Biblioteca Inteligente)
                </div>
                <ul className="space-y-2 mb-3">
                  {resourceLinks.map((link) => (
                    <li key={link.id} className="flex items-center justify-between bg-slate-50 rounded-btn px-3 py-2 text-xs">
                      <span>
                        {link.resource_title} — relevância {link.relevance_score}/5
                      </span>
                      <button onClick={() => handleUnlinkResource(link.id)} className="text-danger">
                        Remover
                      </button>
                    </li>
                  ))}
                  {resourceLinks.length === 0 && (
                    <li className="text-xs text-neutralState">Nenhum recurso vinculado ainda.</li>
                  )}
                </ul>
                <form onSubmit={handleLinkResource} className="flex gap-2">
                  <select
                    value={linkResourceId}
                    onChange={(e) => setLinkResourceId(e.target.value)}
                    className="h-8 text-xs rounded-btn border border-slate-300 px-2 flex-1"
                  >
                    <option value="">Vincular um recurso...</option>
                    {resources.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.title}
                      </option>
                    ))}
                  </select>
                  <select
                    value={linkRelevance}
                    onChange={(e) => setLinkRelevance(Number(e.target.value))}
                    className="h-8 text-xs rounded-btn border border-slate-300 px-2"
                  >
                    {[1, 2, 3, 4, 5].map((n) => (
                      <option key={n} value={n}>
                        Relevância {n}
                      </option>
                    ))}
                  </select>
                  <button type="submit" className="h-8 rounded-btn bg-brand-turquoise text-white px-3 text-xs font-medium">
                    Vincular
                  </button>
                </form>
              </div>
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
