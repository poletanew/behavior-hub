import { FormEvent, useEffect, useState } from "react";
import { Link2, Plus } from "lucide-react";
import { apiRequest, ApiError } from "../api/client";
import { Patient, ResourceItem, ResourceLink, Training, TrainingCategory } from "../types";

function NewTrainingForm({
  categories,
  onCreated,
  onCancel,
}: {
  categories: TrainingCategory[];
  onCreated: () => void;
  onCancel: () => void;
}) {
  const [categoryId, setCategoryId] = useState("");
  const [title, setTitle] = useState("");
  const [objective, setObjective] = useState("");
  const [discriminativeInstruction, setDiscriminativeInstruction] = useState("");
  const [expectedResponse, setExpectedResponse] = useState("");
  const [promptHierarchy, setPromptHierarchy] = useState("");
  const [masteryCriteria, setMasteryCriteria] = useState("");
  const [notes, setNotes] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await apiRequest("/trainings", {
        method: "POST",
        body: {
          category_id: categoryId,
          title,
          objective,
          discriminative_instruction: discriminativeInstruction || null,
          expected_response: expectedResponse || null,
          prompt_hierarchy: promptHierarchy || null,
          mastery_criteria: masteryCriteria || null,
          notes: notes || null,
        },
      });
      onCreated();
    } catch {
      setError("Não foi possível criar o treino. Confirme os campos obrigatórios.");
    }
  }

  return (
    <form onSubmit={handleSubmit} className="bg-white rounded-card shadow-card p-6 mb-6 space-y-4 max-w-xl">
      <div>
        <label className="block text-sm font-medium mb-1">Categoria</label>
        <select
          required
          value={categoryId}
          onChange={(e) => setCategoryId(e.target.value)}
          className="w-full h-10 rounded-btn border border-slate-300 px-3"
        >
          <option value="">Selecione...</option>
          {categories.map((c) => (
            <option key={c.id} value={c.id}>
              {c.name}
            </option>
          ))}
        </select>
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Título</label>
        <input
          required
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          className="w-full h-10 rounded-btn border border-slate-300 px-3"
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Objetivo</label>
        <textarea
          required
          value={objective}
          onChange={(e) => setObjective(e.target.value)}
          className="w-full rounded-btn border border-slate-300 px-3 py-2"
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Instrução discriminativa</label>
        <textarea
          value={discriminativeInstruction}
          onChange={(e) => setDiscriminativeInstruction(e.target.value)}
          className="w-full rounded-btn border border-slate-300 px-3 py-2"
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Resposta esperada</label>
        <textarea
          value={expectedResponse}
          onChange={(e) => setExpectedResponse(e.target.value)}
          className="w-full rounded-btn border border-slate-300 px-3 py-2"
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Hierarquia de ajuda</label>
        <textarea
          value={promptHierarchy}
          onChange={(e) => setPromptHierarchy(e.target.value)}
          className="w-full rounded-btn border border-slate-300 px-3 py-2"
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Critério de domínio</label>
        <textarea
          value={masteryCriteria}
          onChange={(e) => setMasteryCriteria(e.target.value)}
          className="w-full rounded-btn border border-slate-300 px-3 py-2"
        />
      </div>
      <div>
        <label className="block text-sm font-medium mb-1">Observações</label>
        <textarea
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
          className="w-full rounded-btn border border-slate-300 px-3 py-2"
        />
      </div>
      {error && <p className="text-danger text-sm">{error}</p>}
      <div className="flex gap-3">
        <button type="submit" className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
          Salvar treino
        </button>
        <button
          type="button"
          onClick={onCancel}
          className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium"
        >
          Cancelar
        </button>
      </div>
    </form>
  );
}

