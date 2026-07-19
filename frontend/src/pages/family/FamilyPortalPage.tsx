import { FormEvent, useEffect, useState } from "react";
import { apiRequest } from "../../api/client";
import {
  FamilyAppointment,
  FamilyEvolution,
  FamilyGuidance,
  FamilyMessage,
  FamilyMyAccess,
  WhiteLabelSettings,
} from "../../types";

type TabKey = "evolution" | "appointments" | "guidance" | "materials" | "messages";

const TAB_LABELS: Record<TabKey, string> = {
  evolution: "Evolução",
  appointments: "Agenda",
  guidance: "Orientações",
  materials: "Materiais",
  messages: "Mensagens",
};

function tabsFor(access: FamilyMyAccess): TabKey[] {
  const tabs: TabKey[] = [];
  if (access.can_view_evolution_charts) tabs.push("evolution");
  if (access.can_view_upcoming_appointments) tabs.push("appointments");
  if (access.can_view_team_guidance) tabs.push("guidance");
  if (access.can_view_home_materials) tabs.push("materials");
  if (access.can_use_messaging) tabs.push("messages");
  return tabs;
}

function formatDateTime(value: string) {
  return new Date(value).toLocaleString("pt-BR");
}

export default function FamilyPortalPage() {
  const [accesses, setAccesses] = useState<FamilyMyAccess[]>([]);
  const [patientId, setPatientId] = useState<string>("");
  const [tab, setTab] = useState<TabKey | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [branding, setBranding] = useState<WhiteLabelSettings | null>(null);

  useEffect(() => {
    apiRequest<FamilyMyAccess[]>("/family-portal/my-accesses").then((data) => {
      setAccesses(data);
      setLoaded(true);
      if (data.length > 0) setPatientId(data[0].patient_id);
    });
  }, []);

  useEffect(() => {
    if (!patientId) return;
    apiRequest<WhiteLabelSettings>(`/family-portal/patients/${patientId}/branding`).then(setBranding);
  }, [patientId]);

  const currentAccess = accesses.find((a) => a.patient_id === patientId) ?? null;
  const tabs = currentAccess ? tabsFor(currentAccess) : [];

  useEffect(() => {
    if (tabs.length > 0 && (tab === null || !tabs.includes(tab))) {
      setTab(tabs[0]);
    }
    if (tabs.length === 0) setTab(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [patientId, currentAccess]);

  if (!loaded) return <p className="text-neutralState p-8">Carregando...</p>;

  if (accesses.length === 0) {
    return (
      <div className="p-8">
        <div className="bg-white rounded-card shadow-sm p-8 text-center text-neutralState max-w-lg mx-auto">
          Você ainda não tem acesso liberado a nenhum paciente no Portal da Família. Fale com a equipe
          responsável pelo atendimento.
        </div>
      </div>
    );
  }

  return (
    <div className="p-8 max-w-3xl mx-auto">
      {branding?.enabled && (
        <div
          className="flex items-center gap-3 rounded-card px-4 py-3 mb-4 text-white"
          style={{ backgroundColor: branding.brand_color ?? "#1D4ED8" }}
        >
          {branding.logo_url && (
            // eslint-disable-next-line jsx-a11y/alt-text
            <img src={branding.logo_url} className="h-8 w-8 rounded object-contain bg-white/10" />
          )}
          <span className="font-semibold">{branding.display_name ?? "Portal da Família"}</span>
        </div>
      )}
      <h1 className="text-2xl font-bold text-brand-navy mb-1">Portal da Família</h1>
      <p className="text-sm text-neutralState mb-1">
        Você só enxerga aqui o que foi explicitamente liberado pela equipe clínica.
      </p>
      <p className="text-xs text-neutralState mb-6">{branding?.enabled ? "Powered by Behavior Hub" : ""}</p>

      {accesses.length > 1 && (
        <select
          value={patientId}
          onChange={(e) => setPatientId(e.target.value)}
          className="h-10 rounded-btn border border-slate-300 px-3 mb-4"
        >
          {accesses.map((a) => (
            <option key={a.patient_id} value={a.patient_id}>
              {a.patient_name}
            </option>
          ))}
        </select>
      )}

      {tabs.length === 0 ? (
        <div className="bg-white rounded-card shadow-sm p-8 text-center text-neutralState">
          Nenhuma categoria de dados foi liberada para este paciente ainda.
        </div>
      ) : (
        <>
          <div className="flex gap-2 mb-6 border-b border-slate-200">
            {tabs.map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
                  tab === t ? "border-brand-turquoise text-brand-navy" : "border-transparent text-neutralState"
                }`}
              >
                {TAB_LABELS[t]}
              </button>
            ))}
          </div>

          {tab === "evolution" && <EvolutionTab patientId={patientId} />}
          {tab === "appointments" && <AppointmentsTab patientId={patientId} />}
          {tab === "guidance" && <GuidanceTab patientId={patientId} />}
          {tab === "materials" && <MaterialsTab patientId={patientId} />}
          {tab === "messages" && <MessagesTab patientId={patientId} />}
        </>
      )}
    </div>
  );
}

function EvolutionTab({ patientId }: { patientId: string }) {
  const [data, setData] = useState<FamilyEvolution | null>(null);

  useEffect(() => {
    setData(null);
    apiRequest<FamilyEvolution>(`/family-portal/patients/${patientId}/evolution`).then(setData);
  }, [patientId]);

  if (!data) return <p className="text-neutralState">Carregando...</p>;

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-card shadow-sm p-6">
        <h2 className="font-semibold text-brand-navy mb-3">Evolução por treino</h2>
        {data.line.length === 0 && <p className="text-sm text-neutralState">Sem dados suficientes ainda.</p>}
        {data.line.map((series) => (
          <div key={series.training_id} className="mb-3 text-sm">
            <div className="font-medium">{series.training_title}</div>
            <div className="text-neutralState">
              {series.points.map((p) => `${p.date}: ${p.accuracy_pct ?? "-"}%`).join(" · ")}
            </div>
          </div>
        ))}
      </div>
      <div className="bg-white rounded-card shadow-sm p-6">
        <h2 className="font-semibold text-brand-navy mb-3">Visão geral por área</h2>
        {data.radar.map((r) => (
          <div key={r.area} className="flex justify-between text-sm py-1">
            <span>{r.area}</span>
            <span>{r.accuracy_pct !== null ? `${r.accuracy_pct}%` : "dados insuficientes"}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

function AppointmentsTab({ patientId }: { patientId: string }) {
  const [appointments, setAppointments] = useState<FamilyAppointment[]>([]);

  useEffect(() => {
    apiRequest<FamilyAppointment[]>(`/family-portal/patients/${patientId}/appointments`).then(setAppointments);
  }, [patientId]);

  return (
    <div className="bg-white rounded-card shadow-sm divide-y divide-slate-100">
      {appointments.length === 0 && <p className="p-6 text-center text-neutralState">Nenhum agendamento futuro.</p>}
      {appointments.map((a) => (
        <div key={a.id} className="px-4 py-3 flex justify-between text-sm">
          <span>{formatDateTime(a.scheduled_start)}</span>
          <span className="text-neutralState">{a.professional_name}</span>
        </div>
      ))}
    </div>
  );
}

function GuidanceTab({ patientId }: { patientId: string }) {
  const [guidance, setGuidance] = useState<FamilyGuidance[]>([]);

  useEffect(() => {
    apiRequest<FamilyGuidance[]>(`/family-portal/patients/${patientId}/guidance`).then(setGuidance);
  }, [patientId]);

  return (
    <div className="space-y-4">
      {guidance.length === 0 && (
        <div className="bg-white rounded-card shadow-sm p-6 text-center text-neutralState">
          Nenhuma orientação publicada ainda.
        </div>
      )}
      {guidance.map((g) => (
        <div key={g.id} className="bg-white rounded-card shadow-sm p-6">
          <div className="text-xs text-neutralState mb-2">
            {g.period_start} a {g.period_end}
          </div>
          <p className="text-sm whitespace-pre-wrap">{g.content}</p>
        </div>
      ))}
    </div>
  );
}

function MaterialsTab({ patientId }: { patientId: string }) {
  const [materials, setMaterials] = useState<{ id: string; resource_title: string; resource_type: string }[]>([]);

  useEffect(() => {
    apiRequest<{ id: string; resource_title: string; resource_type: string }[]>(
      `/family-portal/patients/${patientId}/materials`
    ).then(setMaterials);
  }, [patientId]);

  return (
    <div className="bg-white rounded-card shadow-sm divide-y divide-slate-100">
      {materials.length === 0 && <p className="p-6 text-center text-neutralState">Nenhum material recomendado ainda.</p>}
      {materials.map((m) => (
        <div key={m.id} className="px-4 py-3 text-sm">
          {m.resource_title}
        </div>
      ))}
    </div>
  );
}

function MessagesTab({ patientId }: { patientId: string }) {
  const [messages, setMessages] = useState<FamilyMessage[]>([]);
  const [body, setBody] = useState("");

  function load() {
    apiRequest<FamilyMessage[]>(`/family-portal/patients/${patientId}/messages`).then(setMessages);
  }

  useEffect(load, [patientId]);

  async function handleSend(e: FormEvent) {
    e.preventDefault();
    if (!body.trim()) return;
    await apiRequest(`/family-portal/patients/${patientId}/messages`, { method: "POST", body: { body } });
    setBody("");
    load();
  }

  return (
    <div className="bg-white rounded-card shadow-sm p-6 flex flex-col h-[28rem]">
      <div className="flex-1 overflow-y-auto space-y-3 mb-4">
        {messages.length === 0 && <p className="text-center text-neutralState">Nenhuma mensagem ainda.</p>}
        {messages.map((m) => (
          <div key={m.id} className="text-sm">
            <div className="font-medium">{m.sender_name}</div>
            <div className="text-neutralState">{m.body}</div>
          </div>
        ))}
      </div>
      <form onSubmit={handleSend} className="flex gap-2">
        <input
          value={body}
          onChange={(e) => setBody(e.target.value)}
          placeholder="Escreva uma mensagem..."
          className="flex-1 h-10 rounded-btn border border-slate-300 px-3"
        />
        <button type="submit" className="h-10 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium">
          Enviar
        </button>
      </form>
    </div>
  );
}
