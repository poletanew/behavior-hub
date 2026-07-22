import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { apiRequest, apiUpload, ApiError } from "../api/client";
import {
  ApplierType,
  DuplicateCandidate,
  FamilyAccess,
  GeneralizationContext,
  Objective,
  ObjectiveAIFillResponse,
  ObjectiveApplier,
  ObjectiveComment,
  ObjectivePriority,
  ObjectiveStatus,
  Patient,
  ResourceItem,
  ResourceLink,
  TreatmentArea,
  TreatmentPlan,
  TreatmentPlanAttachment,
  User,
} from "../types";

const GENERALIZATION_CONTEXT_LABELS: Record<GeneralizationContext, string> = {
  clinica: "Clínica",
  casa: "Casa",
  escola: "Escola",
  outro: "Outro",
};

const APPLIER_TYPE_LABELS: Record<ApplierType, string> = {
  professional: "Profissional",
  parent: "Pai/cuidador",
};

const AREA_LABELS: Record<TreatmentArea, string> = {
  psicologia: "Psicologia",
  aba: "ABA",
  fonoaudiologia: "Fonoaudiologia",
  terapia_ocupacional: "Terapia Ocupacional",
  psicopedagogia: "Psicopedagogia",
  fisioterapia: "Fisioterapia",
  nutricao: "Nutrição",
  outra: "Outra",
};

const STATUS_LABELS: Record<ObjectiveStatus, string> = {
  not_started: "Não iniciado",
  in_progress: "Em andamento",
  mastered: "Dominado",
  paused: "Pausado",
  discontinued: "Descontinuado",
};

const STATUS_COLORS: Record<ObjectiveStatus, string> = {
  not_started: "bg-slate-100 text-slate-600",
  in_progress: "bg-info/10 text-info",
  mastered: "bg-success/10 text-success",
  paused: "bg-warning/10 text-warning",
  discontinued: "bg-danger/10 text-danger",
};

const PRIORITY_LABELS: Record<ObjectivePriority, string> = { low: "Baixa", medium: "Média", high: "Alta" };