function LinkToPatientPanel({ training }: { training: Training }) {
  const [open, setOpen] = useState(false);
  const [patients, setPatients] = useState<Patient[]>([]);
  const [search, setSearch] = useState("");
  const [message, setMessage] = useState<string | null>(null);

  useEffect(() => {
    if (open && patients.length === 0) {
      apiRequest<Patient[]>("/patients").then(setPatients);
    }
  }, [open, patients.length]);

  const filtered = patients.filter((p) => p.name.toLowerCase().includes(search.toLowerCase()));

  async function handleLink(patientId: string) {
    setMessage(null);
    try {
      await apiRequest(`/trainings/${training.id}/link`, {
        method: "POST",
        body: { patient_id: patientId },
      });
      setMessage("Treino vinculado — vai aparecer como \"Prescrito\" no Novo Atendimento desse paciente.");
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setMessage("Este treino já está vinculado a esse paciente.");
      } else {
        setMessage("Não foi possível vincular o treino.");
      }
    }
  }

  return (
    <div className="pt-3 border-t border-slate-100 mt-2">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="text-xs font-medium text-brand-blue underline flex items-center gap-1"
      >
        <Link2 size={12} /> {open ? "Fechar" : "Vincular a um paciente"}
      </button>
      {open && (
        <div className="mt-2 space-y-2">
          <input
            placeholder="Buscar paciente por nome..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="w-full h-8 text-xs rounded-btn border border-slate-300 px-2"
          />
          <ul className="max-h-48 overflow-y-auto divide-y divide-slate-100 border border-slate-100 rounded-btn">
            {filtered.map((p) => (
              <li key={p.id} className="flex items-center justify-between px-3 py-2 text-xs">
                <span>{p.name}</span>
                <button onClick={() => handleLink(p.id)} className="text-brand-turquoise font-medium">
                  Vincular
                </button>
              </li>
            ))}
            {filtered.length === 0 && <li className="px-3 py-2 text-xs text-neutralState">Nenhum paciente encontrado.</li>}
          </ul>
          {message && <p className="text-xs text-neutralState">{message}</p>}
        </div>
      )}
    </div>
  );
}

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
  const [showNewTraining, setShowNewTraining] = useState(false);

  function loadTrainings() {
    const params = new URLSearchParams();
    if (categoryId) params.set("category_id", categoryId);
    if (search) params.set("search", search);
    apiRequest<Training[]>(`/trainings?${params.toString()}`).then(setTrainings);
  }

  useEffect(() => {
    apiRequest<TrainingCategory[]>("/training-categories").then(setCategories);
    apiRequest<ResourceItem[]>("/resources").then(setResources);
  }, []);

  useEffect(loadTrainings, [categoryId, search]);

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
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-brand-navy">Biblioteca de Treino</h1>
        <button
          onClick={() => setShowNewTraining((v) => !v)}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium flex items-center gap-1.5"
        >
          <Plus size={15} /> Novo Treinamento
        </button>
      </div>

      {showNewTraining && (
        <NewTrainingForm
          categories={categories}
          onCreated={() => {
            setShowNewTraining(false);
            loadTrainings();
          }}
          onCancel={() => setShowNewTraining(false)}
        />
      )}

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
          {trainings.map((training) => {
            const categoryName = categories.find((c) => c.id === training.category_id)?.name;
            return (
              <button
                key={training.id}
                onClick={() => selectTraining(training)}
                className={`text-left bg-white rounded-card shadow-card p-4 hover:ring-2 hover:ring-brand-turquoise transition ${
                  selected?.id === training.id ? "ring-2 ring-brand-turquoise" : ""
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="font-semibold text-brand-navy">{training.title}</div>
                  {categoryName && (
                    <span className="shrink-0 rounded-full px-2.5 py-0.5 text-[11px] font-bold bg-info/10 text-info">
                      {categoryName}
                    </span>
                  )}
                </div>
                <div className="text-xs text-neutralState mt-1 line-clamp-2">{training.objective}</div>
              </button>
            );
          })}
          {trainings.length === 0 && <p className="text-neutralState col-span-2">Nenhum treino encontrado.</p>}
        </div>

        <div>
          {selected ? (
            <div className="bg-white rounded-card shadow-card p-6 sticky top-6 space-y-3 text-sm">
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

              <LinkToPatientPanel training={selected} />
            </div>
          ) : (
            <div className="bg-white rounded-card shadow-card p-6 text-neutralState text-sm">
              Selecione um treino para ver os detalhes.
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
