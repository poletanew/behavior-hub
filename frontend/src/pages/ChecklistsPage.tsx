import { FormEvent, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiRequest } from "../api/client";
import EmptyState from "../components/EmptyState";
import { ChecklistAnswerType, ChecklistResponseDetail, ChecklistTemplate, Patient } from "../types";

const ANSWER_TYPE_LABELS: Record<ChecklistAnswerType, string> = {
  yes_no: "Sim/Não",
  scale: "Escala (1-5)",
  short_text: "Texto curto",
};

function ResponseDetailCard({ response }: { response: ChecklistResponseDetail }) {
  const scaleItems = response.items.filter((i) => i.answer_type === "scale");
  return (
    <div className="bg-white rounded-card shadow-sm p-6 mb-6">
      <h3 className="font-semibold text-brand-navy mb-1">{response.template_title}</h3>
      <p className="text-xs text-neutralState mb-4">{new Date(response.applied_at).toLocaleString("pt-BR")}</p>

      <table className="w-full text-sm mb-4">
        <tbody>
          {response.items.map((item) => (
            <tr key={item.question_id} className="border-b border-slate-50 last:border-0">
              <td className="py-2 pr-4 text-neutralState">{item.question_text}</td>
              <td className="py-2 font-medium">
                {item.answer_type === "yes_no" ? (item.value ? "Sim" : "Não") : String(item.value)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {scaleItems.length > 0 && (
        <ResponsiveContainer width="100%" height={Math.max(120, scaleItems.length * 40)}>
          <BarChart data={scaleItems.map((i) => ({ name: i.question_text, value: Number(i.value) }))} layout="vertical" margin={{ left: 24 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" domain={[0, 5]} />
            <YAxis type="category" dataKey="name" width={220} tick={{ fontSize: 11 }} />
            <Tooltip />
            <Bar dataKey="value" fill="#14B8A6" />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}

export default function ChecklistsPage() {
  const { patientId } = useParams<{ patientId: string }>();
  const [patient, setPatient] = useState<Patient | null>(null);
  const [templates, setTemplates] = useState<ChecklistTemplate[]>([]);
  const [responses, setResponses] = useState<ChecklistResponseDetail[]>([]);

  const [showBuilder, setShowBuilder] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [newQuestions, setNewQuestions] = useState<{ text: string; answer_type: ChecklistAnswerType }[]>([
    { text: "", answer_type: "yes_no" },
  ]);

  const [showApply, setShowApply] = useState(false);
  const [templateId, setTemplateId] = useState("");
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const [applyError, setApplyError] = useState<string | null>(null);

  function load() {
    if (!patientId) return;
    apiRequest<Patient>(`/patients/${patientId}`).then(setPatient);
    apiRequest<ChecklistResponseDetail[]>(`/patients/${patientId}/checklist-responses`).then(setResponses);
  }

  useEffect(load, [patientId]);
  useEffect(() => {
    apiRequest<ChecklistTemplate[]>("/checklist-templates").then(setTemplates);
  }, []);

  const selectedTemplate = templates.find((t) => t.id === templateId);

  function addQuestionRow() {
    setNewQuestions((prev) => [...prev, { text: "", answer_type: "yes_no" }]);
  }

  function updateQuestionRow(index: number, field: "text" | "answer_type", value: string) {
    setNewQuestions((prev) => prev.map((q, i) => (i === index ? { ...q, [field]: value } : q)));
  }

  async function handleCreateTemplate(e: FormEvent) {
    e.preventDefault();
    const questions = newQuestions.filter((q) => q.text.trim());
    const created = await apiRequest<ChecklistTemplate>("/checklist-templates", {
      method: "POST",
      body: { title: newTitle, questions },
    });
    setTemplates((prev) => [...prev, created]);
    setNewTitle("");
    setNewQuestions([{ text: "", answer_type: "yes_no" }]);
    setShowBuilder(false);
  }

  async function handleApply(e: FormEvent) {
    e.preventDefault();
    if (!patientId || !selectedTemplate) return;
    setApplyError(null);
    try {
      await apiRequest(`/patients/${patientId}/checklist-responses`, {
        method: "POST",
        body: {
          template_id: templateId,
          answers: selectedTemplate.questions.map((q) => ({
            question_id: q.id,
            value:
              q.answer_type === "yes_no"
                ? answers[q.id] === "true"
                : q.answer_type === "scale"
                  ? Number(answers[q.id] || 0)
                  : answers[q.id] || "",
          })),
        },
      });
      setShowApply(false);
      setTemplateId("");
      setAnswers({});
      load();
    } catch {
      setApplyError("Não foi possível aplicar o checklist. Responda todas as perguntas.");
    }
  }

  if (!patient) return <p className="text-neutralState">Carregando...</p>;

  return (
    <div>
      <Link to={`/patients/${patientId}`} className="text-sm text-brand-blue underline mb-4 inline-block">
        ← Voltar para {patient.name}
      </Link>

      <div className="flex items-center justify-between mb-2">
        <h1 className="text-2xl font-bold text-brand-navy">Checklists Personalizados — {patient.name}</h1>
        <div className="flex gap-2">
          <button
            onClick={() => setShowBuilder((v) => !v)}
            className="rounded-btn bg-white border border-slate-300 px-4 py-2 text-sm font-medium"
          >
            + Novo template
          </button>
          <button
            onClick={() => setShowApply((v) => !v)}
            className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium"
          >
            Aplicar checklist
          </button>
        </div>
      </div>
      <p className="text-sm text-neutralState mb-6">
        Monte um checklist uma vez (pergunta + tipo de resposta) e reaplique em vários pacientes — por
        exemplo, rotina de sono ou comportamento alimentar.
      </p>

      {showBuilder && (
        <form onSubmit={handleCreateTemplate} className="bg-white rounded-card shadow-sm p-6 mb-6 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Título do checklist</label>
            <input
              required
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            />
          </div>
          <div className="space-y-2">
            {newQuestions.map((q, index) => (
              <div key={index} className="flex gap-2 items-center">
                <input
                  required
                  placeholder={`Pergunta ${index + 1}`}
                  value={q.text}
                  onChange={(e) => updateQuestionRow(index, "text", e.target.value)}
                  className="flex-1 h-9 rounded-btn border border-slate-300 px-2 text-sm"
                />
                <select
                  value={q.answer_type}
                  onChange={(e) => updateQuestionRow(index, "answer_type", e.target.value)}
                  className="h-9 rounded-btn border border-slate-300 px-2 text-sm"
                >
                  {Object.entries(ANSWER_TYPE_LABELS).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </div>
            ))}
          </div>
          <button type="button" onClick={addQuestionRow} className="text-xs text-brand-blue underline">
            + Adicionar pergunta
          </button>
          <div>
            <button type="submit" className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
              Salvar template
            </button>
          </div>
        </form>
      )}

      {showApply && (
        <form onSubmit={handleApply} className="bg-white rounded-card shadow-sm p-6 mb-6 space-y-4">
          <div>
            <label className="block text-sm font-medium mb-1">Checklist</label>
            <select
              required
              value={templateId}
              onChange={(e) => {
                setTemplateId(e.target.value);
                setAnswers({});
              }}
              className="w-full h-10 rounded-btn border border-slate-300 px-3"
            >
              <option value="">Selecione...</option>
              {templates.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.title}
                </option>
              ))}
            </select>
          </div>
          {selectedTemplate?.questions.map((q) => (
            <div key={q.id}>
              <label className="block text-sm font-medium mb-1">{q.text}</label>
              {q.answer_type === "yes_no" ? (
                <select
                  required
                  value={answers[q.id] ?? ""}
                  onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
                  className="h-9 rounded-btn border border-slate-300 px-2 text-sm"
                >
                  <option value="">Selecione...</option>
                  <option value="true">Sim</option>
                  <option value="false">Não</option>
                </select>
              ) : q.answer_type === "scale" ? (
                <input
                  type="number"
                  min={1}
                  max={5}
                  required
                  value={answers[q.id] ?? ""}
                  onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
                  className="h-9 w-24 rounded-btn border border-slate-300 px-2 text-sm"
                />
              ) : (
                <input
                  required
                  value={answers[q.id] ?? ""}
                  onChange={(e) => setAnswers((prev) => ({ ...prev, [q.id]: e.target.value }))}
                  className="w-full h-9 rounded-btn border border-slate-300 px-2 text-sm"
                />
              )}
            </div>
          ))}
          {applyError && <p className="text-danger text-sm">{applyError}</p>}
          {selectedTemplate && (
            <button type="submit" className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium">
              Aplicar
            </button>
          )}
        </form>
      )}

      {responses.length === 0 ? (
        <EmptyState icon="📋" message="Nenhum checklist aplicado a este paciente ainda." />
      ) : (
        responses.map((r) => <ResponseDetailCard key={r.id} response={r} />)
      )}
    </div>
  );
}
