import { FormEvent, useEffect, useState } from "react";
import { apiRequest, apiUpload, ApiError } from "../api/client";
import { ResourceItem, ResourceVisibility, ResourceWithUrl } from "../types";

const TYPE_ICONS: Record<string, string> = { pdf: "📄", image: "🖼️", text: "📝" };

export default function ResourcesPage() {
  const [resources, setResources] = useState<ResourceItem[]>([]);
  const [search, setSearch] = useState("");
  const [category, setCategory] = useState("");
  const [showForm, setShowForm] = useState(false);
  const [viewing, setViewing] = useState<ResourceWithUrl | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [categoryInput, setCategoryInput] = useState("");
  const [ageRange, setAgeRange] = useState("");
  const [visibility, setVisibility] = useState<ResourceVisibility>("private");
  const [file, setFile] = useState<File | null>(null);

  function load() {
    const params = new URLSearchParams();
    if (search) params.set("search", search);
    if (category) params.set("category", category);
    apiRequest<ResourceItem[]>(`/resources?${params.toString()}`).then(setResources);
  }

  useEffect(load, [search, category]);

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!file) {
      setError("Selecione um arquivo.");
      return;
    }
    const formData = new FormData();
    formData.append("title", title);
    if (description) formData.append("description", description);
    if (categoryInput) formData.append("category", categoryInput);
    if (ageRange) formData.append("suggested_age_range", ageRange);
    formData.append("visibility", visibility);
    formData.append("file", file);

    try {
      await apiUpload("/resources", formData);
      setShowForm(false);
      setTitle("");
      setDescription("");
      setCategoryInput("");
      setAgeRange("");
      setFile(null);
      load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 415) {
        setError("Tipo de arquivo não suportado. Envie PDF, imagem (PNG/JPEG/WEBP) ou texto simples.");
      } else if (err instanceof ApiError && err.status === 413) {
        setError("Arquivo excede o tamanho máximo permitido (10MB).");
      } else {
        setError("Não foi possível enviar o recurso.");
      }
    }
  }

  async function openResource(id: string) {
    const resource = await apiRequest<ResourceWithUrl>(`/resources/${id}`);
    setViewing(resource);
  }

  async function handleDelete(id: string) {
    if (!confirm("Remover este recurso? Ele ficará em Dados Excluídos por 60 dias.")) return;
    await apiRequest(`/resources/${id}`, { method: "DELETE" });
    load();
  }

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-brand-navy">Recursos Terapêuticos</h1>
        <button onClick={() => setShowForm((v) => !v)} className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
          + Adicionar recurso
        </button>
      </div>

      {showForm && (
        <form onSubmit={handleUpload} className="bg-white rounded-card shadow-sm p-6 mb-6 space-y-4 max-w-lg">
          <div>
            <label className="block text-sm font-medium mb-1">Título</label>
            <input required value={title} onChange={(e) => setTitle(e.target.value)} className="w-full h-10 rounded-btn border border-slate-300 px-3" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Descrição</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="w-full rounded-btn border border-slate-300 px-3 py-2" />
          </div>
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="block text-sm font-medium mb-1">Categoria</label>
              <input value={categoryInput} onChange={(e) => setCategoryInput(e.target.value)} className="w-full h-10 rounded-btn border border-slate-300 px-3" />
            </div>
            <div className="flex-1">
              <label className="block text-sm font-medium mb-1">Faixa etária sugerida</label>
              <input value={ageRange} onChange={(e) => setAgeRange(e.target.value)} className="w-full h-10 rounded-btn border border-slate-300 px-3" />
            </div>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Visibilidade</label>
            <select value={visibility} onChange={(e) => setVisibility(e.target.value as ResourceVisibility)} className="w-full h-10 rounded-btn border border-slate-300 px-3">
              <option value="private">Privado (só eu)</option>
              <option value="clinic_shared">Compartilhado com a clínica</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Arquivo (PDF, imagem ou texto — até 10MB)</label>
            <input
              type="file"
              accept=".pdf,image/png,image/jpeg,image/webp,text/plain"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full text-sm"
            />
          </div>
          {error && <p className="text-danger text-sm">{error}</p>}
          <div className="flex gap-3">
            <button type="submit" className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
              Enviar
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium">
              Cancelar
            </button>
          </div>
        </form>
      )}

      <div className="flex flex-wrap gap-3 mb-6">
        <input placeholder="Buscar por título..." value={search} onChange={(e) => setSearch(e.target.value)} className="h-10 rounded-btn border border-slate-300 px-3 flex-1 min-w-[240px]" />
        <input placeholder="Filtrar por categoria..." value={category} onChange={(e) => setCategory(e.target.value)} className="h-10 rounded-btn border border-slate-300 px-3" />
      </div>

      {resources.length === 0 ? (
        <div className="bg-white rounded-card shadow-sm p-10 text-center text-neutralState">
          Nenhum recurso adicionado ainda.
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {resources.map((resource) => (
            <div key={resource.id} className="bg-white rounded-card shadow-sm p-4">
              <div className="text-3xl mb-2">{TYPE_ICONS[resource.resource_type]}</div>
              <div className="font-medium text-brand-navy">{resource.title}</div>
              {resource.category && <div className="text-xs text-neutralState mt-1">{resource.category}</div>}
              <div className="flex gap-3 mt-3 text-sm">
                <button onClick={() => openResource(resource.id)} className="text-brand-blue underline">
                  Abrir
                </button>
                <button onClick={() => handleDelete(resource.id)} className="text-danger underline">
                  Excluir
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {viewing && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-6" onClick={() => setViewing(null)}>
          <div className="bg-white rounded-card shadow-lg max-w-3xl w-full max-h-[85vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between p-4 border-b border-slate-100">
              <h3 className="font-semibold text-brand-navy">{viewing.title}</h3>
              <div className="flex gap-3 text-sm">
                <a href={viewing.view_url} target="_blank" rel="noreferrer" className="text-brand-blue underline">
                  Baixar / Imprimir
                </a>
                <button onClick={() => setViewing(null)} className="text-neutralState">
                  Fechar
                </button>
              </div>
            </div>
            <div className="flex-1 overflow-auto">
              {viewing.resource_type === "image" ? (
                <img src={viewing.view_url} alt={viewing.title} className="max-w-full mx-auto" />
              ) : (
                <iframe src={viewing.view_url} title={viewing.title} className="w-full h-[70vh]" />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
