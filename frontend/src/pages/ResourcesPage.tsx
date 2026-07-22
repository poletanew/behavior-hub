import { FormEvent, useEffect, useState } from "react";
import { apiRequest, apiUpload, ApiError } from "../api/client";
import EmptyState from "../components/EmptyState";
import { AIResourceKind, ResourceAIDraft, ResourceItem, ResourceVisibility, ResourceWithUrl } from "../types";

const TYPE_ICONS: Record<string, string> = { pdf: "📄", image: "🖼️", text: "📝" };

const AI_KIND_LABELS: Record<AIResourceKind, string> = {
  historia_social: "História Social",
  rotina_visual: "Rotina Visual",
  cartao_comunicacao: "Cartão de Comunicação",
};

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

  const [showAiForm, setShowAiForm] = useState(false);
  const [aiKind, setAiKind] = useState<AIResourceKind>("historia_social");
  const [aiTheme, setAiTheme] = useState("");
  const [aiAgeRange, setAiAgeRange] = useState("");
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiDraft, setAiDraft] = useState<ResourceAIDraft | null>(null);
  const [aiVisibility, setAiVisibility] = useState<ResourceVisibility>("private");
  const [aiPublishing, setAiPublishing] = useState(false);

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

  async function handleGenerateAiDraft(e: FormEvent) {
    e.preventDefault();
    setAiError(null);
    setAiGenerating(true);
    try {
      const draft = await apiRequest<ResourceAIDraft>("/resources/ai-draft", {
        method: "POST",
        body: { kind: aiKind, theme: aiTheme, age_range: aiAgeRange },
      });
      setAiDraft(draft);
    } catch {
      setAiError("Não foi possível gerar o rascunho.");
    } finally {
      setAiGenerating(false);
    }
  }

  async function handlePublishAiResource() {
    if (!aiDraft) return;
    setAiPublishing(true);
    setAiError(null);
    try {
      await apiRequest("/resources/ai-publish", {
        method: "POST",
        body: {
          kind: aiDraft.kind,
          theme: aiDraft.theme,
          age_range: aiDraft.age_range,
          title: aiDraft.title,
          description: aiDraft.description,
          content_text: aiDraft.content_text,
          visibility: aiVisibility,
        },
      });
      setShowAiForm(false);
      setAiDraft(null);
      setAiTheme("");
      setAiAgeRange("");
      load();
    } catch {
      setAiError("Não foi possível publicar o recurso.");
    } finally {
      setAiPublishing(false);
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
        <div className="flex gap-3">
          <button
            onClick={() => {
              setShowAiForm((v) => !v);
              setAiDraft(null);
              setAiError(null);
            }}
            className="rounded-btn bg-white border border-brand-turquoise text-brand-turquoise px-4 py-2 text-sm font-medium"
          >
            ✨ Criar recurso com IA
          </button>
          <button onClick={() => setShowForm((v) => !v)} className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
            + Adicionar recurso
          </button>
        </div>
      </div>

      {showAiForm && (
        <div className="bg-white rounded-card shadow-sm p-6 mb-6 max-w-lg">
          {!aiDraft ? (
            <form onSubmit={handleGenerateAiDraft} className="space-y-4">
              <div>
                <label className="block text-sm font-medium mb-1">Tipo de recurso</label>
                <select
                  value={aiKind}
                  onChange={(e) => setAiKind(e.target.value as AIResourceKind)}
                  className="w-full h-10 rounded-btn border border-slate-300 px-3"
                >
                  {Object.entries(AI_KIND_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Tema</label>
                <input
                  required
                  value={aiTheme}
                  onChange={(e) => setAiTheme(e.target.value)}
                  placeholder="Ex.: Ir ao dentista"
                  className="w-full h-10 rounded-btn border border-slate-300 px-3"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Faixa etária</label>
                <input
                  required
                  value={aiAgeRange}
                  onChange={(e) => setAiAgeRange(e.target.value)}
                  placeholder="Ex.: 5-7 anos"
                  className="w-full h-10 rounded-btn border border-slate-300 px-3"
                />
              </div>
              {aiError && <p className="text-danger text-sm">{aiError}</p>}
              <div className="flex gap-3">
                <button
                  type="submit"
                  disabled={aiGenerating}
                  className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium disabled:opacity-50"
                >
                  {aiGenerating ? "Gerando..." : "Gerar rascunho"}
                </button>
                <button
                  type="button"
                  onClick={() => setShowAiForm(false)}
                  className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium"
                >
                  Cancelar
                </button>
              </div>
            </form>
          ) : (
            <div className="space-y-4">
              <span className="inline-block text-[10px] uppercase font-semibold px-2 py-1 rounded-full bg-brand-turquoise/10 text-brand-turquoise">
                Gerado por IA — revise antes de publicar
              </span>
              <div>
                <label className="block text-sm font-medium mb-1">Título</label>
                <input
                  value={aiDraft.title}
                  onChange={(e) => setAiDraft({ ...aiDraft, title: e.target.value })}
                  className="w-full h-10 rounded-btn border border-slate-300 px-3"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Descrição</label>
                <textarea
                  value={aiDraft.description}
                  onChange={(e) => setAiDraft({ ...aiDraft, description: e.target.value })}
                  className="w-full rounded-btn border border-slate-300 px-3 py-2"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Conteúdo</label>
                <textarea
                  value={aiDraft.content_text}
                  onChange={(e) => setAiDraft({ ...aiDraft, content_text: e.target.value })}
                  rows={8}
                  className="w-full rounded-btn border border-slate-300 px-3 py-2 font-mono text-sm"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">Visibilidade</label>
                <select
                  value={aiVisibility}
                  onChange={(e) => setAiVisibility(e.target.value as ResourceVisibility)}
                  className="w-full h-10 rounded-btn border border-slate-300 px-3"
                >
                  <option value="private">Privado (só eu)</option>
                  <option value="clinic_shared">Compartilhado com a clínica</option>
                </select>
              </div>
              {aiError && <p className="text-danger text-sm">{aiError}</p>}
              <div className="flex gap-3">
                <button
                  onClick={handlePublishAiResource}
                  disabled={aiPublishing}
                  className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium disabled:opacity-50"
                >
                  {aiPublishing ? "Publicando..." : "Publicar"}
                </button>
                <button
                  onClick={() => setAiDraft(null)}
                  className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium"
                >
                  Voltar
                </button>
              </div>
            </div>
          )}
        </div>
      )}

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
        <EmptyState icon="📚" message="Nenhum recurso adicionado ainda. Que tal criar o primeiro com IA?" />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {resources.map((resource) => (
            <div key={resource.id} className="bg-white rounded-card shadow-sm p-4">
              <div className="text-3xl mb-2">{TYPE_ICONS[resource.resource_type]}</div>
              <div className="font-medium text-brand-navy">
                {resource.title}
                {resource.ai_generated && (
                  <span className="ml-2 rounded px-1.5 py-0.5 text-[10px] font-medium bg-brand-turquoise/10 text-brand-turquoise align-middle">
                    Gerado por IA
                  </span>
                )}
              </div>
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