function ObjectiveCard({
  objective,
  onChanged,
  professionals,
  resources,
  familyAccesses,
}: {
  objective: Objective;
  onChanged: () => void;
  professionals: User[];
  resources: ResourceItem[];
  familyAccesses: FamilyAccess[];
}) {
  const [expanded, setExpanded] = useState(false);
  const [comments, setComments] = useState<ObjectiveComment[]>([]);
  const [commentBody, setCommentBody] = useState("");
  const [mentionedUserId, setMentionedUserId] = useState("");
  const [resourceLinks, setResourceLinks] = useState<ResourceLink[]>([]);
  const [linkResourceId, setLinkResourceId] = useState("");
  const [linkRelevance, setLinkRelevance] = useState(3);

  const [appliers, setAppliers] = useState<ObjectiveApplier[]>([]);
  const [applierType, setApplierType] = useState<ApplierType>("professional");
  const [applierUserId, setApplierUserId] = useState("");
  const [applierError, setApplierError] = useState<string | null>(null);

  const [genContext, setGenContext] = useState<GeneralizationContext>("clinica");
  const [genTestedAt, setGenTestedAt] = useState(() => new Date().toISOString().slice(0, 10));
  const [genResult, setGenResult] = useState("");
  const [genNotes, setGenNotes] = useState("");

  const [maintenanceResult, setMaintenanceResult] = useState<"mantida" | "perdida">("mantida");
  const [maintenanceNotes, setMaintenanceNotes] = useState("");

  function loadComments() {
    apiRequest<ObjectiveComment[]>(`/objectives/${objective.id}/comments`).then(setComments);
  }

  function loadResourceLinks() {
    apiRequest<ResourceLink[]>(`/objectives/${objective.id}/resource-links`).then(setResourceLinks);
  }

  function loadAppliers() {
    apiRequest<ObjectiveApplier[]>(`/objectives/${objective.id}/appliers`).then(setAppliers);
  }

  useEffect(() => {
    if (expanded) {
      loadComments();
      loadResourceLinks();
      loadAppliers();
    }
  }, [expanded]);

  async function handleLinkResource(e: FormEvent) {
    e.preventDefault();
    if (!linkResourceId) return;
    await apiRequest("/resource-links", {
      method: "POST",
      body: { resource_id: linkResourceId, objective_id: objective.id, relevance_score: linkRelevance },
    });
    setLinkResourceId("");
    setLinkRelevance(3);
    loadResourceLinks();
  }

  async function handleUnlinkResource(linkId: string) {
    await apiRequest(`/resource-links/${linkId}`, { method: "DELETE" });
    loadResourceLinks();
  }

  function professionalName(userId: string): string {
    return professionals.find((p) => p.id === userId)?.name || "Profissional";
  }

  async function updateStatus(status: ObjectiveStatus) {
    await apiRequest(`/objectives/${objective.id}`, { method: "PATCH", body: { status } });
    onChanged();
  }

  async function handleDelete() {
    if (!confirm("Excluir este objetivo? O histórico será mantido.")) return;
    await apiRequest(`/objectives/${objective.id}`, { method: "DELETE" });
    onChanged();
  }

  async function submitComment(e: FormEvent) {
    e.preventDefault();
    await apiRequest(`/objectives/${objective.id}/comments`, {
      method: "POST",
      body: { body: commentBody, mentioned_user_id: mentionedUserId || null },
    });
    setCommentBody("");
    setMentionedUserId("");
    loadComments();
  }

  async function submitApplier(e: FormEvent) {
    e.preventDefault();
    setApplierError(null);
    if (!applierUserId) return;
    try {
      await apiRequest(`/objectives/${objective.id}/appliers`, {
        method: "POST",
        body: { applier_type: applierType, applier_user_id: applierUserId },
      });
      setApplierUserId("");
      loadAppliers();
    } catch (err) {
      if (err instanceof ApiError && err.status === 400) {
        setApplierError("Este responsável ainda não tem acesso ativo ao Portal da Família para este paciente.");
      } else if (err instanceof ApiError && err.status === 409) {
        setApplierError("Esta pessoa já é aplicadora deste objetivo.");
      } else {
        setApplierError("Não foi possível adicionar o aplicador.");
      }
    }
  }

  async function submitGeneralizationContext(e: FormEvent) {
    e.preventDefault();
    if (!genResult) return;
    await apiRequest(`/objectives/${objective.id}/generalization-contexts`, {
      method: "POST",
      body: { context: genContext, tested_at: genTestedAt, result: genResult, notes: genNotes || null },
    });
    setGenResult("");
    setGenNotes("");
    onChanged();
  }

  async function submitMaintenanceCheck(e: FormEvent) {
    e.preventDefault();
    await apiRequest(`/objectives/${objective.id}/maintenance-checks`, {
      method: "POST",
      body: { result: maintenanceResult, notes: maintenanceNotes || null },
    });
    setMaintenanceNotes("");
    onChanged();
  }

  const activeFamilyAccesses = familyAccesses.filter((a) => !a.revoked_at);

  return (
    <div className="bg-white rounded-card shadow-sm p-4 mb-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="font-medium text-brand-navy">
            {objective.title}
            {objective.ai_generated && (
              <span className="ml-2 rounded px-1.5 py-0.5 text-[10px] font-medium bg-brand-turquoise/10 text-brand-turquoise align-middle">
                Gerado por IA
              </span>
            )}
          </div>
          <div className="text-xs text-neutralState mt-0.5">Prioridade: {PRIORITY_LABELS[objective.priority]}</div>
          {objective.maintenance_due && (
            <div className="text-[10px] font-semibold text-warning mt-1">
              ⏰ Reteste de manutenção pendente
            </div>
          )}
        </div>
        <span className={`text-[10px] uppercase font-semibold px-2 py-1 rounded-full ${STATUS_COLORS[objective.status]}`}>
          {STATUS_LABELS[objective.status]}
        </span>
      </div>

      <button onClick={() => setExpanded((v) => !v)} className="text-xs text-brand-blue underline mt-2">
        {expanded ? "Ocultar detalhes" : "Ver detalhes"}
      </button>

      {expanded && (
        <div className="mt-2 text-sm space-y-1 border-t border-slate-100 pt-2">
          {objective.description && <p>{objective.description}</p>}
          {objective.criteria && (
            <p>
              <span className="font-medium">Critério de domínio:</span> {objective.criteria}
            </p>
          )}
          {objective.strategies && (
            <p>
              <span className="font-medium">Estratégias:</span> {objective.strategies}
            </p>
          )}
          <div className="flex flex-wrap gap-2 pt-2">
            <select
              value={objective.status}
              onChange={(e) => updateStatus(e.target.value as ObjectiveStatus)}
              className="h-8 text-xs rounded-btn border border-slate-300 px-2"
            >
              {Object.entries(STATUS_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <button onClick={handleDelete} className="h-8 text-xs text-danger px-2">
              Excluir
            </button>
          </div>

          <div className="pt-3 border-t border-slate-100 mt-2">
            <div className="font-medium text-xs uppercase text-neutralState mb-2">Comentários</div>
            <ul className="space-y-2 mb-3">
              {comments.map((comment) => (
                <li key={comment.id} className="bg-slate-50 rounded-btn px-3 py-2 text-xs">
                  <div className="font-medium">{professionalName(comment.author_id)}</div>
                  <div>{comment.body}</div>
                </li>
              ))}
              {comments.length === 0 && <li className="text-xs text-neutralState">Nenhum comentário ainda.</li>}
            </ul>
            <form onSubmit={submitComment} className="space-y-2">
              <textarea
                required
                value={commentBody}
                onChange={(e) => setCommentBody(e.target.value)}
                placeholder="Escreva um comentário..."
                className="w-full text-xs rounded-btn border border-slate-300 px-2 py-1.5"
              />
              <div className="flex gap-2">
                <select
                  value={mentionedUserId}
                  onChange={(e) => setMentionedUserId(e.target.value)}
                  className="h-8 text-xs rounded-btn border border-slate-300 px-2 flex-1"
                >
                  <option value="">Mencionar (@) um profissional — opcional</option>
                  {professionals.map((p) => (
                    <option key={p.id} value={p.id}>
                      @{p.name}
                    </option>
                  ))}
                </select>
                <button type="submit" className="h-8 rounded-btn bg-brand-turquoise text-white px-3 text-xs font-medium">
                  Comentar
                </button>
              </div>
            </form>
          </div>

          <div className="pt-3 border-t border-slate-100 mt-2">
            <div className="font-medium text-xs uppercase text-neutralState mb-2">
              Recursos recomendados (Biblioteca Inteligente)
            </div>
            <ul className="space-y-2 mb-3">
              {resourceLinks.map((link) => (
                <li key={link.id} className="flex items-center justify-between bg-slate-50 rounded-btn px-3 py-2 text-xs">
                  <span>
                    {link.resource_title} — relevância {link.relevance_score}/5
                    {link.training_id && <span className="text-neutralState"> (via treino)</span>}
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

          {objective.status === "mastered" && (
            <div className="pt-3 border-t border-slate-100 mt-2">
              <div className="font-medium text-xs uppercase text-neutralState mb-2">
                Manutenção e generalização (Addendum RF-24)
              </div>
              <p className="text-xs text-neutralState mb-2">
                {objective.maintenance_check_date
                  ? `Próximo reteste de manutenção: ${formatDate(objective.maintenance_check_date)}${
                      objective.maintenance_due ? " (pendente)" : ""
                    }`
                  : "Sem reteste de manutenção agendado."}
              </p>
              <form onSubmit={submitMaintenanceCheck} className="flex flex-wrap gap-2 mb-3">
                <select
                  value={maintenanceResult}
                  onChange={(e) => setMaintenanceResult(e.target.value as "mantida" | "perdida")}
                  className="h-8 text-xs rounded-btn border border-slate-300 px-2"
                >
                  <option value="mantida">Habilidade mantida</option>
                  <option value="perdida">Habilidade perdida</option>
                </select>
                <input
                  value={maintenanceNotes}
                  onChange={(e) => setMaintenanceNotes(e.target.value)}
                  placeholder="Observações (opcional)"
                  className="h-8 text-xs rounded-btn border border-slate-300 px-2 flex-1 min-w-[140px]"
                />
                <button type="submit" className="h-8 rounded-btn bg-white border border-slate-300 px-3 text-xs font-medium">
                  Registrar reteste
                </button>
              </form>

              <ul className="space-y-1 mb-2">
                {(objective.generalization_contexts || []).map((entry, idx) => (
                  <li key={idx} className="bg-slate-50 rounded-btn px-3 py-2 text-xs">
                    <span className="font-medium">{GENERALIZATION_CONTEXT_LABELS[entry.context]}</span>
                    {" — "}
                    {formatDate(entry.tested_at)}: {entry.result}
                    {entry.notes && <div className="text-neutralState">{entry.notes}</div>}
                  </li>
                ))}
                {(objective.generalization_contexts || []).length === 0 && (
                  <li className="text-xs text-neutralState">Generalização ainda não testada em nenhum contexto.</li>
                )}
              </ul>
              <form onSubmit={submitGeneralizationContext} className="flex flex-wrap gap-2">
                <select
                  value={genContext}
                  onChange={(e) => setGenContext(e.target.value as GeneralizationContext)}
                  className="h-8 text-xs rounded-btn border border-slate-300 px-2"
                >
                  {Object.entries(GENERALIZATION_CONTEXT_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <input
                  type="date"
                  required
                  value={genTestedAt}
                  onChange={(e) => setGenTestedAt(e.target.value)}
                  className="h-8 text-xs rounded-btn border border-slate-300 px-2"
                />
                <input
                  required
                  value={genResult}
                  onChange={(e) => setGenResult(e.target.value)}
                  placeholder="Resultado observado"
                  className="h-8 text-xs rounded-btn border border-slate-300 px-2 flex-1 min-w-[140px]"
                />
                <input
                  value={genNotes}
                  onChange={(e) => setGenNotes(e.target.value)}
                  placeholder="Notas (opcional)"
                  className="h-8 text-xs rounded-btn border border-slate-300 px-2 flex-1 min-w-[140px]"
                />
                <button type="submit" className="h-8 rounded-btn bg-brand-turquoise text-white px-3 text-xs font-medium">
                  Registrar
                </button>
              </form>
            </div>
          )}

          <div className="pt-3 border-t border-slate-100 mt-2">
            <div className="font-medium text-xs uppercase text-neutralState mb-2">
              Aplicadores (Addendum RF-25)
            </div>
            <ul className="space-y-1 mb-2">
              {appliers.map((a) => (
                <li key={a.id} className="bg-slate-50 rounded-btn px-3 py-2 text-xs">
                  {a.applier_name} — {APPLIER_TYPE_LABELS[a.applier_type]}
                </li>
              ))}
              {appliers.length === 0 && (
                <li className="text-xs text-neutralState">Nenhum aplicador marcado ainda.</li>
              )}
            </ul>
            <form onSubmit={submitApplier} className="flex flex-wrap gap-2">
              <select
                value={applierType}
                onChange={(e) => {
                  setApplierType(e.target.value as ApplierType);
                  setApplierUserId("");
                }}
                className="h-8 text-xs rounded-btn border border-slate-300 px-2"
              >
                <option value="professional">Profissional</option>
                <option value="parent">Pai/cuidador</option>
              </select>
              <select
                value={applierUserId}
                onChange={(e) => setApplierUserId(e.target.value)}
                className="h-8 text-xs rounded-btn border border-slate-300 px-2 flex-1 min-w-[140px]"
              >
                <option value="">Selecione...</option>
                {applierType === "professional"
                  ? professionals.map((p) => (
                      <option key={p.id} value={p.id}>
                        {p.name}
                      </option>
                    ))
                  : activeFamilyAccesses.map((a) => (
                      <option key={a.family_user_id} value={a.family_user_id}>
                        {a.family_user_name}
                      </option>
                    ))}
              </select>
              <button type="submit" className="h-8 rounded-btn bg-white border border-slate-300 px-3 text-xs font-medium">
                Marcar como aplicador
              </button>
            </form>
            {applierType === "parent" && activeFamilyAccesses.length === 0 && (
              <p className="text-xs text-neutralState mt-1">
                Nenhum responsável com acesso ativo ao Portal da Família para este paciente.
              </p>
            )}
            {applierError && <p className="text-danger text-xs mt-1">{applierError}</p>}
          </div>
        </div>
      )}
    </div>
  );
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("pt-BR");
}

function AreaAttachments({
  patientId,
  area,
  attachments,
  onUploaded,
}: {
  patientId: string;
  area: TreatmentArea;
  attachments: TreatmentPlanAttachment[];
  onUploaded: () => void;
}) {
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);

  async function handleUpload(e: FormEvent) {
    e.preventDefault();
    setError(null);
    if (!file) return;
    const formData = new FormData();
    formData.append("area", area);
    formData.append("file", file);
    setUploading(true);
    try {
      await apiUpload(`/patients/${patientId}/treatment-plan/attachments`, formData);
      setFile(null);
      onUploaded();
    } catch (err) {
      if (err instanceof ApiError && err.status === 415) {
        setError("Apenas arquivos PDF são aceitos.");
      } else if (err instanceof ApiError && err.status === 403) {
        setError("Você não tem permissão para importar PDF nesta área.");
      } else {
        setError("Não foi possível importar o arquivo.");
      }
    } finally {
      setUploading(false);
    }
  }

  async function openAttachment(attachmentId: string) {
    const detail = await apiRequest<TreatmentPlanAttachment & { view_url: string }>(
      `/treatment-plan/attachments/${attachmentId}`
    );
    window.open(detail.view_url, "_blank", "noopener,noreferrer");
  }

  return (
    <div className="mt-3 pt-3 border-t border-slate-100">
      <div className="text-xs font-semibold uppercase text-neutralState mb-2">PDFs anexados</div>
      {attachments.length === 0 ? (
        <p className="text-xs text-neutralState mb-2">Nenhum PDF anexado a esta área ainda.</p>
      ) : (
        <ul className="space-y-1 mb-2">
          {attachments.map((a) => (
            <li key={a.id}>
              <button
                onClick={() => openAttachment(a.id)}
                className="text-xs text-brand-blue underline text-left"
              >
                📄 {a.original_filename}
              </button>
              <span className="text-xs text-neutralState">
                {" "}
                — {a.uploaded_by_name}, {formatDate(a.uploaded_at)}
              </span>
            </li>
          ))}
        </ul>
      )}
      <form onSubmit={handleUpload} className="space-y-2">
        <input
          type="file"
          accept="application/pdf"
          onChange={(e) => setFile(e.target.files?.[0] || null)}
          className="block w-full text-xs file:mr-2 file:rounded-btn file:border-0 file:bg-slate-100 file:px-2 file:py-1 file:text-xs"
        />
        <button
          type="submit"
          disabled={!file || uploading}
          className="w-full rounded-btn bg-white border border-slate-300 px-3 py-1.5 text-xs font-medium disabled:opacity-50"
        >
          Importar PDF
        </button>
      </form>
      {error && <p className="text-danger text-xs mt-1">{error}</p>}
    </div>
  );
}

export default function TreatmentPlanPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [plan, setPlan] = useState<TreatmentPlan | null>(null);
  const [areaFilter, setAreaFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState("");

  const [showForm, setShowForm] = useState(false);
  const [area, setArea] = useState<TreatmentArea>("aba");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [criteria, setCriteria] = useState("");
  const [strategies, setStrategies] = useState("");
  const [priority, setPriority] = useState<ObjectivePriority>("medium");
  const [duplicateCandidates, setDuplicateCandidates] = useState<DuplicateCandidate[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [professionals, setProfessionals] = useState<User[]>([]);
  const [resources, setResources] = useState<ResourceItem[]>([]);
  const [familyAccesses, setFamilyAccesses] = useState<FamilyAccess[]>([]);
  const [draggedObjectiveId, setDraggedObjectiveId] = useState<string | null>(null);
  const [aiAttachmentId, setAiAttachmentId] = useState("");
  const [aiFilling, setAiFilling] = useState(false);
  const [aiError, setAiError] = useState<string | null>(null);
  const [aiGenerated, setAiGenerated] = useState(false);
  const [aiExtractionNote, setAiExtractionNote] = useState<string | null>(null);

  useEffect(() => {
    apiRequest<User[]>("/professionals").then(setProfessionals);
    apiRequest<ResourceItem[]>("/resources").then(setResources);
  }, []);

  function load() {
    if (!patientId) return;
    apiRequest<Patient>(`/patients/${patientId}`).then(setPatient);
    const params = new URLSearchParams();
    if (areaFilter) params.set("area", areaFilter);
    if (statusFilter) params.set("status", statusFilter);
    apiRequest<TreatmentPlan>(`/patients/${patientId}/treatment-plan?${params.toString()}`).then(setPlan);
    apiRequest<FamilyAccess[]>(`/patients/${patientId}/family-accesses`)
      .then(setFamilyAccesses)
      .catch(() => setFamilyAccesses([]));
  }

  useEffect(load, [patientId, areaFilter, statusFilter]);

  function resetForm() {
    setTitle("");
    setDescription("");
    setCriteria("");
    setStrategies("");
    setPriority("medium");
    setDuplicateCandidates(null);
    setError(null);
    setAiAttachmentId("");
    setAiGenerated(false);
    setAiError(null);
    setAiExtractionNote(null);
  }

  async function handleAiFill() {
    if (!aiAttachmentId) return;
    setAiError(null);
    setAiFilling(true);
    try {
      const draft = await apiRequest<ObjectiveAIFillResponse>(
        `/patients/${patientId}/treatment-plan/objectives/ai-fill`,
        { method: "POST", body: { attachment_id: aiAttachmentId } }
      );
      setTitle(draft.title);
      setDescription(draft.description);
      setCriteria(draft.criteria);
      setStrategies(draft.strategies);
      setAiGenerated(true);
      setAiExtractionNote(draft.extraction_note);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setAiError("Você não tem permissão para editar objetivos desta área.");
      } else {
        setAiError("Não foi possível gerar o rascunho a partir deste documento.");
      }
    } finally {
      setAiFilling(false);
    }
  }

  async function submitObjective(force: boolean) {
    try {
      await apiRequest(`/patients/${patientId}/treatment-plan/objectives`, {
        method: "POST",
        body: {
          area,
          title,
          description: description || null,
          criteria: criteria || null,
          strategies: strategies || null,
          priority,
          force,
          ai_generated: aiGenerated,
          ai_source_document_id: aiGenerated ? aiAttachmentId : null,
        },
      });
      setShowForm(false);
      resetForm();
      load();
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        const detail = err.detail as { duplicate_candidates: DuplicateCandidate[] };
        setDuplicateCandidates(detail.duplicate_candidates);
      } else if (err instanceof ApiError && err.status === 403) {
        setError("Você não tem permissão para editar objetivos desta área.");
      } else {
        setError("Não foi possível salvar o objetivo.");
      }
    }
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError(null);
    await submitObjective(false);
  }

  async function handleReorderDrop(area: TreatmentArea, targetObjectiveId: string) {
    if (!draggedObjectiveId || draggedObjectiveId === targetObjectiveId) return;
    const current = objectivesByArea[area] || [];
    const ids = current.map((o) => o.id);
    const fromIndex = ids.indexOf(draggedObjectiveId);
    const toIndex = ids.indexOf(targetObjectiveId);
    setDraggedObjectiveId(null);
    if (fromIndex === -1 || toIndex === -1) return;

    const reordered = [...ids];
    reordered.splice(fromIndex, 1);
    reordered.splice(toIndex, 0, draggedObjectiveId);
    await apiRequest(`/patients/${patientId}/treatment-plan/objectives/reorder`, {
      method: "POST",
      body: { area, ordered_ids: reordered },
    });
    load();
  }

  const objectivesByArea: Record<string, Objective[]> = {};
  for (const objective of plan?.objectives || []) {
    objectivesByArea[objective.area] = objectivesByArea[objective.area] || [];
    objectivesByArea[objective.area].push(objective);
  }

  const attachmentsByArea: Record<string, TreatmentPlanAttachment[]> = {};
  for (const attachment of plan?.attachments || []) {
    attachmentsByArea[attachment.area] = attachmentsByArea[attachment.area] || [];
    attachmentsByArea[attachment.area].push(attachment);
  }

  const areasToShow = areaFilter ? [areaFilter as TreatmentArea] : (Object.keys(AREA_LABELS) as TreatmentArea[]);

  return (
    <div>
      <Link to={`/patients/${patientId}`} className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para o paciente
      </Link>

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-brand-navy">Plano de Tratamento{patient ? ` — ${patient.name}` : ""}</h1>
        <button
          onClick={() => {
            resetForm();
            setShowForm((v) => !v);
          }}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
        >
          + Novo objetivo
        </button>
      </div>

      <div className="flex flex-wrap gap-3 mb-6">
        <select value={areaFilter} onChange={(e) => setAreaFilter(e.target.value)} className="h-9 rounded-btn border border-slate-300 px-2 text-sm">
          <option value="">Todas as áreas</option>
          {Object.entries(AREA_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select value={statusFilter} onChange={(e) => setStatusFilter(e.target.value)} className="h-9 rounded-btn border border-slate-300 px-2 text-sm">
          <option value="">Todos os status</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
      </div>

      {showForm && (
        <form onSubmit={handleSubmit} className="bg-white rounded-card shadow-sm p-6 mb-6 space-y-4 max-w-xl">
          {duplicateCandidates && duplicateCandidates.length > 0 && (
            <div className="bg-warning/10 border border-warning rounded-card p-4 text-sm">
              <p className="font-medium mb-2">
                Um objetivo semelhante já foi adicionado. Deseja visualizar, mesclar ou continuar?
              </p>
              <ul className="space-y-1 mb-3">
                {duplicateCandidates.map((c) => (
                  <li key={c.id}>
                    "{c.title}" — área: {AREA_LABELS[c.area]} — similaridade: {Math.round(c.similarity * 100)}%
                  </li>
                ))}
              </ul>
              <div className="flex gap-3">
                <button
                  type="button"
                  onClick={() => submitObjective(true)}
                  className="rounded-btn bg-warning text-white px-3 py-1.5 text-xs font-medium"
                >
                  Adicionar mesmo assim
                </button>
                <button
                  type="button"
                  onClick={() => setDuplicateCandidates(null)}
                  className="rounded-btn bg-white border border-slate-300 px-3 py-1.5 text-xs font-medium"
                >
                  Cancelar
                </button>
              </div>
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1">Área</label>
            <select
              value={area}
              onChange={(e) => {
                setArea(e.target.value as TreatmentArea);
                setAiAttachmentId("");
              }}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            >
              {Object.entries(AREA_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {(attachmentsByArea[area] || []).length > 0 && (
            <div className="bg-brand-grayLight rounded-card p-3">
              <label className="block text-xs font-medium mb-1">
                Preencher a partir de um PDF já anexado a esta área (RF-04)
              </label>
              <div className="flex gap-2">
                <select
                  value={aiAttachmentId}
                  onChange={(e) => setAiAttachmentId(e.target.value)}
                  className="flex-1 h-9 rounded-btn border border-slate-300 px-2 text-sm"
                >
                  <option value="">Selecione um PDF...</option>
                  {(attachmentsByArea[area] || []).map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.original_filename}
                    </option>
                  ))}
                </select>
                <button
                  type="button"
                  disabled={!aiAttachmentId || aiFilling}
                  onClick={handleAiFill}
                  className="h-9 rounded-btn bg-white border border-slate-300 px-3 text-xs font-medium disabled:opacity-50"
                >
                  {aiFilling ? "Lendo documento..." : "Preencher com IA"}
                </button>
              </div>
              {aiError && <p className="text-danger text-xs mt-1">{aiError}</p>}
              {aiGenerated && (
                <p className="text-xs text-brand-turquoise font-medium mt-2">
                  Gerado por IA — revise os campos abaixo antes de salvar.
                </p>
              )}
              {aiExtractionNote && <p className="text-xs text-warning mt-1">{aiExtractionNote}</p>}
            </div>
          )}

          <div>
            <label className="block text-sm font-medium mb-1">Objetivo</label>
            <input required value={title} onChange={(e) => setTitle(e.target.value)} className="w-full h-10 rounded-btn border border-slate-300 px-3" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Descrição</label>
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} className="w-full rounded-btn border border-slate-300 px-3 py-2" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Critério de domínio</label>
            <input value={criteria} onChange={(e) => setCriteria(e.target.value)} className="w-full h-10 rounded-btn border border-slate-300 px-3" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Estratégias</label>
            <input value={strategies} onChange={(e) => setStrategies(e.target.value)} className="w-full h-10 rounded-btn border border-slate-300 px-3" />
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">Prioridade</label>
            <select value={priority} onChange={(e) => setPriority(e.target.value as ObjectivePriority)} className="w-full h-10 rounded-btn border border-slate-300 px-3">
              {Object.entries(PRIORITY_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>
          {error && <p className="text-danger text-sm">{error}</p>}
          <div className="flex gap-3">
            <button type="submit" className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
              Salvar
            </button>
            <button type="button" onClick={() => setShowForm(false)} className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium">
              Cancelar
            </button>
          </div>
        </form>
      )}

      {patient && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
          {areasToShow.map((areaKey) => (
            <div key={areaKey} className="bg-white rounded-card shadow-sm p-4">
              <h2 className="font-semibold text-brand-navy mb-2">{AREA_LABELS[areaKey]}</h2>
              {(objectivesByArea[areaKey] || []).map((objective) => (
                <div key={objective.id}>
                  <div
                    draggable
                    onDragStart={() => setDraggedObjectiveId(objective.id)}
                    onDragOver={(e) => e.preventDefault()}
                    onDrop={() => handleReorderDrop(areaKey, objective.id)}
                    className="flex items-center justify-center h-4 text-slate-300 hover:text-slate-500 cursor-move select-none text-xs"
                    title="Arraste para reordenar a prioridade nesta área"
                  >
                    ⠿⠿⠿
                  </div>
                  <ObjectiveCard
                    objective={objective}
                    onChanged={load}
                    professionals={professionals}
                    resources={resources}
                    familyAccesses={familyAccesses}
                  />
                </div>
              ))}
              {(objectivesByArea[areaKey] || []).length === 0 && (
                <p className="text-xs text-neutralState mb-2">Nenhum objetivo nesta área ainda.</p>
              )}
              {patientId && (
                <AreaAttachments
                  patientId={patientId}
                  area={areaKey}
                  attachments={attachmentsByArea[areaKey] || []}
                  onUploaded={load}
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
