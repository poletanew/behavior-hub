import React, { useState, useMemo, useEffect, useCallback, useRef } from "react";
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  RadarChart, PolarGrid, PolarAngleAxis, Radar,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend
} from "recharts";
import {
  LayoutDashboard, Users, ClipboardList, BookOpen, ListChecks,
  BarChart3, UserPlus, FolderOpen, CreditCard, Plus, Search,
  ChevronRight, ChevronLeft, X, Check, AlertTriangle, Clock, Trash2, RotateCcw,
  Loader2, ArchiveX, ClipboardCheck, UserCog, History, KeyRound,
  Sparkles, Link2, FileUp, LogIn, PartyPopper, Send, MessageCircle, CalendarDays, MapPin, Phone
} from "lucide-react";

/* ---------- Brand tokens (Behavior Hub) ---------- */
const C = {
  blueDeep: "#1D4ED8", blueDeepDark: "#0f2557", blueLight: "#3B82F6",
  teal: "#14B8A6", green: "#22C55E", greenLight: "#84CC16", purple: "#8B5CF6",
  graphite: "#334155", grayLight: "#F1F5F9", white: "#FFFFFF",
  orange: "#F59E0B", red: "#EF4444", neutral: "#64748B", border: "#E2E8F0",
};

const STORAGE_KEY = "behavior_hub_state_v2";
const RETENTION_DAYS = 60;
const AREAS = ["Psicologia", "ABA", "Fonoaudiologia", "Terapia Ocupacional"];

/* Estrutura genérica dos protocolos de avaliação — só domínios, quantidade de itens por
   domínio e escala de pontuação. Não contém o texto dos itens (protegido/licenciado);
   o profissional consulta o material licenciado dele (PDF/planilha própria) e só lança
   a pontuação aqui. */
const ASSESSMENT_PROTOCOLS = {
  vbmapp: {
    label: "VB-MAPP Milestones",
    maxPerItem: 1,
    scoreOptions: [0, 0.5, 1, "NA"],
    levels: [
      { id: 1, label: "Nível 1 (0–18 meses)", domains: ["Mando", "Tato", "Ouvinte", "Ecoico", "Imitação Motora", "Comportamento Vocal Espontâneo", "VPS-MTS", "Brincar Independente", "Brincadeira Social"].map(name => ({ name, items: 5 })) },
      { id: 2, label: "Nível 2 (18–30 meses)", domains: ["Mando", "Tato", "Ouvinte", "LRFFC - Ouvinte", "Ecoico", "Intraverbal", "Imitação Motora", "VPS-MTS", "Brincar Independente", "Brincadeira Social", "Habilidades de Grupo", "Estrutura Linguística"].map(name => ({ name, items: 5 })) },
      { id: 3, label: "Nível 3 (30–48 meses)", domains: ["Mando", "Tato", "Ouvinte", "LRFFC - Ouvinte", "Intraverbal", "VPS-MTS", "Brincar Independente", "Brincadeira Social", "Habilidades de Grupo", "Estrutura Linguística", "Leitura", "Escrita", "Matemática"].map(name => ({ name, items: 5 })) },
    ],
  },
  sociallysavvy: {
    label: "Socially Savvy Checklist",
    maxPerItem: 3,
    scoreOptions: [0, 1, 2, 3, "NA"],
    levels: [
      { id: 1, label: "Checklist completo", domains: [
        { name: "Atenção Compartilhada", items: 9 },
        { name: "Brincadeira Social", items: 24 },
        { name: "Autorregulação", items: 18 },
        { name: "Social/Emocional", items: 6 },
        { name: "Linguagem Social", items: 24 },
        { name: "Comportamento de Grupo/Sala de Aula", items: 23 },
        { name: "Linguagem Social Não-Verbal", items: 6 },
      ] },
    ],
  },
};

const NAV_ITEMS = [
  { id: "area-trabalho", label: "Área de Trabalho", icon: LayoutDashboard },
  { id: "pacientes", label: "Pacientes", icon: Users },
  { id: "atendimentos", label: "Atendimentos", icon: ClipboardList },
  { id: "agenda", label: "Agenda", icon: CalendarDays },
  { id: "biblioteca", label: "Biblioteca de Treino", icon: BookOpen },
  { id: "planos-tratamento", label: "Treatment Plans", icon: ListChecks },
  { id: "avaliacoes", label: "Avaliações", icon: ClipboardCheck },
  { id: "reports", label: "Reports", icon: BarChart3 },
  { id: "aba", label: "ABA", icon: UserCog },
  { id: "deleted", label: "Deleted Data", icon: ArchiveX },
  { id: "profissionais", label: "Profissionais", icon: UserPlus },
  { id: "recursos", label: "Recursos", icon: FolderOpen },
  { id: "auditoria", label: "Auditoria", icon: History },
  { id: "planos", label: "Planos", icon: CreditCard },
  { id: "seguranca", label: "Segurança", icon: KeyRound },
];

const defaultState = {
  currentUser: { name: "", role: "Administrador" },
  patients: [
    { id: "p1", name: "Maria Souza", age: 6, diagnosis: "TEA nível 1", responsavel: "Não informado", endereco: "", telefone: "", escola: "Escola Girassol", turno: "Manhã", professional: "Ana Ribeiro (Psicóloga)", status: "Ativo", deletedAt: null },
    { id: "p2", name: "João Pedro", age: 8, diagnosis: "TDAH", responsavel: "Não informado", endereco: "", telefone: "", escola: "Colégio Vitória", turno: "Tarde", professional: "Carlos Lima (ABA)", status: "Ativo", deletedAt: null },
    { id: "p3", name: "Beatriz Alves", age: 5, diagnosis: "TEA nível 2", responsavel: "Não informado", endereco: "", telefone: "", escola: "", turno: "Integral", professional: "Ana Ribeiro (Psicóloga)", status: "Ativo", deletedAt: null },
  ],
  sessions: [
    {
      id: "s1", patientId: "p1", patient: "Maria Souza", professional: "Ana Ribeiro", specialty: "Psicóloga infantil",
      date: "16/07/2026 14:00", createdAt: "2026-07-16T14:00:00", trainingTitle: "Aguardar por 30 segundos",
      trials: [{ id: "t1", help: "Independente", result: "correta" }, { id: "t2", help: "Ajuda verbal", result: "correta" }, { id: "t3", help: "Ajuda gestual", result: "incorreta" }, { id: "t4", help: "Independente", result: "correta" }, { id: "t5", help: "Independente", result: "correta" }],
      deletedAt: null,
    },
    {
      id: "s2", patientId: "p2", patient: "João Pedro", professional: "Carlos Lima", specialty: "Analista do Comportamento",
      date: "16/07/2026 10:30", createdAt: "2026-07-16T10:30:00", trainingTitle: "Comunicação funcional",
      trials: [{ id: "t6", help: "Independente", result: "correta" }, { id: "t7", help: "Ajuda verbal", result: "incorreta" }, { id: "t8", help: "Independente", result: "correta" }],
      deletedAt: null,
    },
    {
      id: "s3", patientId: "p1", patient: "Maria Souza", professional: "Ana Ribeiro", specialty: "Psicóloga infantil",
      date: "20/07/2026 09:00", createdAt: "2026-07-20T09:00:00", trainingTitle: "Contato visual ao ser chamado",
      trials: [{ id: "t9", help: "Independente", result: "correta" }, { id: "t10", help: "Independente", result: "correta" }, { id: "t11", help: "Ajuda gestual", result: "parcial" }],
      deletedAt: null,
    },
    {
      id: "s4", patientId: "p3", patient: "Beatriz Alves", professional: "Ana Ribeiro", specialty: "Psicóloga infantil",
      date: "21/07/2026 11:00", createdAt: "2026-07-21T11:00:00", trainingTitle: "Tomada de turno em jogo simples",
      trials: [{ id: "t12", help: "Ajuda verbal", result: "incorreta" }, { id: "t13", help: "Ajuda gestual", result: "parcial" }, { id: "t14", help: "Ajuda verbal", result: "correta" }],
      deletedAt: null,
    },
    {
      id: "s5", patientId: "p2", patient: "João Pedro", professional: "Carlos Lima", specialty: "Analista do Comportamento",
      date: "23/07/2026 15:30", createdAt: "2026-07-23T15:30:00", trainingTitle: "Aguardar por 30 segundos",
      trials: [{ id: "t15", help: "Independente", result: "correta" }, { id: "t16", help: "Independente", result: "correta" }, { id: "t17", help: "Ajuda verbal", result: "correta" }, { id: "t18", help: "Independente", result: "nao_respondida" }],
      deletedAt: null,
    },
  ],
  trainings: [
    { id: "tr1", title: "Aguardar por 30 segundos", area: "ABA", ageRange: "4-8 anos", custom: false },
    { id: "tr2", title: "Contato visual ao ser chamado", area: "Comunicação", ageRange: "3-6 anos", custom: false },
    { id: "tr3", title: "Pedido funcional com gesto", area: "Comunicação", ageRange: "3-7 anos", custom: false },
    { id: "tr5", title: "Comunicação funcional", area: "Comunicação", ageRange: "3-8 anos", custom: false },
    { id: "tr4", title: "Tomada de turno em jogo simples", area: "Social", ageRange: "5-9 anos", custom: false },
  ],
  trainingLinks: [],
  objectives: [
    { id: "o1", patientId: "p1", area: "Psicologia", title: "Identificar necessidades e emoções", description: "", strategy: "", masteryCriteria: "", status: "success", aiGenerated: false },
    { id: "o2", patientId: "p1", area: "ABA", title: "Treino de mando funcional", description: "", strategy: "", masteryCriteria: "", status: "success", aiGenerated: false },
    { id: "o3", patientId: "p1", area: "ABA", title: "Aguardar por 30 segundos com comportamento seguro", description: "Aumento gradual do tempo de espera.", strategy: "Previsibilidade visual e reforço diferencial.", masteryCriteria: "80% de respostas independentes em 3 sessões consecutivas.", status: "warn", aiGenerated: false },
  ],
  planAttachments: [],
  auditLog: [],
  resources: [
    { id: "r1", title: "Rotina visual — hora do banho", type: "PDF", age: "3-7 anos", aiGenerated: false },
    { id: "r2", title: "História social — esperar a vez", type: "PDF", age: "4-9 anos", aiGenerated: false },
    { id: "r3", title: "Cartões de comunicação básica", type: "Imagem", age: "2-6 anos", aiGenerated: false },
  ],
  atAssignments: [],
  assessments: [],
  appointments: [
    { id: "ap1", patientId: "p1", patient: "Maria Souza", professional: "Ana Ribeiro", room: "Sala 1", date: "2026-07-24", time: "09:00", status: "confirmado" },
    { id: "ap2", patientId: "p2", patient: "João Pedro", professional: "Carlos Lima", room: "Sala 2", date: "2026-07-24", time: "10:30", status: "agendado" },
    { id: "ap3", patientId: "p3", patient: "Beatriz Alves", professional: "Ana Ribeiro", room: "Sala 1", date: "2026-07-24", time: "14:00", status: "agendado" },
  ],
  familyMessages: [
    { id: "fm1", patientId: "p1", sender: "equipe", text: "Oi! Hoje a Maria treinou espera com bastante independência 🎉" },
    { id: "fm2", patientId: "p1", sender: "familia", text: "Que ótimo! Em casa ela também está esperando melhor na fila do mercado." },
  ],
};

/* ---------- storage helpers ---------- */
async function loadState() {
  try {
    const res = await window.storage.get(STORAGE_KEY, false);
    if (res && res.value) {
      const parsed = JSON.parse(res.value);
      return { ...defaultState, ...parsed };
    }
  } catch (e) { /* key doesn't exist yet */ }
  return defaultState;
}
async function saveState(state) {
  try {
    await window.storage.set(STORAGE_KEY, JSON.stringify(state), false);
    return true;
  } catch (e) {
    console.error("Falha ao salvar:", e);
    return false;
  }
}

/* ---------- AI helper (real call — no key needed in this environment) ---------- */
async function askClaude(systemPrompt, userPrompt) {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-6",
      max_tokens: 1000,
      system: systemPrompt,
      messages: [{ role: "user", content: userPrompt }],
    }),
  });
  const data = await response.json();
  const block = (data.content || []).find(b => b.type === "text");
  if (!block) throw new Error("Resposta vazia da IA");
  const cleaned = block.text.replace(/```json|```/g, "").trim();
  return JSON.parse(cleaned);
}

const CHAT_SYSTEM_PROMPT = "Você é a IA do Behavior Hub, assistente virtual dentro do sistema para profissionais de terapia infantil (ABA, Psicologia, Fonoaudiologia, Terapia Ocupacional, Psicopedagogia e áreas afins). Ajude com dúvidas sobre como usar o sistema, sugestões de estratégias e treinos, e dúvidas gerais sobre análise do comportamento aplicada. Responda em português do Brasil, de forma objetiva e acolhedora. Nunca emita diagnóstico, nunca afirme causalidade clínica definitiva, e deixe claro quando uma sugestão precisa de revisão do profissional antes de ser aplicada a um paciente real.";

async function askClaudeChat(messages) {
  const response = await fetch("https://api.anthropic.com/v1/messages", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      model: "claude-sonnet-4-6",
      max_tokens: 1000,
      system: CHAT_SYSTEM_PROMPT,
      messages: messages.map(m => ({ role: m.role, content: m.content })),
    }),
  });
  const data = await response.json();
  const block = (data.content || []).find(b => b.type === "text");
  if (!block) throw new Error("Resposta vazia da IA");
  return block.text;
}

function accuracyOf(trials) {
  const valid = (trials || []).filter(t => t.result !== "nao_respondida");
  if (valid.length === 0) return 0;
  const correct = valid.filter(t => t.result === "correta").length;
  return Math.round((correct / valid.length) * 1000) / 10;
}
function daysLeft(deletedAt) {
  const elapsed = (Date.now() - new Date(deletedAt).getTime()) / (1000 * 60 * 60 * 24);
  return Math.max(0, Math.ceil(RETENTION_DAYS - elapsed));
}
function uid(prefix) { return prefix + "_" + Math.random().toString(36).slice(2, 9); }
function nowStamp() { return new Date().toLocaleString("pt-BR"); }

/* ---------- shared UI bits ---------- */
function Badge({ children, tone = "neutral" }) {
  const tones = { success: C.green, info: C.blueLight, warn: C.orange, error: C.red, neutral: C.neutral, purple: C.purple };
  return <span style={{ background: tones[tone], color: "#fff", fontSize: 11, fontWeight: 700, padding: "3px 10px", borderRadius: 999, letterSpacing: 0.3, whiteSpace: "nowrap", display: "inline-flex", alignItems: "center", gap: 4 }}>{children}</span>;
}
function Card({ children, style, onClick }) {
  return <div onClick={onClick} style={{ background: "#fff", borderRadius: 14, border: `1px solid ${C.border}`, boxShadow: "0 1px 3px rgba(15,37,87,0.06)", padding: 20, cursor: onClick ? "pointer" : "default", transition: "box-shadow .15s", ...style }}>{children}</div>;
}
function Button({ children, variant = "primary", onClick, style, icon: Icon, disabled, loading }) {
  const base = { display: "inline-flex", alignItems: "center", gap: 6, fontSize: 13.5, fontWeight: 600, padding: "9px 16px", borderRadius: 9, cursor: disabled ? "not-allowed" : "pointer", border: "1px solid transparent", opacity: disabled ? 0.5 : 1 };
  const variants = {
    primary: { background: C.teal, color: "#fff" },
    secondary: { background: "#fff", color: C.graphite, border: `1px solid ${C.border}` },
    destructive: { background: C.red, color: "#fff" },
    ghost: { background: "transparent", color: C.blueDeep },
    ai: { background: C.purple, color: "#fff" },
  };
  return (
    <button disabled={disabled || loading} onClick={onClick} style={{ ...base, ...variants[variant], ...style }}
      onMouseOver={e => !disabled && (e.currentTarget.style.opacity = 0.88)}
      onMouseOut={e => !disabled && (e.currentTarget.style.opacity = 1)}>
      {loading ? <Loader2 size={15} className="spin" /> : Icon && <Icon size={15} />} {children}
    </button>
  );
}
function EmptyState({ title, cta, onClick, emoji = "🌱" }) {
  return (
    <div style={{ textAlign: "center", padding: "40px 20px", color: C.neutral }}>
      <div style={{ fontSize: 30, marginBottom: 6 }}>{emoji}</div>
      <p style={{ marginBottom: 16, fontSize: 14 }}>{title}</p>
      {cta && <Button icon={Plus} onClick={onClick}>{cta}</Button>}
    </div>
  );
}
const inputStyle = { width: "100%", padding: "9px 12px", borderRadius: 8, border: `1px solid ${C.border}`, fontSize: 13.5, fontFamily: "inherit" };
function Field({ label, children }) {
  return <div style={{ marginBottom: 12 }}><label style={{ display: "block", fontSize: 12.5, fontWeight: 600, color: C.graphite, marginBottom: 5 }}>{label}</label>{children}</div>;
}
function Modal({ title, children, onClose, wide }) {
  return (
    <div style={{ position: "fixed", inset: 0, background: "rgba(15,37,87,0.4)", display: "flex", alignItems: "center", justifyContent: "center", zIndex: 50, padding: 16 }} onClick={onClose}>
      <div style={{ background: "#fff", borderRadius: 14, padding: 24, width: wide ? 620 : 440, maxWidth: "92vw", maxHeight: "88vh", overflowY: "auto" }} onClick={e => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
          <h3 style={{ margin: 0, fontSize: 16, color: C.blueDeepDark }}>{title}</h3>
          <X size={18} style={{ cursor: "pointer", color: C.neutral }} onClick={onClose} />
        </div>
        {children}
      </div>
    </div>
  );
}
function ConfirmModal({ title, message, onConfirm, onClose, confirmLabel = "Confirmar" }) {
  return (
    <Modal title={title} onClose={onClose}>
      <p style={{ fontSize: 13.5, color: C.graphite, lineHeight: 1.5 }}>{message}</p>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 18 }}>
        <Button variant="secondary" onClick={onClose}>Cancelar</Button>
        <Button variant="destructive" onClick={onConfirm}>{confirmLabel}</Button>
      </div>
    </Modal>
  );
}
function AiDraftNote() {
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 6, background: "#F5F3FF", border: `1px solid ${C.purple}`, borderRadius: 8, padding: "6px 10px", marginBottom: 10, fontSize: 11.5, color: C.purple, fontWeight: 700 }}>
      <Sparkles size={13} /> Gerado por IA — revise antes de salvar
    </div>
  );
}
function Logo({ compact, dark }) {
  const nodes = [[30, 8], [10, 22], [4, 44], [10, 66], [30, 80], [30, 44]];
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
      <svg width={compact ? 26 : 34} height={compact ? 26 : 34} viewBox="0 0 60 88">
        <defs><linearGradient id="bhGrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor={C.blueDeep} /><stop offset="100%" stopColor={C.green} /></linearGradient></defs>
        <g stroke="url(#bhGrad)" strokeWidth="3" fill="none">
          <path d="M30 44 L30 8 L38 8 Q54 8 54 26 Q54 44 38 44" />
          <path d="M30 44 Q54 44 54 62 Q54 80 38 80 L30 80 L30 44" />
          {nodes.map(([x, y], i) => <line key={i} x1="30" y1="44" x2={x} y2={y} />)}
        </g>
        {nodes.map(([x, y], i) => <circle key={i} cx={x} cy={y} r="5.5" fill="url(#bhGrad)" />)}
        <circle cx="30" cy="44" r="7" fill="url(#bhGrad)" />
      </svg>
      {!compact && (
        <div style={{ lineHeight: 1.05 }}>
          <div style={{ fontWeight: 800, fontSize: 17, color: dark ? C.blueDeepDark : "#fff" }}>Behavior</div>
          <div style={{ fontWeight: 800, fontSize: 17, color: C.teal }}>Hub</div>
        </div>
      )}
    </div>
  );
}

const helpLevels = ["Independente", "Ajuda verbal", "Ajuda gestual", "Modelação", "Física parcial", "Física total"];
const resultOptions = [
  { key: "correta", label: "Correta", tone: "success" },
  { key: "incorreta", label: "Incorreta", tone: "error" },
  { key: "parcial", label: "Parcial", tone: "warn" },
  { key: "nao_respondida", label: "Não resp.", tone: "neutral" },
];

/* ================= LOGIN (RF-01) ================= */
function LoginScreen({ onEnter }) {
  const [name, setName] = useState("");
  return (
    <div style={{ minHeight: 640, display: "flex", alignItems: "center", justifyContent: "center", background: `linear-gradient(160deg, ${C.blueDeepDark}, #133a7a)`, fontFamily: "Inter, sans-serif" }}>
      <div style={{ background: "#fff", borderRadius: 18, padding: "40px 36px", width: 360, textAlign: "center", boxShadow: "0 10px 40px rgba(0,0,0,0.25)" }}>
        <div style={{ display: "flex", justifyContent: "center", marginBottom: 14 }}>
          <svg width="72" height="105" viewBox="0 0 60 88">
            <defs><linearGradient id="loginGrad" x1="0" y1="0" x2="1" y2="1"><stop offset="0%" stopColor={C.blueDeep} /><stop offset="100%" stopColor={C.green} /></linearGradient></defs>
            <g stroke="url(#loginGrad)" strokeWidth="3" fill="none">
              <path d="M30 44 L30 8 L38 8 Q54 8 54 26 Q54 44 38 44" />
              <path d="M30 44 Q54 44 54 62 Q54 80 38 80 L30 80 L30 44" />
              {[[30, 8], [10, 22], [4, 44], [10, 66], [30, 80], [30, 44]].map(([x, y], i) => <line key={i} x1="30" y1="44" x2={x} y2={y} />)}
            </g>
            {[[30, 8], [10, 22], [4, 44], [10, 66], [30, 80], [30, 44]].map(([x, y], i) => <circle key={i} cx={x} cy={y} r="5.5" fill="url(#loginGrad)" />)}
            <circle cx="30" cy="44" r="7" fill="url(#loginGrad)" />
          </svg>
        </div>
        <div style={{ fontWeight: 800, fontSize: 22, color: C.blueDeepDark }}>Behavior<span style={{ color: C.teal }}> Hub</span></div>
        <div style={{ fontSize: 10.5, letterSpacing: 1, color: C.neutral, fontWeight: 700, marginBottom: 26 }}>DADOS · COMPORTAMENTO · INTELIGÊNCIA</div>
        <Field label="Seu nome">
          <input style={inputStyle} placeholder="ex.: Ana Ribeiro" value={name} onChange={e => setName(e.target.value)}
            onKeyDown={e => e.key === "Enter" && name.trim() && onEnter(name.trim())} />
        </Field>
        <Field label="Senha"><input style={inputStyle} type="password" placeholder="••••••••" /></Field>
        <Button style={{ width: "100%", justifyContent: "center", marginTop: 6 }} icon={LogIn}
          disabled={!name.trim()} onClick={() => onEnter(name.trim())}>Entrar</Button>
        <p style={{ fontSize: 10.5, color: C.neutral, marginTop: 14 }}>Protótipo de demonstração — sem autenticação real.</p>
      </div>
    </div>
  );
}

/* ================= ÁREA DE TRABALHO (RF-02) ================= */
function AreaDeTrabalhoPage({ patients, sessions, trainings, setPage, currentUser }) {
  const [panel, setPanel] = useState("paciente"); // 'paciente' | 'profissional'
  const [filterPatientId, setFilterPatientId] = useState("");
  const [filterProfessional, setFilterProfessional] = useState("");
  const [filterStart, setFilterStart] = useState("");
  const [filterEnd, setFilterEnd] = useState("");
  const [rankOrder, setRankOrder] = useState("top"); // 'top' | 'bottom'

  const activePatients = patients.filter(p => !p.deletedAt);
  const activeSessions = sessions.filter(s => !s.deletedAt);
  const professionals = [...new Set(activeSessions.map(s => s.professional))];

  const filtered = activeSessions.filter(s => {
    if (panel === "paciente" && filterPatientId && s.patientId !== filterPatientId) return false;
    if (panel === "profissional" && filterProfessional && s.professional !== filterProfessional) return false;
    if (filterStart && new Date(s.createdAt || 0) < new Date(filterStart)) return false;
    if (filterEnd && new Date(s.createdAt || 0) > new Date(filterEnd + "T23:59:59")) return false;
    return true;
  });

  const totalSessions = filtered.length;
  const programasAplicados = new Set(filtered.map(s => s.trainingTitle)).size;
  const mediaTentativas = totalSessions ? Math.round((filtered.reduce((sum, s) => sum + (s.trials?.length || 0), 0) / totalSessions) * 10) / 10 : 0;
  const acertoMedio = totalSessions ? Math.round(filtered.reduce((sum, s) => sum + accuracyOf(s.trials), 0) / totalSessions) : 0;

  const areaMap = {};
  filtered.forEach(s => {
    const training = trainings.find(t => t.title === s.trainingTitle);
    const area = training?.area || "Outros";
    if (!areaMap[area]) areaMap[area] = { area, total: 0, count: 0 };
    areaMap[area].total += accuracyOf(s.trials);
    areaMap[area].count += 1;
  });
  const areaPerformance = Object.values(areaMap).map(a => ({ area: a.area, desempenho: Math.round(a.total / a.count) }));

  const trainingMap = {};
  filtered.forEach(s => {
    if (!trainingMap[s.trainingTitle]) trainingMap[s.trainingTitle] = { title: s.trainingTitle, total: 0, count: 0 };
    trainingMap[s.trainingTitle].total += accuracyOf(s.trials);
    trainingMap[s.trainingTitle].count += 1;
  });
  const trainingRanking = Object.values(trainingMap)
    .map(t => ({ title: t.title, desempenho: Math.round(t.total / t.count) }))
    .sort((a, b) => rankOrder === "top" ? b.desempenho - a.desempenho : a.desempenho - b.desempenho)
    .slice(0, 5);

  const resultCounts = { correta: 0, incorreta: 0, parcial: 0, nao_respondida: 0 };
  filtered.forEach(s => (s.trials || []).forEach(t => resultCounts[t.result] !== undefined && resultCounts[t.result]++));
  const distributionData = [
    { name: "Correta", value: resultCounts.correta, color: C.green },
    { name: "Incorreta", value: resultCounts.incorreta, color: C.red },
    { name: "Parcial", value: resultCounts.parcial, color: C.orange },
    { name: "Não respondida", value: resultCounts.nao_respondida, color: C.neutral },
  ].filter(d => d.value > 0);

  function weekLabel(iso) {
    const d = new Date(iso);
    const onejan = new Date(d.getFullYear(), 0, 1);
    const week = Math.ceil((((d - onejan) / 86400000) + onejan.getDay() + 1) / 7);
    return `Sem ${week}`;
  }
  const weekMap = {};
  filtered.forEach(s => {
    const wk = weekLabel(s.createdAt || new Date().toISOString());
    weekMap[wk] = (weekMap[wk] || 0) + 1;
  });
  const weeklyData = Object.entries(weekMap).map(([week, sessoes]) => ({ week, sessoes }));

  return (
    <div>
      <h1 style={{ fontSize: 22, color: C.blueDeepDark, marginBottom: 4 }}>Área de Trabalho</h1>
      <p style={{ color: C.neutral, fontSize: 13.5, marginBottom: 16 }}>Bem-vindo(a){currentUser?.name ? `, ${currentUser.name}` : ""} — painel calculado em tempo real a partir dos dados registrados.</p>

      <div style={{ display: "flex", gap: 4, marginBottom: 14 }}>
        <button onClick={() => setPanel("paciente")} style={{
          padding: "8px 16px", borderRadius: "8px 8px 0 0", border: "none", cursor: "pointer", fontSize: 12.5, fontWeight: 700,
          background: panel === "paciente" ? "#fff" : "transparent", color: panel === "paciente" ? C.blueDeep : C.neutral,
          borderBottom: panel === "paciente" ? `2.5px solid ${C.teal}` : "2.5px solid transparent",
        }}>Painel do Paciente</button>
        <button onClick={() => setPanel("profissional")} style={{
          padding: "8px 16px", borderRadius: "8px 8px 0 0", border: "none", cursor: "pointer", fontSize: 12.5, fontWeight: 700,
          background: panel === "profissional" ? "#fff" : "transparent", color: panel === "profissional" ? C.blueDeep : C.neutral,
          borderBottom: panel === "profissional" ? `2.5px solid ${C.teal}` : "2.5px solid transparent",
        }}>Painel do Profissional</button>
      </div>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 10 }}>
          {panel === "paciente" ? (
            <Field label="Paciente">
              <select style={inputStyle} value={filterPatientId} onChange={e => setFilterPatientId(e.target.value)}>
                <option value="">Todos</option>
                {activePatients.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
              </select>
            </Field>
          ) : (
            <Field label="Profissional">
              <select style={inputStyle} value={filterProfessional} onChange={e => setFilterProfessional(e.target.value)}>
                <option value="">Todos</option>
                {professionals.map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </Field>
          )}
          <Field label="Data início"><input type="date" style={inputStyle} value={filterStart} onChange={e => setFilterStart(e.target.value)} /></Field>
          <Field label="Data fim"><input type="date" style={inputStyle} value={filterEnd} onChange={e => setFilterEnd(e.target.value)} /></Field>
        </div>
      </Card>

      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14, marginBottom: 16 }}>
        <Card><div style={{ color: C.neutral, fontSize: 12, marginBottom: 6 }}>Sessões realizadas</div><div style={{ fontSize: 24, fontWeight: 800, color: C.blueDeepDark }}>{totalSessions}</div></Card>
        <Card><div style={{ color: C.neutral, fontSize: 12, marginBottom: 6 }}>Programas aplicados</div><div style={{ fontSize: 24, fontWeight: 800, color: C.blueDeepDark }}>{programasAplicados}</div></Card>
        <Card><div style={{ color: C.neutral, fontSize: 12, marginBottom: 6 }}>Média tentativas/sessão</div><div style={{ fontSize: 24, fontWeight: 800, color: C.blueDeepDark }}>{mediaTentativas}</div></Card>
        <Card><div style={{ color: C.neutral, fontSize: 12, marginBottom: 6 }}>Média de acerto</div><div style={{ fontSize: 24, fontWeight: 800, color: C.blueDeepDark }}>{acertoMedio}%</div></Card>
      </div>

      {totalSessions === 0 ? (
        <Card><EmptyState title="Nenhuma sessão no período/filtro selecionado ainda." cta="Adicionar paciente" onClick={() => setPage("pacientes")} /></Card>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <Card>
            <h3 style={{ margin: "0 0 10px 0", fontSize: 14, color: C.graphite }}>Desempenho por Área</h3>
            <ResponsiveContainer width="100%" height={190}>
              <BarChart data={areaPerformance}>
                <CartesianGrid stroke={C.border} vertical={false} />
                <XAxis dataKey="area" tick={{ fontSize: 10.5 }} />
                <YAxis tick={{ fontSize: 11 }} unit="%" />
                <Tooltip />
                <Bar dataKey="desempenho" fill={C.teal} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <Card>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
              <h3 style={{ margin: 0, fontSize: 14, color: C.graphite }}>Treinos: Maior/Menor Desempenho</h3>
              <div style={{ display: "flex", gap: 4 }}>
                <button onClick={() => setRankOrder("top")} style={{ fontSize: 10.5, padding: "4px 8px", borderRadius: 6, border: `1px solid ${C.border}`, background: rankOrder === "top" ? C.blueDeep : "#fff", color: rankOrder === "top" ? "#fff" : C.graphite, cursor: "pointer", fontWeight: 700 }}>Maior</button>
                <button onClick={() => setRankOrder("bottom")} style={{ fontSize: 10.5, padding: "4px 8px", borderRadius: 6, border: `1px solid ${C.border}`, background: rankOrder === "bottom" ? C.blueDeep : "#fff", color: rankOrder === "bottom" ? "#fff" : C.graphite, cursor: "pointer", fontWeight: 700 }}>Menor</button>
              </div>
            </div>
            {trainingRanking.map((t, i) => (
              <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "7px 2px", borderBottom: i < trainingRanking.length - 1 ? `1px solid ${C.border}` : "none" }}>
                <span style={{ fontSize: 12.5, color: C.graphite }}>{t.title}</span>
                <Badge tone={t.desempenho >= 70 ? "success" : t.desempenho >= 40 ? "warn" : "error"}>{t.desempenho}%</Badge>
              </div>
            ))}
          </Card>

          <Card>
            <h3 style={{ margin: "0 0 10px 0", fontSize: 14, color: C.graphite }}>Distribuição de Resultados</h3>
            <ResponsiveContainer width="100%" height={190}>
              <PieChart>
                <Pie data={distributionData} dataKey="value" nameKey="name" innerRadius={38} outerRadius={68}>
                  {distributionData.map((entry, i) => <Cell key={i} fill={entry.color} />)}
                </Pie>
                <Legend wrapperStyle={{ fontSize: 10.5 }} />
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </Card>

          <Card>
            <h3 style={{ margin: "0 0 10px 0", fontSize: 14, color: C.graphite }}>Sessões por Semana</h3>
            <ResponsiveContainer width="100%" height={190}>
              <BarChart data={weeklyData}>
                <CartesianGrid stroke={C.border} vertical={false} />
                <XAxis dataKey="week" tick={{ fontSize: 10.5 }} />
                <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
                <Tooltip />
                <Bar dataKey="sessoes" fill={C.blueLight} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}

      <Card style={{ marginTop: 16 }}>
        <h3 style={{ margin: "0 0 12px 0", fontSize: 15, color: C.graphite }}>Alertas clínicos</h3>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-start", marginBottom: 12 }}>
          <AlertTriangle size={16} color={C.orange} style={{ marginTop: 2, flexShrink: 0 }} />
          <div style={{ fontSize: 12.5, color: C.graphite }}>Programa "Tolerância à espera" está sem coleta há 14 dias (exemplo ilustrativo).</div>
        </div>
        <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
          <Clock size={16} color={C.blueLight} style={{ marginTop: 2, flexShrink: 0 }} />
          <div style={{ fontSize: 12.5, color: C.graphite }}>Paciente com independência ≥ 80% pode estar pronto para fading de ajuda.</div>
        </div>
      </Card>
    </div>
  );
}

/* ================= PACIENTES (RF-03) ================= */
function PacientesPage({ patients, addPatient, deletePatient, onOpenPatient }) {
  const [query, setQuery] = useState("");
  const [showModal, setShowModal] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [form, setForm] = useState({ name: "", age: "", diagnosis: "", responsavel: "", endereco: "", telefone: "", escola: "", turno: "Manhã" });

  const active = patients.filter(p => !p.deletedAt);
  const filtered = active.filter(p => p.name.toLowerCase().includes(query.toLowerCase()));
  const atLimit = active.length >= 3;

  function submit() {
    if (!form.name) return;
    addPatient({ ...form, professional: "Não atribuído", status: "Ativo" });
    setForm({ name: "", age: "", diagnosis: "", responsavel: "", endereco: "", telefone: "", escola: "", turno: "Manhã" });
    setShowModal(false);
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 20 }}>
        <div>
          <h1 style={{ fontSize: 22, color: C.blueDeepDark, marginBottom: 4 }}>Pacientes</h1>
          <p style={{ color: C.neutral, fontSize: 13.5, margin: 0 }}>{active.length} paciente(s) ativo(s) — plano Free permite até 3.</p>
        </div>
        <Button icon={Plus} onClick={() => setShowModal(true)} disabled={atLimit}>Adicionar paciente</Button>
      </div>

      <div style={{ position: "relative", marginBottom: 16, maxWidth: 320 }}>
        <Search size={15} style={{ position: "absolute", left: 12, top: 11, color: C.neutral }} />
        <input value={query} onChange={e => setQuery(e.target.value)} placeholder="Buscar por nome..." style={{ ...inputStyle, paddingLeft: 34 }} />
      </div>

      {active.length === 0 ? (
        <Card><EmptyState title="Nenhum paciente adicionado. Clique em Adicionar paciente para começar." cta="Adicionar paciente" onClick={() => setShowModal(true)} /></Card>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
          {filtered.map(p => (
            <Card key={p.id} onClick={() => onOpenPatient(p.id)}>
              <div style={{ display: "flex", justifyContent: "space-between" }}>
                <div style={{ display: "flex", gap: 10, alignItems: "center", marginBottom: 10 }}>
                  <div style={{ width: 40, height: 40, borderRadius: "50%", background: C.blueLight, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 14 }}>
                    {p.name.split(" ").map(n => n[0]).slice(0, 2).join("")}
                  </div>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 14, color: C.graphite }}>{p.name}</div>
                    <div style={{ fontSize: 12, color: C.neutral }}>{p.age} anos</div>
                  </div>
                </div>
                <Trash2 size={15} style={{ cursor: "pointer", color: C.neutral }} onClick={(e) => { e.stopPropagation(); setConfirmDelete(p); }} />
              </div>
              <div style={{ fontSize: 12.5, color: C.graphite, marginBottom: 4 }}><b>Diagnóstico:</b> {p.diagnosis}</div>
              {(p.escola || p.turno) && (
                <div style={{ fontSize: 11.5, color: C.neutral, marginBottom: 8 }}>🏫 {p.escola || "Escola não informada"} · {p.turno}</div>
              )}
              <Badge tone="success">{p.status}</Badge>
            </Card>
          ))}
        </div>
      )}

      {atLimit && (
        <div style={{ marginTop: 16, background: "#FFF7ED", border: `1px solid ${C.orange}`, borderRadius: 10, padding: "12px 16px", fontSize: 13, color: C.graphite }}>
          Você atingiu o limite de 3 pacientes do plano gratuito. <b style={{ color: C.blueDeep }}>Conheça os planos</b> para adicionar mais.
        </div>
      )}

      {showModal && (
        <Modal onClose={() => setShowModal(false)} title="Adicionar paciente" wide>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
            <Field label="Nome completo"><input style={inputStyle} value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} /></Field>
            <Field label="Idade"><input style={inputStyle} value={form.age} onChange={e => setForm({ ...form, age: e.target.value })} /></Field>
          </div>
          <Field label="Diagnóstico / informações clínicas"><input style={inputStyle} value={form.diagnosis} onChange={e => setForm({ ...form, diagnosis: e.target.value })} /></Field>
          <Field label="Nome do responsável"><input style={inputStyle} value={form.responsavel} onChange={e => setForm({ ...form, responsavel: e.target.value })} /></Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
            <Field label="Endereço"><input style={inputStyle} value={form.endereco} onChange={e => setForm({ ...form, endereco: e.target.value })} /></Field>
            <Field label="Telefone"><input style={inputStyle} value={form.telefone} onChange={e => setForm({ ...form, telefone: e.target.value })} /></Field>
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
            <Field label="Nome da escola"><input style={inputStyle} value={form.escola} onChange={e => setForm({ ...form, escola: e.target.value })} /></Field>
            <Field label="Turno escolar">
              <select style={inputStyle} value={form.turno} onChange={e => setForm({ ...form, turno: e.target.value })}>
                <option>Manhã</option><option>Tarde</option><option>Integral</option><option>Não frequenta</option>
              </select>
            </Field>
          </div>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
            <Button variant="secondary" onClick={() => setShowModal(false)}>Cancelar</Button>
            <Button onClick={submit}>Salvar paciente</Button>
          </div>
        </Modal>
      )}

      {confirmDelete && (
        <ConfirmModal
          title="Excluir paciente"
          message={`Este paciente e todos os dados relacionados serão movidos para Dados Excluídos por ${RETENTION_DAYS} dias. Deseja continuar?`}
          confirmLabel="Excluir"
          onClose={() => setConfirmDelete(null)}
          onConfirm={() => { deletePatient(confirmDelete.id); setConfirmDelete(null); }}
        />
      )}
    </div>
  );
}

/* ================= FICHA DO PACIENTE (RF-07, RF-09) ================= */
function PatientDetailPage({ patient, sessions, objectives, trainings, trainingLinks, planAttachments, auditLog, onBack, addSession, addObjective, addAttachment, initialTab, familyMessages, addFamilyMessage }) {
  const [tab, setTab] = useState(initialTab || "resumo");
  const patientSessions = sessions.filter(s => s.patientId === patient.id && !s.deletedAt);
  const patientObjectives = objectives.filter(o => o.patientId === patient.id);
  const prescribedTrainingIds = trainingLinks.filter(l => l.patientId === patient.id).map(l => l.trainingId);

  const tabs = [
    { id: "resumo", label: "Resumo" },
    { id: "historico", label: "Histórico de Sessões" },
    { id: "plano", label: "Plano de Tratamento" },
    { id: "familia", label: "Família" },
    { id: "novo-atendimento", label: "Novo Atendimento" },
  ];

  return (
    <div>
      <Button variant="ghost" onClick={onBack} style={{ marginBottom: 10 }}><ChevronLeft size={15} /> Voltar para Pacientes</Button>
      <div style={{ display: "flex", gap: 14, alignItems: "center", marginBottom: 18 }}>
        <div style={{ width: 54, height: 54, borderRadius: "50%", background: C.blueLight, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center", fontWeight: 700, fontSize: 18 }}>
          {patient.name.split(" ").map(n => n[0]).slice(0, 2).join("")}
        </div>
        <div>
          <h1 style={{ fontSize: 20, color: C.blueDeepDark, margin: 0 }}>{patient.name}</h1>
          <div style={{ fontSize: 12.5, color: C.neutral }}>{patient.age} anos · {patient.diagnosis} · Responsável: {patient.responsavel || "não informado"}</div>
        </div>
      </div>

      <div style={{ display: "flex", gap: 4, borderBottom: `1px solid ${C.border}`, marginBottom: 18, flexWrap: "wrap" }}>
        {tabs.map(t => (
          <div key={t.id} onClick={() => setTab(t.id)} style={{
            padding: "9px 14px", cursor: "pointer", fontSize: 13, fontWeight: 600,
            color: tab === t.id ? C.blueDeep : C.neutral,
            borderBottom: tab === t.id ? `2.5px solid ${C.teal}` : "2.5px solid transparent",
          }}>{t.label}</div>
        ))}
      </div>

      {tab === "resumo" && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
          <Card>
            <h3 style={{ marginTop: 0, fontSize: 14, color: C.graphite }}>Dados cadastrais</h3>
            <p style={{ fontSize: 12.5, margin: "4px 0" }}><b>Endereço:</b> {patient.endereco || "não informado"}</p>
            <p style={{ fontSize: 12.5, margin: "4px 0" }}><b>Telefone:</b> {patient.telefone || "não informado"}</p>
            <p style={{ fontSize: 12.5, margin: "4px 0" }}><b>Escola:</b> {patient.escola || "não informado"} — {patient.turno}</p>
            <p style={{ fontSize: 12.5, margin: "4px 0" }}><b>Profissional principal:</b> {patient.professional}</p>
          </Card>
          <Card>
            <h3 style={{ marginTop: 0, fontSize: 14, color: C.graphite }}>Treinos prescritos</h3>
            {prescribedTrainingIds.length === 0 ? (
              <p style={{ fontSize: 12.5, color: C.neutral }}>Nenhum treino vinculado ainda — veja a Biblioteca de Treino.</p>
            ) : trainings.filter(t => prescribedTrainingIds.includes(t.id)).map(t => (
              <div key={t.id} style={{ fontSize: 12.5, color: C.graphite, marginBottom: 4 }}>⭐ {t.title}</div>
            ))}
          </Card>
        </div>
      )}

      {tab === "historico" && (
        patientSessions.length === 0 ? (
          <Card><EmptyState title="Nenhum atendimento registrado para este paciente ainda." cta="Novo Atendimento" onClick={() => setTab("novo-atendimento")} /></Card>
        ) : (
          <Card style={{ padding: 0 }}>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
              <thead><tr style={{ background: C.blueDeep, color: "#fff", textAlign: "left" }}>
                <th style={{ padding: "10px 16px" }}>Treino</th><th style={{ padding: "10px 16px" }}>Data</th><th style={{ padding: "10px 16px" }}>Acerto</th>
              </tr></thead>
              <tbody>
                {[...patientSessions].reverse().map(s => (
                  <tr key={s.id} style={{ borderBottom: `1px solid ${C.border}` }}>
                    <td style={{ padding: "10px 16px", fontWeight: 600 }}>{s.trainingTitle}</td>
                    <td style={{ padding: "10px 16px", color: C.neutral }}>{s.date}</td>
                    <td style={{ padding: "10px 16px" }}><Badge tone={accuracyOf(s.trials) >= 70 ? "success" : "warn"}>{accuracyOf(s.trials)}%</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        )
      )}

      {tab === "plano" && (
        <TreatmentPlanTab patient={patient} objectives={patientObjectives} planAttachments={planAttachments.filter(a => a.patientId === patient.id)}
          addObjective={addObjective} addAttachment={addAttachment} />
      )}

      {tab === "familia" && (
        <FamilyChatTab patient={patient} messages={familyMessages.filter(m => m.patientId === patient.id)} addMessage={addFamilyMessage} />
      )}

      {tab === "novo-atendimento" && (
        <NovoAtendimentoForm patient={patient} trainings={trainings} prescribedTrainingIds={prescribedTrainingIds}
          onSave={(data) => { addSession(data); setTab("historico"); }} />
      )}
    </div>
  );
}

/* ================= NOVO ATENDIMENTO (RF-07, RF-08) ================= */
/* ================= COMUNICAÇÃO COM A FAMÍLIA — chat de verdade, não recado burocrático ================= */
function FamilyChatTab({ patient, messages, addMessage }) {
  const [sender, setSender] = useState("equipe");
  const [text, setText] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages.length]);

  function send() {
    if (!text.trim()) return;
    addMessage({ patientId: patient.id, sender, text: text.trim() });
    setText("");
  }

  return (
    <Card style={{ padding: 0, display: "flex", flexDirection: "column", height: 460, overflow: "hidden" }}>
      <div style={{ padding: "12px 16px", borderBottom: `1px solid ${C.border}`, display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <b style={{ fontSize: 13.5, color: C.graphite }}>Comunicação com a Família</b>
        <span style={{ fontSize: 10.5, color: C.neutral }}>Responsável: {patient.responsavel || "não informado"}</span>
      </div>
      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: 14, display: "flex", flexDirection: "column", gap: 8, background: C.grayLight }}>
        {messages.length === 0 ? (
          <div style={{ textAlign: "center", color: C.neutral, fontSize: 12.5, marginTop: 30 }}>Nenhuma mensagem ainda. Envie a primeira atualização para a família.</div>
        ) : messages.map(m => (
          <div key={m.id} style={{
            alignSelf: m.sender === "equipe" ? "flex-end" : "flex-start",
            maxWidth: "75%", padding: "8px 12px", borderRadius: 13, fontSize: 12.5, lineHeight: 1.4,
            background: m.sender === "equipe" ? C.blueDeep : "#fff",
            color: m.sender === "equipe" ? "#fff" : C.graphite,
            boxShadow: m.sender === "equipe" ? "none" : "0 1px 3px rgba(15,37,87,0.08)",
          }}>
            <div style={{ fontSize: 9.5, opacity: 0.75, marginBottom: 2, fontWeight: 700 }}>{m.sender === "equipe" ? "Equipe" : "Família"}</div>
            {m.text}
          </div>
        ))}
      </div>
      <div style={{ padding: 10, borderTop: `1px solid ${C.border}` }}>
        <div style={{ display: "flex", gap: 6, marginBottom: 6 }}>
          <button onClick={() => setSender("equipe")} style={{ fontSize: 10.5, padding: "4px 10px", borderRadius: 999, border: `1px solid ${C.border}`, background: sender === "equipe" ? C.blueDeep : "#fff", color: sender === "equipe" ? "#fff" : C.graphite, cursor: "pointer", fontWeight: 700 }}>Enviar como Equipe</button>
          <button onClick={() => setSender("familia")} style={{ fontSize: 10.5, padding: "4px 10px", borderRadius: 999, border: `1px solid ${C.border}`, background: sender === "familia" ? C.teal : "#fff", color: sender === "familia" ? "#fff" : C.graphite, cursor: "pointer", fontWeight: 700 }}>Simular Família</button>
        </div>
        <div style={{ display: "flex", gap: 6 }}>
          <input style={{ ...inputStyle, flex: 1 }} placeholder="Escrever mensagem..." value={text} onChange={e => setText(e.target.value)} onKeyDown={e => e.key === "Enter" && send()} />
          <Button onClick={send} disabled={!text.trim()} icon={Send} />
        </div>
      </div>
    </Card>
  );
}

function NovoAtendimentoForm({ patient, trainings, prescribedTrainingIds, onSave }) {
  const orderedTrainings = [...trainings].sort((a, b) => (prescribedTrainingIds.includes(b.id) ? 1 : 0) - (prescribedTrainingIds.includes(a.id) ? 1 : 0));
  const [trainingTitle, setTrainingTitle] = useState(orderedTrainings[0]?.title || "");
  const [trials, setTrials] = useState([{ id: uid("t"), help: "Independente", result: "correta" }]);
  const accuracy = useMemo(() => accuracyOf(trials), [trials]);

  function addTrial() { setTrials([...trials, { id: uid("t"), help: "Independente", result: "correta" }]); }
  function removeTrial(id) { setTrials(trials.filter(t => t.id !== id)); }
  function updateTrial(id, field, value) { setTrials(trials.map(t => t.id === id ? { ...t, [field]: value } : t)); }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "1fr 1.3fr", gap: 16 }}>
      <Card>
        <Field label="Paciente">
          <div style={{ ...inputStyle, background: C.grayLight, color: C.graphite, fontWeight: 600 }}>{patient.name}</div>
        </Field>
        <Field label="Profissional (múltipla escolha)">
          <select style={inputStyle} defaultValue="Ana Ribeiro — Psicóloga infantil">
            <option>Ana Ribeiro — Psicóloga infantil</option>
            <option>Carlos Lima — Analista do Comportamento / ABA</option>
            <option>Fernanda Dias — Fonoaudióloga</option>
          </select>
        </Field>
        <Field label="Treino do dia">
          <select style={inputStyle} value={trainingTitle} onChange={e => setTrainingTitle(e.target.value)}>
            {orderedTrainings.map(t => <option key={t.id}>{prescribedTrainingIds.includes(t.id) ? `⭐ ${t.title} (Prescrito)` : t.title}</option>)}
          </select>
        </Field>
        <Field label="Observações"><textarea style={{ ...inputStyle, minHeight: 70 }} placeholder="Texto clínico opcional..." /></Field>
      </Card>

      <Card>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14 }}>
          <h3 style={{ margin: 0, fontSize: 15, color: C.graphite }}>Treino: {trainingTitle}</h3>
          <Badge tone={accuracy >= 70 ? "success" : "warn"}>Percentual de acerto: {accuracy}%</Badge>
        </div>
        {trials.map((t, i) => (
          <div key={t.id} style={{ border: `1px solid ${C.border}`, borderRadius: 10, padding: 12, marginBottom: 10 }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <b style={{ fontSize: 13, color: C.blueDeep }}>Tentativa {i + 1}</b>
              {trials.length > 1 && <Trash2 size={14} style={{ cursor: "pointer", color: C.neutral }} onClick={() => removeTrial(t.id)} />}
            </div>
            <div style={{ marginBottom: 10 }}>
              <label style={{ fontSize: 10.5, color: C.neutral, fontWeight: 700, marginBottom: 4, display: "block" }}>Nível de ajuda</label>
              <select style={{ ...inputStyle, width: "100%" }} value={t.help} onChange={e => updateTrial(t.id, "help", e.target.value)}>
                {helpLevels.map(h => <option key={h}>{h}</option>)}
              </select>
            </div>
            <label style={{ fontSize: 10.5, color: C.neutral, fontWeight: 700, marginBottom: 4, display: "block" }}>Resultado</label>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 6 }}>
              {resultOptions.map(r => (
                <button key={r.key} onClick={() => updateTrial(t.id, "result", r.key)} style={{
                  border: `2px solid ${t.result === r.key ? C.blueDeep : C.border}`,
                  background: t.result === r.key ? C.blueDeep : "#fff",
                  color: t.result === r.key ? "#fff" : C.graphite,
                  borderRadius: 10, padding: "16px 4px", fontSize: 12, cursor: "pointer", fontWeight: 700,
                  minHeight: 54,
                }}>{r.label}</button>
              ))}
            </div>
          </div>
        ))}
        <Button variant="secondary" icon={Plus} onClick={addTrial}>Adicionar tentativa</Button>
        <div style={{ display: "flex", justifyContent: "flex-end", marginTop: 16 }}>
          <Button onClick={() => onSave({
            patientId: patient.id, patient: patient.name, professional: "Ana Ribeiro", specialty: "Psicóloga infantil",
            date: nowStamp(), createdAt: new Date().toISOString(), trainingTitle, trials,
          })}><Check size={15} /> Salvar atendimento</Button>
        </div>
      </Card>
    </div>
  );
}

/* ================= PLANO DE TRATAMENTO (dentro da ficha) — RF-04, RF-05 ================= */
function TreatmentPlanTab({ patient, objectives, planAttachments, addObjective, addAttachment }) {
  const [showNewObjective, setShowNewObjective] = useState(null); // area string

  return (
    <div>
      <div style={{ display: "grid", gridTemplateColumns: `repeat(${AREAS.length}, 1fr)`, gap: 12 }}>
        {AREAS.map(area => {
          const areaObjectives = objectives.filter(o => o.area === area);
          const attachments = planAttachments.filter(a => a.area === area);
          return (
            <Card key={area} style={{ padding: 14 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 10 }}>
                <b style={{ fontSize: 12.5, color: C.blueDeep }}>{area}</b>
              </div>
              {areaObjectives.length === 0 ? (
                <p style={{ fontSize: 11.5, color: C.neutral }}>Sem objetivos ainda.</p>
              ) : areaObjectives.map(o => (
                <div key={o.id} style={{ border: `1px solid ${C.border}`, borderRadius: 8, padding: 8, marginBottom: 8 }}>
                  <div style={{ fontSize: 12, fontWeight: 600, color: C.graphite, marginBottom: 3 }}>{o.title}</div>
                  <Badge tone={o.status}>{o.status === "success" ? "Dominado 🎉" : o.status === "warn" ? "Em andamento" : "Não iniciado"}</Badge>
                  {o.aiGenerated && <div style={{ marginTop: 4 }}><Badge tone="purple"><Sparkles size={10} /> IA</Badge></div>}
                </div>
              ))}
              {attachments.length > 0 && (
                <div style={{ marginTop: 6, marginBottom: 6 }}>
                  {attachments.map(a => <div key={a.id} style={{ fontSize: 10.5, color: C.neutral, display: "flex", alignItems: "center", gap: 4 }}><FileUp size={11} /> {a.fileName}</div>)}
                </div>
              )}
              <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 8 }}>
                <Button variant="secondary" style={{ fontSize: 11, padding: "6px 10px" }} onClick={() => setShowNewObjective(area)}>+ Novo Objetivo</Button>
                <label style={{ fontSize: 11, color: C.blueDeep, cursor: "pointer", textAlign: "center", border: `1px dashed ${C.border}`, borderRadius: 7, padding: "6px 10px" }}>
                  <FileUp size={11} style={{ verticalAlign: "-2px", marginRight: 4 }} />Importar PDF
                  <input type="file" accept=".pdf" style={{ display: "none" }} onChange={e => {
                    const f = e.target.files?.[0];
                    if (f) addAttachment({ patientId: patient.id, area, fileName: f.name });
                  }} />
                </label>
              </div>
            </Card>
          );
        })}
      </div>

      {showNewObjective && (
        <NovoObjetivoModal area={showNewObjective} patient={patient}
          onClose={() => setShowNewObjective(null)}
          onSave={(obj) => { addObjective({ patientId: patient.id, area: showNewObjective, ...obj }); setShowNewObjective(null); }} />
      )}
    </div>
  );
}

function NovoObjetivoModal({ area, onClose, onSave }) {
  const [sourceText, setSourceText] = useState("");
  const [form, setForm] = useState({ title: "", description: "", strategy: "", masteryCriteria: "" });
  const [aiGenerated, setAiGenerated] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function fillWithAI() {
    if (!sourceText.trim()) return;
    setLoading(true); setError("");
    try {
      const result = await askClaude(
        "Você ajuda a rascunhar objetivos de plano terapêutico multidisciplinar (ABA, Psicologia, Fonoaudiologia, Terapia Ocupacional) a partir de um texto de referência fornecido pelo profissional. Responda APENAS com um objeto JSON válido, sem markdown, sem crases, exatamente no formato: {\"title\": string, \"description\": string, \"strategy\": string, \"masteryCriteria\": string}. Use linguagem de sugestão clínica revisável; nunca inclua diagnóstico ou linguagem causal definitiva.",
        `Área: ${area}\nTexto/documento de referência fornecido pelo profissional:\n${sourceText}\n\nGere um rascunho de objetivo terapêutico para esta área com base neste conteúdo.`
      );
      setForm({ title: result.title || "", description: result.description || "", strategy: result.strategy || "", masteryCriteria: result.masteryCriteria || "" });
      setAiGenerated(true);
    } catch (e) {
      setError("Não foi possível gerar com IA agora. Preencha manualmente.");
    } finally { setLoading(false); }
  }

  return (
    <Modal title={`Novo Objetivo — ${area}`} onClose={onClose} wide>
      <Field label="Cole ou descreva o conteúdo do documento/avaliação (opcional)">
        <textarea style={{ ...inputStyle, minHeight: 60 }} value={sourceText} onChange={e => setSourceText(e.target.value)}
          placeholder="Ex.: trecho da avaliação, anotações da sessão, resumo do PDF importado..." />
      </Field>
      <Button variant="ai" icon={Sparkles} loading={loading} disabled={!sourceText.trim()} onClick={fillWithAI} style={{ marginBottom: 14 }}>
        Preencher com IA
      </Button>
      {error && <div style={{ fontSize: 12, color: C.red, marginBottom: 10 }}>{error}</div>}
      {aiGenerated && <AiDraftNote />}
      <Field label="Título do objetivo"><input style={inputStyle} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></Field>
      <Field label="Descrição"><textarea style={{ ...inputStyle, minHeight: 50 }} value={form.description} onChange={e => setForm({ ...form, description: e.target.value })} /></Field>
      <Field label="Estratégia"><textarea style={{ ...inputStyle, minHeight: 50 }} value={form.strategy} onChange={e => setForm({ ...form, strategy: e.target.value })} /></Field>
      <Field label="Critério de domínio"><input style={inputStyle} value={form.masteryCriteria} onChange={e => setForm({ ...form, masteryCriteria: e.target.value })} /></Field>
      <div style={{ display: "flex", justifyContent: "flex-end", gap: 8, marginTop: 8 }}>
        <Button variant="secondary" onClick={onClose}>Cancelar</Button>
        <Button disabled={!form.title} onClick={() => onSave({ ...form, status: "warn", aiGenerated })}>Salvar objetivo</Button>
      </div>
    </Modal>
  );
}

/* ================= ATENDIMENTOS (lista supervisória, RF-09) ================= */
/* ================= AGENDA — dia a dia, salas e conflito de horário ================= */
function AgendaPage({ patients, appointments, addAppointment, updateAppointmentStatus, onStartSession }) {
  const active = patients.filter(p => !p.deletedAt);
  const [selectedDate, setSelectedDate] = useState(new Date().toISOString().slice(0, 10));
  const [showNew, setShowNew] = useState(false);
  const [form, setForm] = useState({ patientId: active[0]?.id || "", professional: "Ana Ribeiro", room: "Sala 1", time: "09:00" });

  const dayAppointments = appointments.filter(a => a.date === selectedDate).sort((a, b) => a.time.localeCompare(b.time));

  function changeDay(delta) {
    const d = new Date(selectedDate + "T00:00:00");
    d.setDate(d.getDate() + delta);
    setSelectedDate(d.toISOString().slice(0, 10));
  }
  function formatDatePretty(iso) {
    const d = new Date(iso + "T00:00:00");
    const s = d.toLocaleDateString("pt-BR", { weekday: "long", day: "2-digit", month: "long" });
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  const statusMeta = {
    agendado: { label: "Agendado", tone: "info" },
    confirmado: { label: "Confirmado", tone: "success" },
    realizado: { label: "Realizado", tone: "neutral" },
    cancelado: { label: "Cancelado", tone: "error" },
    faltou: { label: "Faltou", tone: "warn" },
  };

  function hasConflict(room, time) {
    return dayAppointments.some(a => a.room === room && a.time === time);
  }

  function submitNew() {
    if (!form.patientId) return;
    const patient = active.find(p => p.id === form.patientId);
    addAppointment({ patientId: form.patientId, patient: patient?.name, professional: form.professional, room: form.room, date: selectedDate, time: form.time, status: "agendado" });
    setShowNew(false);
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, color: C.blueDeepDark, margin: 0 }}>Agenda</h1>
        <Button icon={Plus} onClick={() => setShowNew(true)}>Novo Agendamento</Button>
      </div>

      <Card style={{ marginBottom: 16, display: "flex", alignItems: "center", justifyContent: "space-between" }}>
        <Button variant="ghost" onClick={() => changeDay(-1)}><ChevronLeft size={16} /></Button>
        <div style={{ textAlign: "center" }}>
          <div style={{ fontWeight: 700, fontSize: 13.5, color: C.blueDeepDark }}>{formatDatePretty(selectedDate)}</div>
          <input type="date" value={selectedDate} onChange={e => setSelectedDate(e.target.value)} style={{ ...inputStyle, marginTop: 6, fontSize: 11, padding: "4px 8px" }} />
        </div>
        <Button variant="ghost" onClick={() => changeDay(1)}><ChevronRight size={16} /></Button>
      </Card>

      {dayAppointments.length === 0 ? (
        <Card><EmptyState title="Nenhum agendamento para este dia." cta="Novo Agendamento" onClick={() => setShowNew(true)} emoji="📅" /></Card>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
          {dayAppointments.map(a => (
            <Card key={a.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 10 }}>
              <div style={{ display: "flex", gap: 14, alignItems: "center" }}>
                <div style={{ fontWeight: 800, fontSize: 16, color: C.blueDeep, minWidth: 50 }}>{a.time}</div>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 13.5, color: C.graphite }}>{a.patient}</div>
                  <div style={{ fontSize: 11.5, color: C.neutral, display: "flex", gap: 10, alignItems: "center", flexWrap: "wrap" }}>
                    <span>{a.professional}</span>
                    <span style={{ display: "flex", alignItems: "center", gap: 3 }}><MapPin size={11} /> {a.room}</span>
                  </div>
                </div>
              </div>
              <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                <Badge tone={statusMeta[a.status].tone}>{statusMeta[a.status].label}</Badge>
                {a.status === "agendado" && (
                  <Button variant="secondary" style={{ fontSize: 11, padding: "6px 10px" }} onClick={() => updateAppointmentStatus(a.id, "confirmado")}>Confirmar</Button>
                )}
                {(a.status === "agendado" || a.status === "confirmado") && (
                  <Button style={{ fontSize: 11, padding: "6px 10px" }} onClick={() => onStartSession(a.id, a.patientId)}>Iniciar sessão</Button>
                )}
              </div>
            </Card>
          ))}
        </div>
      )}

      {showNew && (
        <Modal title="Novo Agendamento" onClose={() => setShowNew(false)}>
          <Field label="Paciente">
            <select style={inputStyle} value={form.patientId} onChange={e => setForm({ ...form, patientId: e.target.value })}>
              {active.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>
          <Field label="Profissional">
            <select style={inputStyle} value={form.professional} onChange={e => setForm({ ...form, professional: e.target.value })}>
              <option>Ana Ribeiro</option><option>Carlos Lima</option><option>Fernanda Dias</option>
            </select>
          </Field>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 0 }}>
            <Field label="Sala">
              <select style={inputStyle} value={form.room} onChange={e => setForm({ ...form, room: e.target.value })}>
                <option>Sala 1</option><option>Sala 2</option><option>Sala 3</option>
              </select>
            </Field>
            <Field label="Horário"><input type="time" style={inputStyle} value={form.time} onChange={e => setForm({ ...form, time: e.target.value })} /></Field>
          </div>
          {hasConflict(form.room, form.time) && (
            <div style={{ fontSize: 11.5, color: C.red, marginBottom: 10, display: "flex", gap: 5, alignItems: "center" }}>
              <AlertTriangle size={13} /> Já existe um agendamento nesta sala e horário.
            </div>
          )}
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button variant="secondary" onClick={() => setShowNew(false)}>Cancelar</Button>
            <Button onClick={submitNew}>Salvar agendamento</Button>
          </div>
        </Modal>
      )}
    </div>
  );
}

function AtendimentosPage({ patients, sessions, onGoToPatient }) {
  const activePatients = patients.filter(p => !p.deletedAt);
  const activeSessions = sessions.filter(s => !s.deletedAt);
  const [pick, setPick] = useState(activePatients[0]?.id || "");

  return (
    <div>
      <h1 style={{ fontSize: 22, color: C.blueDeepDark, marginBottom: 4 }}>Atendimentos</h1>
      <p style={{ color: C.neutral, fontSize: 13, marginBottom: 16 }}>Para iniciar um atendimento, abra a ficha do paciente — o registro sempre parte do contexto dele.</p>

      <Card style={{ marginBottom: 16, display: "flex", gap: 10, alignItems: "center" }}>
        <select style={{ ...inputStyle, flex: 1 }} value={pick} onChange={e => setPick(e.target.value)}>
          {activePatients.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <Button icon={ChevronRight} onClick={() => onGoToPatient(pick, "novo-atendimento")} disabled={!pick}>Ir para o paciente</Button>
      </Card>

      {activeSessions.length === 0 ? (
        <Card><EmptyState title="Nenhum atendimento registrado ainda." /></Card>
      ) : (
        <Card style={{ padding: 0 }}>
          <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 13 }}>
            <thead><tr style={{ background: C.blueDeep, color: "#fff", textAlign: "left" }}>
              <th style={{ padding: "10px 16px" }}>Paciente</th><th style={{ padding: "10px 16px" }}>Treino</th>
              <th style={{ padding: "10px 16px" }}>Data</th><th style={{ padding: "10px 16px" }}>Acerto</th>
            </tr></thead>
            <tbody>
              {[...activeSessions].reverse().map(s => (
                <tr key={s.id} style={{ borderBottom: `1px solid ${C.border}`, cursor: "pointer" }} onClick={() => onGoToPatient(s.patientId, "historico")}>
                  <td style={{ padding: "10px 16px", fontWeight: 600, color: C.graphite }}>{s.patient}</td>
                  <td style={{ padding: "10px 16px", color: C.neutral }}>{s.trainingTitle}</td>
                  <td style={{ padding: "10px 16px", color: C.neutral }}>{s.date}</td>
                  <td style={{ padding: "10px 16px" }}><Badge tone={accuracyOf(s.trials) >= 70 ? "success" : "warn"}>{accuracyOf(s.trials)}%</Badge></td>
                </tr>
              ))}
            </tbody>
          </table>
        </Card>
      )}
    </div>
  );
}

/* ================= BIBLIOTECA DE TREINO (RF-10) ================= */
function BibliotecaTreinoPage({ trainings, patients, trainingLinks, addTraining, linkTraining }) {
  const [showNew, setShowNew] = useState(false);
  const [linkingTraining, setLinkingTraining] = useState(null);
  const [form, setForm] = useState({ title: "", area: "ABA", ageRange: "" });

  function submitNew() {
    if (!form.title) return;
    addTraining(form);
    setForm({ title: "", area: "ABA", ageRange: "" });
    setShowNew(false);
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, color: C.blueDeepDark, margin: 0 }}>Biblioteca de Treino</h1>
        <Button icon={Plus} onClick={() => setShowNew(true)}>Novo Treinamento</Button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(2, 1fr)", gap: 14 }}>
        {trainings.map(t => {
          const linkedCount = trainingLinks.filter(l => l.trainingId === t.id).length;
          return (
            <Card key={t.id}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: 10 }}>
                <div>
                  <div style={{ fontWeight: 700, fontSize: 14, color: C.graphite, marginBottom: 4 }}>{t.title}</div>
                  <div style={{ fontSize: 12, color: C.neutral }}>{t.ageRange || "Idade não especificada"}</div>
                </div>
                <Badge tone="info">{t.area}</Badge>
              </div>
              {linkedCount > 0 && <div style={{ fontSize: 11, color: C.teal, fontWeight: 700, marginBottom: 8 }}>⭐ Prescrito para {linkedCount} paciente(s)</div>}
              <Button variant="secondary" icon={Link2} style={{ fontSize: 12 }} onClick={() => setLinkingTraining(t)}>Vincular</Button>
            </Card>
          );
        })}
      </div>

      {showNew && (
        <Modal title="Novo Treinamento" onClose={() => setShowNew(false)}>
          <Field label="Título"><input style={inputStyle} value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} /></Field>
          <Field label="Categoria/área">
            <select style={inputStyle} value={form.area} onChange={e => setForm({ ...form, area: e.target.value })}>
              <option>ABA</option><option>Comunicação</option><option>Social</option><option>Autonomia</option><option>Motor</option>
            </select>
          </Field>
          <Field label="Faixa etária sugerida"><input style={inputStyle} value={form.ageRange} onChange={e => setForm({ ...form, ageRange: e.target.value })} placeholder="ex.: 4-8 anos" /></Field>
          <div style={{ display: "flex", justifyContent: "flex-end", gap: 8 }}>
            <Button variant="secondary" onClick={() => setShowNew(false)}>Cancelar</Button>
            <Button onClick={submitNew}>Salvar treino</Button>
          </div>
        </Modal>
      )}

      {linkingTraining && (
        <VincularModal training={linkingTraining} patients={patients} trainingLinks={trainingLinks}
          onClose={() => setLinkingTraining(null)} onLink={linkTraining} />
      )}
    </div>
  );
}

function VincularModal({ training, patients, trainingLinks, onClose, onLink }) {
  const [query, setQuery] = useState("");
  const active = patients.filter(p => !p.deletedAt && p.name.toLowerCase().includes(query.toLowerCase()));
  const linkedIds = trainingLinks.filter(l => l.trainingId === training.id).map(l => l.patientId);

  return (
    <Modal title={`Vincular "${training.title}"`} onClose={onClose}>
      <div style={{ position: "relative", marginBottom: 12 }}>
        <Search size={14} style={{ position: "absolute", left: 10, top: 10, color: C.neutral }} />
        <input style={{ ...inputStyle, paddingLeft: 30 }} placeholder="Buscar paciente..." value={query} onChange={e => setQuery(e.target.value)} />
      </div>
      {active.map(p => {
        const linked = linkedIds.includes(p.id);
        return (
          <div key={p.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "8px 4px", borderBottom: `1px solid ${C.border}` }}>
            <span style={{ fontSize: 13, color: C.graphite }}>{p.name}</span>
            <Button variant={linked ? "secondary" : "primary"} style={{ fontSize: 11, padding: "5px 10px" }}
              onClick={() => onLink(training.id, p.id, linked)}>{linked ? "Vinculado ✓" : "Vincular"}</Button>
          </div>
        );
      })}
    </Modal>
  );
}

/* ================= AVALIAÇÕES — VB-MAPP Milestones (estrutura genérica, sem itens protegidos) ================= */
function AvaliacoesPage({ patients, assessments, addAssessment, addObjectivesBulk }) {
  const active = patients.filter(p => !p.deletedAt);
  const [patientId, setPatientId] = useState(active[0]?.id || "");
  const [protocolKey, setProtocolKey] = useState("vbmapp");
  const [levelId, setLevelId] = useState(1);
  const [scores, setScores] = useState({}); // { domainName: [item1..itemN] }
  const [lowAreasEdit, setLowAreasEdit] = useState("");
  const [draft, setDraft] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const protocol = ASSESSMENT_PROTOCOLS[protocolKey];
  const level = protocol.levels.find(l => l.id === levelId) || protocol.levels[0];

  function getScore(domainName, itemIdx) { return scores[domainName]?.[itemIdx] ?? 0; }
  function setScore(domainName, itemIdx, value) {
    setScores(prev => {
      const domain = level.domains.find(d => d.name === domainName);
      const arr = prev[domainName] ? [...prev[domainName]] : Array(domain.items).fill(0);
      arr[itemIdx] = value;
      return { ...prev, [domainName]: arr };
    });
  }
  function subtotalOf(arr) { return (arr || []).reduce((s, v) => s + (typeof v === "number" ? v : 0), 0); }
  function domainSubtotal(domainName) { return subtotalOf(scores[domainName]); }
  function domainMax(domain) { return domain.items * protocol.maxPerItem; }
  function pct(sub, max) { return max ? Math.round((sub / max) * 1000) / 10 : 0; }
  function domainPercent(domain) { return pct(domainSubtotal(domain.name), domainMax(domain)); }

  const levelTotalPoints = level.domains.reduce((sum, d) => sum + domainSubtotal(d.name), 0);
  const levelMaxPoints = level.domains.reduce((sum, d) => sum + domainMax(d), 0);
  const levelPercent = pct(levelTotalPoints, levelMaxPoints);

  const patientAssessments = assessments.filter(a => a.patientId === patientId && a.protocol === protocolKey).sort((a, b) => new Date(a.appliedAt) - new Date(b.appliedAt));
  const sameLevelAssessments = patientAssessments.filter(a => a.level === levelId).slice(-4);

  function saveAssessment() {
    if (!patientId) return;
    addAssessment({ patientId, protocol: protocolKey, level: levelId, appliedAt: new Date().toISOString(), scores });
    setScores({});
  }

  const evolutionData = patientAssessments.map(a => {
    const lvl = protocol.levels.find(l => l.id === a.level) || protocol.levels[0];
    const totalPts = lvl.domains.reduce((sum, d) => sum + subtotalOf(a.scores[d.name]), 0);
    const maxPts = lvl.domains.reduce((sum, d) => sum + domainMax(d), 0);
    return { data: new Date(a.appliedAt).toLocaleDateString("pt-BR"), percentual: pct(totalPts, maxPts) };
  });

  const comparisonDates = sameLevelAssessments.map(a => new Date(a.appliedAt).toLocaleDateString("pt-BR"));
  const comparisonData = level.domains.map(d => {
    const row = { domain: d.name.length > 16 ? d.name.slice(0, 15) + "…" : d.name };
    sameLevelAssessments.forEach((a, i) => { row[comparisonDates[i]] = pct(subtotalOf(a.scores[d.name]), domainMax(d)); });
    return row;
  });

  const radarData = level.domains.map(d => ({ domain: d.name.length > 14 ? d.name.slice(0, 13) + "…" : d.name, percentual: domainPercent(d) }));

  function computeLowAreas() {
    const last = patientAssessments[patientAssessments.length - 1];
    if (!last) return "";
    const lvl = protocol.levels.find(l => l.id === last.level) || protocol.levels[0];
    return lvl.domains
      .map(d => ({ name: d.name, p: pct(subtotalOf(last.scores[d.name]), domainMax(d)) }))
      .sort((a, b) => a.p - b.p)
      .slice(0, 3)
      .map(s => `${s.name} (${s.p}%)`)
      .join(", ");
  }

  async function generatePlan() {
    const text = lowAreasEdit.trim() || computeLowAreas();
    if (!text || !patientId) return;
    setLoading(true); setError(""); setDraft(null);
    try {
      const result = await askClaude(
        "Você ajuda a gerar um rascunho simples de plano de tratamento multidisciplinar a partir do resultado de uma avaliação padronizada. Responda APENAS com um objeto JSON válido, sem markdown, sem crases, exatamente no formato: {\"objectives\": [{\"area\": string, \"title\": string, \"description\": string, \"strategy\": string, \"masteryCriteria\": string}]}. Gere no máximo 4 objetivos, um por domínio de menor percentual informado, escolhendo o campo area entre: Psicologia, ABA, Fonoaudiologia, Terapia Ocupacional. Use linguagem de sugestão revisável, nunca diagnóstico.",
        `Protocolo: ${protocol.label} — ${level.label}\nDomínios com menor percentual:\n${text}\n\nGere um rascunho de plano de tratamento com objetivos sugeridos para esses domínios.`
      );
      setDraft(result.objectives || []);
    } catch (e) {
      setError("Não foi possível gerar com IA agora. Tente novamente em instantes.");
    } finally { setLoading(false); }
  }

  return (
    <div>
      <h1 style={{ fontSize: 22, color: C.blueDeepDark, marginBottom: 4 }}>Avaliações Padronizadas</h1>
      <p style={{ color: C.neutral, fontSize: 13, marginBottom: 16 }}>Consulte seu material licenciado (PDF/planilha própria) para o texto de cada item; aqui você só lança a pontuação e o consolidado por domínio sai automático.</p>

      <Card style={{ marginBottom: 16 }}>
        <div style={{ display: "grid", gridTemplateColumns: protocol.levels.length > 1 ? "1fr 1fr 1fr" : "1fr 1fr", gap: 12 }}>
          <Field label="Paciente">
            <select style={inputStyle} value={patientId} onChange={e => { setPatientId(e.target.value); setScores({}); }}>
              {active.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
            </select>
          </Field>
          <Field label="Protocolo">
            <select style={inputStyle} value={protocolKey} onChange={e => {
              const nk = e.target.value;
              setProtocolKey(nk); setLevelId(ASSESSMENT_PROTOCOLS[nk].levels[0].id); setScores({});
            }}>
              {Object.entries(ASSESSMENT_PROTOCOLS).map(([key, p]) => <option key={key} value={key}>{p.label}</option>)}
            </select>
          </Field>
          {protocol.levels.length > 1 && (
            <Field label="Nível">
              <select style={inputStyle} value={levelId} onChange={e => { setLevelId(Number(e.target.value)); setScores({}); }}>
                {protocol.levels.map(l => <option key={l.id} value={l.id}>{l.label}</option>)}
              </select>
            </Field>
          )}
        </div>
      </Card>

      <Card style={{ marginBottom: 16, padding: 0, overflow: "hidden" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 18px", borderBottom: `1px solid ${C.border}` }}>
          <h3 style={{ margin: 0, fontSize: 14, color: C.graphite }}>Pontuação por domínio — {protocol.label} · {level.label}</h3>
          <Badge tone={levelPercent >= 70 ? "success" : levelPercent >= 40 ? "warn" : "error"}>{levelTotalPoints}/{levelMaxPoints} pts · {levelPercent}%</Badge>
        </div>
        {level.domains.map(domain => (
          <div key={domain.name} style={{ padding: "10px 18px", borderBottom: `1px solid ${C.border}` }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
              <b style={{ fontSize: 12.5, color: C.graphite }}>{domain.name}</b>
              <Badge tone={domainPercent(domain) >= 70 ? "success" : domainPercent(domain) >= 40 ? "warn" : "error"}>
                {domainSubtotal(domain.name)}/{domainMax(domain)} · {domainPercent(domain)}%
              </Badge>
            </div>
            <div style={{ display: "flex", flexWrap: "wrap", gap: 6 }}>
              {Array.from({ length: domain.items }).map((_, i) => (
                <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 2 }}>
                  <span style={{ fontSize: 8.5, color: C.neutral }}>{i + 1}</span>
                  <select value={getScore(domain.name, i)} onChange={e => setScore(domain.name, i, e.target.value === "NA" ? "NA" : Number(e.target.value))}
                    style={{ width: 46, fontSize: 10.5, padding: "2px 1px", borderRadius: 5, border: `1px solid ${C.border}`, textAlign: "center" }}>
                    {protocol.scoreOptions.map(o => <option key={o} value={o}>{o}</option>)}
                  </select>
                </div>
              ))}
            </div>
          </div>
        ))}
        <div style={{ padding: 14, display: "flex", justifyContent: "flex-end" }}>
          <Button onClick={saveAssessment} disabled={!patientId}><Check size={15} /> Salvar aplicação</Button>
        </div>
      </Card>

      {patientAssessments.length > 0 && (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16, marginBottom: 16 }}>
          <Card>
            <h3 style={{ margin: "0 0 10px 0", fontSize: 14, color: C.graphite }}>Evolução do percentual total</h3>
            <ResponsiveContainer width="100%" height={190}>
              <LineChart data={evolutionData}>
                <CartesianGrid stroke={C.border} vertical={false} />
                <XAxis dataKey="data" tick={{ fontSize: 10.5 }} />
                <YAxis tick={{ fontSize: 11 }} unit="%" domain={[0, 100]} />
                <Tooltip />
                <Line type="monotone" dataKey="percentual" stroke={C.teal} strokeWidth={2.5} dot={{ r: 3 }} />
              </LineChart>
            </ResponsiveContainer>
          </Card>
          <Card>
            <h3 style={{ margin: "0 0 10px 0", fontSize: 14, color: C.graphite }}>% por domínio — última aplicação</h3>
            <ResponsiveContainer width="100%" height={190}>
              <RadarChart data={radarData}>
                <PolarGrid stroke={C.border} />
                <PolarAngleAxis dataKey="domain" tick={{ fontSize: 8.5 }} />
                <Radar dataKey="percentual" stroke={C.blueDeep} fill={C.blueLight} fillOpacity={0.4} />
                <Tooltip />
              </RadarChart>
            </ResponsiveContainer>
          </Card>
        </div>
      )}

      {sameLevelAssessments.length > 0 && (
        <Card style={{ marginBottom: 16 }}>
          <h3 style={{ margin: "0 0 10px 0", fontSize: 14, color: C.graphite }}>Consolidado — % por domínio (até 4 aplicações · {level.label})</h3>
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={comparisonData}>
              <CartesianGrid stroke={C.border} vertical={false} />
              <XAxis dataKey="domain" tick={{ fontSize: 8.5 }} interval={0} angle={-30} textAnchor="end" height={60} />
              <YAxis tick={{ fontSize: 11 }} unit="%" domain={[0, 100]} />
              <Tooltip />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              {comparisonDates.map((d, i) => (
                <Bar key={d} dataKey={d} fill={[C.blueLight, C.teal, C.green, C.purple][i % 4]} />
              ))}
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}

      <Card>
        <h3 style={{ marginTop: 0, fontSize: 14, color: C.graphite }}>Gerar plano de tratamento a partir da avaliação</h3>
        <Field label="Domínios de menor percentual (preenchido automaticamente a partir da última aplicação — edite se quiser)">
          <textarea style={{ ...inputStyle, minHeight: 50 }} value={lowAreasEdit || computeLowAreas()} onChange={e => setLowAreasEdit(e.target.value)} />
        </Field>
        <Button variant="ai" icon={Sparkles} loading={loading} disabled={!patientId} onClick={generatePlan}>Gerar plano com IA</Button>
        {error && <div style={{ fontSize: 12, color: C.red, marginTop: 8 }}>{error}</div>}
      </Card>

      {draft && (
        <Card style={{ marginTop: 16 }}>
          <AiDraftNote />
          {draft.map((o, i) => (
            <div key={i} style={{ border: `1px solid ${C.border}`, borderRadius: 8, padding: 10, marginBottom: 8 }}>
              <Badge tone="info">{o.area}</Badge>
              <div style={{ fontWeight: 700, fontSize: 13, marginTop: 6, color: C.graphite }}>{o.title}</div>
              <div style={{ fontSize: 12, color: C.neutral, marginTop: 3 }}>{o.description}</div>
            </div>
          ))}
          <Button onClick={() => { addObjectivesBulk(patientId, draft); setDraft(null); }}>Aprovar e adicionar ao Plano de Tratamento</Button>
        </Card>
      )}
    </div>
  );
}

/* ================= REPORTS ================= */
function ReportsPage({ sessions }) {
  const activeSessions = sessions.filter(s => !s.deletedAt);
  const lineData = activeSessions.map((s, i) => ({ data: s.date.split(" ")[0] || `S${i + 1}`, acerto: accuracyOf(s.trials) }));
  const helpCounts = {};
  activeSessions.forEach(s => {
    const key = s.trainingTitle;
    if (!helpCounts[key]) helpCounts[key] = { treino: key, Independente: 0, "Ajuda verbal": 0, "Ajuda gestual": 0 };
    (s.trials || []).forEach(t => {
      if (t.help === "Independente") helpCounts[key].Independente++;
      else if (t.help === "Ajuda verbal") helpCounts[key]["Ajuda verbal"]++;
      else if (t.help === "Ajuda gestual") helpCounts[key]["Ajuda gestual"]++;
    });
  });
  const barData = Object.values(helpCounts);
  const counts = { correta: 0, incorreta: 0, parcial: 0, nao_respondida: 0 };
  activeSessions.forEach(s => (s.trials || []).forEach(t => counts[t.result] !== undefined && counts[t.result]++));
  const pieData = [
    { name: "Correta", value: counts.correta, color: C.green }, { name: "Incorreta", value: counts.incorreta, color: C.red },
    { name: "Parcial", value: counts.parcial, color: C.orange }, { name: "Não respondida", value: counts.nao_respondida, color: C.neutral },
  ].filter(d => d.value > 0);
  const overallAccuracy = activeSessions.length ? Math.round(activeSessions.reduce((sum, s) => sum + accuracyOf(s.trials), 0) / activeSessions.length) : 0;

  return (
    <div>
      <h1 style={{ fontSize: 22, color: C.blueDeepDark, marginBottom: 4 }}>Reports</h1>
      <p style={{ color: C.neutral, fontSize: 13, marginBottom: 20 }}>Calculado em tempo real a partir das {activeSessions.length} sessão(ões) registrada(s).</p>
      {activeSessions.length === 0 ? (
        <Card><EmptyState title="Registre um atendimento para gerar relatórios." /></Card>
      ) : (
        <>
          <Card style={{ marginBottom: 16, borderLeft: `4px solid ${C.purple}` }}>
            <Badge tone="info">Resumo automático — revise antes de exportar</Badge>
            <p style={{ marginTop: 10, marginBottom: 0, fontSize: 13.5, color: C.graphite }}>Percentual médio de acerto: <b>{overallAccuracy}%</b>.</p>
          </Card>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Card>
              <h3 style={{ margin: "0 0 10px 0", fontSize: 14, color: C.graphite }}>Curva de Aprendizagem</h3>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={lineData}>
                  <CartesianGrid stroke={C.border} vertical={false} /><XAxis dataKey="data" tick={{ fontSize: 11 }} /><YAxis tick={{ fontSize: 11 }} /><Tooltip />
                  <Line type="monotone" dataKey="acerto" stroke={C.teal} strokeWidth={2.5} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </Card>
            <Card>
              <h3 style={{ margin: "0 0 10px 0", fontSize: 14, color: C.graphite }}>Níveis de ajuda por treino</h3>
              <ResponsiveContainer width="100%" height={200}>
                <BarChart data={barData}>
                  <CartesianGrid stroke={C.border} vertical={false} /><XAxis dataKey="treino" tick={{ fontSize: 10 }} /><YAxis tick={{ fontSize: 11 }} allowDecimals={false} /><Tooltip /><Legend wrapperStyle={{ fontSize: 11 }} />
                  <Bar dataKey="Independente" stackId="a" fill={C.green} /><Bar dataKey="Ajuda verbal" stackId="a" fill={C.blueLight} /><Bar dataKey="Ajuda gestual" stackId="a" fill={C.orange} />
                </BarChart>
              </ResponsiveContainer>
            </Card>
            <Card>
              <h3 style={{ margin: "0 0 10px 0", fontSize: 14, color: C.graphite }}>Distribuição de respostas</h3>
              <ResponsiveContainer width="100%" height={200}>
                <PieChart><Pie data={pieData} dataKey="value" nameKey="name" innerRadius={40} outerRadius={70}>{pieData.map((entry, i) => <Cell key={i} fill={entry.color} />)}</Pie><Legend wrapperStyle={{ fontSize: 11 }} /><Tooltip /></PieChart>
              </ResponsiveContainer>
            </Card>
            <Card>
              <h3 style={{ margin: "0 0 10px 0", fontSize: 14, color: C.graphite }}>Radar por área (ilustrativo)</h3>
              <ResponsiveContainer width="100%" height={200}>
                <RadarChart data={[{ area: "Comunicação", valor: 80 }, { area: "Social", valor: 55 }, { area: "Autonomia", valor: 90 }, { area: "Motor", valor: 40 }, { area: "Cognitivo", valor: 68 }]}>
                  <PolarGrid stroke={C.border} /><PolarAngleAxis dataKey="area" tick={{ fontSize: 11 }} /><Radar dataKey="valor" stroke={C.blueDeep} fill={C.blueLight} fillOpacity={0.4} />
                </RadarChart>
              </ResponsiveContainer>
            </Card>
          </div>
        </>
      )}
    </div>
  );
}

/* ================= ABA (RF-11) ================= */
function ABAPage({ patients, trainings, trainingLinks, atAssignments, addAtAssignment, currentUser, setCurrentUser }) {
  const isAT = currentUser.role === "AT";
  const active = patients.filter(p => !p.deletedAt);
  const [newAssign, setNewAssign] = useState({ atName: "", patientId: active[0]?.id || "", trainingId: trainings[0]?.id || "" });

  const myAssignments = atAssignments.filter(a => a.atName === currentUser.name);

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, color: C.blueDeepDark, margin: 0 }}>ABA — Espaço do Supervisor e dos ATs</h1>
        <Field label="">
          <select style={inputStyle} value={currentUser.role} onChange={e => setCurrentUser({ ...currentUser, role: e.target.value })}>
            <option value="Administrador">Ver como: Supervisor</option>
            <option value="AT">Ver como: AT (Auxiliar Terapêutico)</option>
          </select>
        </Field>
      </div>

      {!isAT ? (
        <>
          <Card style={{ marginBottom: 16 }}>
            <h3 style={{ marginTop: 0, fontSize: 14, color: C.graphite }}>Atribuir AT a um paciente e treino</h3>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr auto", gap: 10, alignItems: "end" }}>
              <Field label="Nome do AT"><input style={inputStyle} value={newAssign.atName} onChange={e => setNewAssign({ ...newAssign, atName: e.target.value })} placeholder="ex.: Rafael Souza" /></Field>
              <Field label="Paciente">
                <select style={inputStyle} value={newAssign.patientId} onChange={e => setNewAssign({ ...newAssign, patientId: e.target.value })}>
                  {active.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
                </select>
              </Field>
              <Field label="Treino">
                <select style={inputStyle} value={newAssign.trainingId} onChange={e => setNewAssign({ ...newAssign, trainingId: e.target.value })}>
                  {trainings.map(t => <option key={t.id} value={t.id}>{t.title}</option>)}
                </select>
              </Field>
              <Button disabled={!newAssign.atName} onClick={() => addAtAssignment(newAssign)} style={{ marginBottom: 12 }}>Atribuir</Button>
            </div>
          </Card>

          <Card style={{ padding: 0 }}>
            {atAssignments.length === 0 ? <EmptyState title="Nenhuma atribuição de AT ainda." /> : atAssignments.map((a, i) => {
              const p = patients.find(pt => pt.id === a.patientId);
              const t = trainings.find(tr => tr.id === a.trainingId);
              return (
                <div key={a.id} style={{ display: "flex", justifyContent: "space-between", padding: "12px 16px", borderBottom: i < atAssignments.length - 1 ? `1px solid ${C.border}` : "none" }}>
                  <div style={{ fontSize: 13 }}><b>{a.atName}</b> aplica <b>{t?.title}</b> em <b>{p?.name}</b></div>
                  <Badge tone="info">Ativo</Badge>
                </div>
              );
            })}
          </Card>
        </>
      ) : (
        <Card style={{ padding: 0 }}>
          {myAssignments.length === 0 ? (
            <EmptyState title={`Nenhum paciente/treino atribuído a ${currentUser.name || "este AT"} ainda.`} />
          ) : myAssignments.map((a, i) => {
            const p = patients.find(pt => pt.id === a.patientId);
            const t = trainings.find(tr => tr.id === a.trainingId);
            return (
              <div key={a.id} style={{ padding: "14px 16px", borderBottom: i < myAssignments.length - 1 ? `1px solid ${C.border}` : "none" }}>
                <div style={{ fontWeight: 700, fontSize: 13.5, color: C.graphite }}>{p?.name}</div>
                <div style={{ fontSize: 12, color: C.neutral, marginBottom: 6 }}>Treino: {t?.title}</div>
                <Badge tone="success">Pronto para aplicar</Badge>
              </div>
            );
          })}
          <p style={{ fontSize: 11, color: C.neutral, padding: "0 16px 14px 16px" }}>Como AT, você só vê os pacientes e treinos atribuídos a você — sem acesso a diagnóstico completo, plano de tratamento ou relatórios.</p>
        </Card>
      )}
    </div>
  );
}

/* ================= AUDITORIA (RF-14) ================= */
function AuditoriaPage({ patients, auditLog }) {
  const [selectedPatientId, setSelectedPatientId] = useState(null);
  const filtered = selectedPatientId ? auditLog.filter(a => a.patientId === selectedPatientId) : auditLog;
  const patientsWithLogs = patients.filter(p => auditLog.some(a => a.patientId === p.id));

  return (
    <div>
      <h1 style={{ fontSize: 22, color: C.blueDeepDark, marginBottom: 16 }}>Auditoria</h1>
      <div style={{ display: "flex", gap: 8, marginBottom: 16, flexWrap: "wrap" }}>
        <Button variant={!selectedPatientId ? "primary" : "secondary"} onClick={() => setSelectedPatientId(null)} style={{ fontSize: 12 }}>Todos</Button>
        {patientsWithLogs.map(p => (
          <Button key={p.id} variant={selectedPatientId === p.id ? "primary" : "secondary"} onClick={() => setSelectedPatientId(p.id)} style={{ fontSize: 12 }}>{p.name}</Button>
        ))}
      </div>
      {filtered.length === 0 ? (
        <Card><EmptyState title="Nenhuma ação registrada ainda." /></Card>
      ) : (
        <Card style={{ padding: 0 }}>
          {[...filtered].reverse().map((a, i) => (
            <div key={a.id} style={{ padding: "10px 16px", borderBottom: i < filtered.length - 1 ? `1px solid ${C.border}` : "none", fontSize: 12.5 }}>
              <span style={{ color: C.neutral }}>{new Date(a.timestamp).toLocaleString("pt-BR")} · </span>
              <b style={{ color: C.blueDeep }}>{a.actor}</b> {a.action} {a.patientName && <>— paciente <b>{a.patientName}</b></>}
              {a.detail && <span style={{ color: C.neutral }}> ({a.detail})</span>}
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}

/* ================= SEGURANÇA (RF-15) ================= */
function SegurancaPage({ currentUser, updateUserName }) {
  const [name, setName] = useState(currentUser.name);
  const [pwd, setPwd] = useState({ atual: "", nova: "", confirmar: "" });
  const [msg, setMsg] = useState("");

  return (
    <div>
      <h1 style={{ fontSize: 22, color: C.blueDeepDark, marginBottom: 16 }}>Segurança</h1>
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 16 }}>
        <Card>
          <h3 style={{ marginTop: 0, fontSize: 14, color: C.graphite }}>Nome de usuário</h3>
          <Field label="Nome de exibição"><input style={inputStyle} value={name} onChange={e => setName(e.target.value)} /></Field>
          <Button onClick={() => { updateUserName(name); setMsg("Nome de usuário atualizado."); }}>Salvar</Button>
        </Card>
        <Card>
          <h3 style={{ marginTop: 0, fontSize: 14, color: C.graphite }}>Trocar senha</h3>
          <Field label="Senha atual"><input type="password" style={inputStyle} value={pwd.atual} onChange={e => setPwd({ ...pwd, atual: e.target.value })} /></Field>
          <Field label="Nova senha"><input type="password" style={inputStyle} value={pwd.nova} onChange={e => setPwd({ ...pwd, nova: e.target.value })} /></Field>
          <Field label="Confirmar nova senha"><input type="password" style={inputStyle} value={pwd.confirmar} onChange={e => setPwd({ ...pwd, confirmar: e.target.value })} /></Field>
          <Button onClick={() => setMsg("Senha atualizada nesta demonstração (sem backend real de autenticação).")} disabled={!pwd.nova || pwd.nova !== pwd.confirmar}>Salvar nova senha</Button>
        </Card>
      </div>
      {msg && <div style={{ marginTop: 14, fontSize: 12.5, color: C.green, fontWeight: 600 }}>✓ {msg}</div>}
      <p style={{ fontSize: 11, color: C.neutral, marginTop: 10 }}>Protótipo de demonstração — não há autenticação real por trás destes campos.</p>
    </div>
  );
}

/* ================= DELETED DATA ================= */
function DeletedDataPage({ patients, restorePatient, purgeExpired }) {
  const deletedPatients = patients.filter(p => p.deletedAt);
  useEffect(() => { purgeExpired(); }, []); // eslint-disable-line
  return (
    <div>
      <h1 style={{ fontSize: 22, color: C.blueDeepDark, marginBottom: 4 }}>Deleted Data</h1>
      <p style={{ color: C.neutral, fontSize: 13.5, marginBottom: 20 }}>Registros excluídos ficam retidos por {RETENTION_DAYS} dias antes da exclusão permanente.</p>
      {deletedPatients.length === 0 ? (
        <Card><EmptyState title="Nenhum registro excluído no momento." emoji="✅" /></Card>
      ) : (
        <Card style={{ padding: 0 }}>
          {deletedPatients.map((p, i) => (
            <div key={p.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px", borderBottom: i < deletedPatients.length - 1 ? `1px solid ${C.border}` : "none" }}>
              <div>
                <div style={{ fontWeight: 600, fontSize: 13.5, color: C.graphite }}>{p.name} <Badge tone="neutral">Paciente</Badge></div>
                <div style={{ fontSize: 12, color: C.neutral }}>Excluído em {new Date(p.deletedAt).toLocaleString("pt-BR")} · {daysLeft(p.deletedAt)} dias restantes</div>
              </div>
              <Button variant="secondary" icon={RotateCcw} onClick={() => restorePatient(p.id)}>Restaurar</Button>
            </div>
          ))}
        </Card>
      )}
    </div>
  );
}

/* ================= PROFISSIONAIS ================= */
function ProfissionaisPage() {
  const pros = [
    { name: "Ana Ribeiro", specialty: "Psicóloga infantil", status: "Ativo", role: "Profissional" },
    { name: "Carlos Lima", specialty: "Analista do Comportamento / ABA", status: "Ativo", role: "Profissional" },
    { name: "Fernanda Dias", specialty: "Fonoaudióloga", status: "Convite pendente", role: "Profissional" },
    { name: "Rafael Souza", specialty: "Auxiliar Terapêutico", status: "Ativo", role: "AT" },
  ];
  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 20 }}>
        <h1 style={{ fontSize: 22, color: C.blueDeepDark, margin: 0 }}>Profissionais</h1>
        <Button icon={Plus}>Gerar convite</Button>
      </div>
      <Card style={{ padding: 0 }}>
        {pros.map((p, i) => (
          <div key={i} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "14px 20px", borderBottom: i < pros.length - 1 ? `1px solid ${C.border}` : "none" }}>
            <div>
              <div style={{ fontWeight: 600, fontSize: 13.5, color: C.graphite }}>{p.name} {p.role === "AT" && <Badge tone="purple">AT</Badge>}</div>
              <div style={{ fontSize: 12, color: C.neutral }}>{p.specialty}</div>
            </div>
            <Badge tone={p.status === "Ativo" ? "success" : "warn"}>{p.status}</Badge>
          </div>
        ))}
      </Card>
    </div>
  );
}

/* ================= RECURSOS (RF-12) ================= */
function RecursosPage({ resources, addResource }) {
  const [showAI, setShowAI] = useState(false);
  const [form, setForm] = useState({ type: "História social", theme: "", age: "4-8 anos" });
  const [draft, setDraft] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function generate() {
    if (!form.theme.trim()) return;
    setLoading(true); setError(""); setDraft(null);
    try {
      const result = await askClaude(
        "Você ajuda profissionais de terapia infantil (ABA, fonoaudiologia, TO, psicologia) a rascunhar recursos terapêuticos como histórias sociais, rotinas visuais e cartões de comunicação. Responda APENAS com um objeto JSON válido, sem markdown, sem crases, exatamente no formato: {\"title\": string, \"content\": string}. O conteúdo deve ser apropriado para crianças, breve e claramente educativo — nunca clínico-diagnóstico.",
        `Tipo de recurso: ${form.type}\nTema: ${form.theme}\nFaixa etária: ${form.age}\n\nGere um rascunho deste recurso terapêutico.`
      );
      setDraft(result);
    } catch (e) {
      setError("Não foi possível gerar com IA agora.");
    } finally { setLoading(false); }
  }

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 16 }}>
        <h1 style={{ fontSize: 22, color: C.blueDeepDark, margin: 0 }}>Recursos Terapêuticos</h1>
        <Button variant="ai" icon={Sparkles} onClick={() => setShowAI(true)}>Criar recurso com IA</Button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
        {resources.map((r) => (
          <Card key={r.id}>
            <div style={{ height: 90, background: C.grayLight, borderRadius: 8, marginBottom: 10, display: "flex", alignItems: "center", justifyContent: "center", color: C.neutral, fontSize: 12 }}>{r.type}</div>
            <div style={{ fontWeight: 600, fontSize: 13, color: C.graphite, marginBottom: 4 }}>{r.title}</div>
            <div style={{ fontSize: 11.5, color: C.neutral }}>{r.age}</div>
            {r.aiGenerated && <div style={{ marginTop: 6 }}><Badge tone="purple"><Sparkles size={10} /> IA</Badge></div>}
          </Card>
        ))}
      </div>

      {showAI && (
        <Modal title="Criar recurso com IA" onClose={() => setShowAI(false)} wide>
          {!draft ? (
            <>
              <Field label="Tipo de recurso">
                <select style={inputStyle} value={form.type} onChange={e => setForm({ ...form, type: e.target.value })}>
                  <option>História social</option><option>Rotina visual</option><option>Cartão de comunicação</option>
                </select>
              </Field>
              <Field label="Tema"><input style={inputStyle} value={form.theme} onChange={e => setForm({ ...form, theme: e.target.value })} placeholder="ex.: esperar a vez no parquinho" /></Field>
              <Field label="Faixa etária"><input style={inputStyle} value={form.age} onChange={e => setForm({ ...form, age: e.target.value })} /></Field>
              <Button variant="ai" icon={Sparkles} loading={loading} disabled={!form.theme.trim()} onClick={generate}>Gerar rascunho</Button>
              {error && <div style={{ fontSize: 12, color: C.red, marginTop: 8 }}>{error}</div>}
            </>
          ) : (
            <>
              <AiDraftNote />
              <h3 style={{ fontSize: 15, color: C.blueDeepDark }}>{draft.title}</h3>
              <p style={{ fontSize: 13, color: C.graphite, whiteSpace: "pre-wrap" }}>{draft.content}</p>
              <div style={{ display: "flex", gap: 8, justifyContent: "flex-end" }}>
                <Button variant="secondary" onClick={() => setDraft(null)}>Descartar</Button>
                <Button onClick={() => { addResource({ title: draft.title, type: form.type, age: form.age, aiGenerated: true }); setShowAI(false); setDraft(null); setForm({ type: "História social", theme: "", age: "4-8 anos" }); }}>Publicar na biblioteca</Button>
              </div>
            </>
          )}
        </Modal>
      )}
    </div>
  );
}

/* ================= PLANOS (RF-16) ================= */
function PlanosPage() {
  const plans = [
    { name: "Free", price: "R$ 0", features: ["Até 3 pacientes", "Sessões ilimitadas", "Sem foto"] },
    { name: "Basic", price: "R$ 79/mês", features: ["Limite configurável", "Gráficos parciais", "Recursos terapêuticos"] },
    { name: "Premium", price: "R$ 149/mês", features: ["Gráficos avançados", "Foto em sessão", "Clinical Intelligence parcial"], highlight: true },
    { name: "Enterprise", price: "Sob consulta", features: ["Múltiplos profissionais", "Convites e RBAC", "Clinical Intelligence completa"] },
  ];
  return (
    <div>
      <h1 style={{ fontSize: 22, color: C.blueDeepDark, marginBottom: 16 }}>Planos</h1>
      <Card style={{ marginBottom: 16 }}>
        <h3 style={{ marginTop: 0, fontSize: 14, color: C.graphite }}>Assinatura atual</h3>
        <p style={{ fontSize: 12.5, color: C.neutral, margin: "4px 0 12px 0" }}>Plano Free · cobrança via InfinitePay quando fizer upgrade.</p>
        <Button variant="secondary">Gerenciar assinatura</Button>
      </Card>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 14 }}>
        {plans.map(p => (
          <Card key={p.name} style={{ border: p.highlight ? `2px solid ${C.teal}` : `1px solid ${C.border}` }}>
            <div style={{ fontWeight: 700, fontSize: 15, color: C.blueDeepDark, marginBottom: 4 }}>{p.name}</div>
            <div style={{ fontSize: 20, fontWeight: 800, color: C.graphite, marginBottom: 12 }}>{p.price}</div>
            {p.features.map((f, i) => (
              <div key={i} style={{ fontSize: 12, color: C.neutral, marginBottom: 6, display: "flex", gap: 6, alignItems: "center" }}>
                <Check size={12} color={C.green} /> {f}
              </div>
            ))}
          </Card>
        ))}
      </div>
    </div>
  );
}

/* ================= IA BEHAVIOR HUB — botão flutuante global ================= */
function AIChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState([
    { role: "assistant", content: "Olá! Sou a IA do Behavior Hub. Posso ajudar com dúvidas sobre o sistema, sugerir estratégias e treinos, ou tirar dúvidas gerais sobre análise do comportamento. Como posso ajudar?" },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, open, loading]);

  async function send() {
    if (!input.trim() || loading) return;
    const userMsg = { role: "user", content: input.trim() };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    setError("");
    try {
      const reply = await askClaudeChat(nextMessages);
      setMessages([...nextMessages, { role: "assistant", content: reply }]);
    } catch (e) {
      setError("Não foi possível falar com a IA agora. Tente novamente em instantes.");
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button onClick={() => setOpen(true)} style={{
        position: "fixed", bottom: 22, right: 22, zIndex: 70,
        background: `linear-gradient(135deg, ${C.blueDeep}, ${C.teal})`, color: "#fff",
        border: "none", borderRadius: 999, padding: "13px 20px", display: "flex", alignItems: "center", gap: 8,
        fontSize: 13, fontWeight: 700, cursor: "pointer", boxShadow: "0 8px 24px rgba(15,37,87,0.35)",
      }}>
        <Sparkles size={16} /> Fale com a IA do Behavior Hub
      </button>
    );
  }

  return (
    <div style={{
      position: "fixed", bottom: 22, right: 22, width: 350, height: 480, zIndex: 70,
      background: "#fff", borderRadius: 16, boxShadow: "0 16px 48px rgba(15,37,87,0.35)",
      display: "flex", flexDirection: "column", overflow: "hidden", border: `1px solid ${C.border}`,
    }}>
      <div style={{ background: C.blueDeepDark, padding: "13px 16px", display: "flex", justifyContent: "space-between", alignItems: "center", flexShrink: 0 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, color: "#fff", fontWeight: 700, fontSize: 13.5 }}>
          <Sparkles size={16} color={C.teal} /> IA Behavior Hub
        </div>
        <X size={17} style={{ cursor: "pointer", color: "#fff" }} onClick={() => setOpen(false)} />
      </div>

      <div ref={scrollRef} style={{ flex: 1, overflowY: "auto", padding: 14, display: "flex", flexDirection: "column", gap: 10, background: C.grayLight }}>
        {messages.map((m, i) => (
          <div key={i} style={{
            alignSelf: m.role === "user" ? "flex-end" : "flex-start",
            maxWidth: "85%", padding: "9px 13px", borderRadius: 13, fontSize: 12.5, lineHeight: 1.45,
            background: m.role === "user" ? C.blueDeep : "#fff",
            color: m.role === "user" ? "#fff" : C.graphite,
            boxShadow: m.role === "user" ? "none" : "0 1px 3px rgba(15,37,87,0.08)",
            whiteSpace: "pre-wrap",
          }}>{m.content}</div>
        ))}
        {loading && (
          <div style={{ alignSelf: "flex-start", padding: "9px 13px", borderRadius: 13, background: "#fff", display: "flex", alignItems: "center", gap: 6, boxShadow: "0 1px 3px rgba(15,37,87,0.08)" }}>
            <Loader2 size={13} className="spin" /> <span style={{ fontSize: 12, color: C.neutral }}>digitando...</span>
          </div>
        )}
        {error && <div style={{ fontSize: 11.5, color: C.red }}>{error}</div>}
      </div>

      <div style={{ display: "flex", gap: 6, padding: 10, borderTop: `1px solid ${C.border}`, flexShrink: 0, background: "#fff" }}>
        <input style={{ ...inputStyle, flex: 1 }} placeholder="Pergunte alguma coisa..." value={input}
          onChange={e => setInput(e.target.value)} onKeyDown={e => e.key === "Enter" && send()} disabled={loading} />
        <Button onClick={send} disabled={loading || !input.trim()} style={{ padding: "9px 12px" }} icon={Send} />
      </div>
      <div style={{ fontSize: 9.5, color: C.neutral, textAlign: "center", padding: "0 10px 8px 10px", background: "#fff" }}>
        As respostas são sugestões — sempre use seu julgamento clínico.
      </div>
    </div>
  );
}

/* ---------- App shell ---------- */
export default function BehaviorHubPrototype() {
  const [page, setPage] = useState("area-trabalho");
  const [state, setState] = useState(null);
  const [saving, setSaving] = useState(false);
  const [openPatientId, setOpenPatientId] = useState(null);
  const [openPatientTab, setOpenPatientTab] = useState("resumo");

  useEffect(() => { loadState().then(setState); }, []);
  useEffect(() => { document.title = "Behavior Hub"; }, []);

  const persist = useCallback(async (next) => {
    setState(next);
    setSaving(true);
    await saveState(next);
    setSaving(false);
  }, []);

  const withAudit = (base, entry) => ({
    ...base,
    auditLog: [...base.auditLog, { id: uid("a"), timestamp: new Date().toISOString(), actor: base.currentUser.name || "Usuário", ...entry }],
  });

  const addPatient = useCallback((data) => {
    const p = { id: uid("p"), deletedAt: null, ...data };
    let next = { ...state, patients: [...state.patients, p] };
    next = withAudit(next, { patientId: p.id, patientName: p.name, action: "cadastrou o paciente" });
    persist(next);
  }, [state, persist]);

  const deletePatient = useCallback((id) => {
    const patient = state.patients.find(p => p.id === id);
    const patients = state.patients.map(p => p.id === id ? { ...p, deletedAt: new Date().toISOString() } : p);
    let next = { ...state, patients };
    next = withAudit(next, { patientId: id, patientName: patient?.name, action: "excluiu o paciente" });
    persist(next);
  }, [state, persist]);

  const restorePatient = useCallback((id) => {
    const patient = state.patients.find(p => p.id === id);
    const patients = state.patients.map(p => p.id === id ? { ...p, deletedAt: null } : p);
    let next = { ...state, patients };
    next = withAudit(next, { patientId: id, patientName: patient?.name, action: "restaurou o paciente" });
    persist(next);
  }, [state, persist]);

  const purgeExpired = useCallback(() => {
    if (!state) return;
    const patients = state.patients.filter(p => !p.deletedAt || daysLeft(p.deletedAt) > 0);
    if (patients.length !== state.patients.length) persist({ ...state, patients });
  }, [state, persist]);

  const addSession = useCallback((data) => {
    const s = { id: uid("s"), deletedAt: null, ...data };
    let next = { ...state, sessions: [...state.sessions, s] };
    next = withAudit(next, { patientId: data.patientId, patientName: data.patient, action: "registrou um atendimento", detail: data.trainingTitle });
    persist(next);
  }, [state, persist]);

  const addObjective = useCallback((data) => {
    const o = { id: uid("o"), ...data };
    const patient = state.patients.find(p => p.id === data.patientId);
    let next = { ...state, objectives: [...state.objectives, o] };
    next = withAudit(next, { patientId: data.patientId, patientName: patient?.name, action: "adicionou um objetivo ao plano", detail: data.title });
    persist(next);
  }, [state, persist]);

  const addObjectivesBulk = useCallback((patientId, objs) => {
    const patient = state.patients.find(p => p.id === patientId);
    const newObjs = objs.map(o => ({ id: uid("o"), patientId, status: "warn", aiGenerated: true, ...o }));
    let next = { ...state, objectives: [...state.objectives, ...newObjs] };
    next = withAudit(next, { patientId, patientName: patient?.name, action: "aprovou plano gerado por IA a partir de avaliação", detail: `${newObjs.length} objetivo(s)` });
    persist(next);
  }, [state, persist]);

  const addAssessment = useCallback((data) => {
    const patient = state.patients.find(p => p.id === data.patientId);
    const a = { id: uid("as"), ...data };
    let next = { ...state, assessments: [...state.assessments, a] };
    next = withAudit(next, { patientId: data.patientId, patientName: patient?.name, action: "registrou aplicação de avaliação", detail: `${ASSESSMENT_PROTOCOLS[data.protocol]?.label || data.protocol} — Nível ${data.level}` });
    persist(next);
  }, [state, persist]);

  const addAppointment = useCallback((data) => {
    const a = { id: uid("ap"), ...data };
    let next = { ...state, appointments: [...state.appointments, a] };
    next = withAudit(next, { patientId: data.patientId, patientName: data.patient, action: "criou um agendamento", detail: `${data.date} ${data.time} — ${data.room}` });
    persist(next);
  }, [state, persist]);

  const updateAppointmentStatus = useCallback((id, status) => {
    const appt = state.appointments.find(a => a.id === id);
    const appointments = state.appointments.map(a => a.id === id ? { ...a, status } : a);
    let next = { ...state, appointments };
    next = withAudit(next, { patientId: appt?.patientId, patientName: appt?.patient, action: `marcou agendamento como "${status}"` });
    persist(next);
  }, [state, persist]);

  const addFamilyMessage = useCallback((data) => {
    const patient = state.patients.find(p => p.id === data.patientId);
    const m = { id: uid("fm"), ...data };
    let next = { ...state, familyMessages: [...state.familyMessages, m] };
    next = withAudit(next, { patientId: data.patientId, patientName: patient?.name, action: data.sender === "equipe" ? "enviou mensagem para a família" : "recebeu mensagem da família" });
    persist(next);
  }, [state, persist]);

  const addAttachment = useCallback((data) => {
    const a = { id: uid("att"), uploadedAt: new Date().toISOString(), ...data };
    const patient = state.patients.find(p => p.id === data.patientId);
    let next = { ...state, planAttachments: [...state.planAttachments, a] };
    next = withAudit(next, { patientId: data.patientId, patientName: patient?.name, action: "importou um PDF no plano", detail: `${data.area} — ${data.fileName}` });
    persist(next);
  }, [state, persist]);

  const addTraining = useCallback((data) => {
    const t = { id: uid("tr"), custom: true, ...data };
    persist({ ...state, trainings: [...state.trainings, t] });
  }, [state, persist]);

  const linkTraining = useCallback((trainingId, patientId, alreadyLinked) => {
    const links = alreadyLinked
      ? state.trainingLinks.filter(l => !(l.trainingId === trainingId && l.patientId === patientId))
      : [...state.trainingLinks, { id: uid("link"), trainingId, patientId }];
    persist({ ...state, trainingLinks: links });
  }, [state, persist]);

  const addResource = useCallback((data) => {
    persist({ ...state, resources: [...state.resources, { id: uid("r"), ...data }] });
  }, [state, persist]);

  const addAtAssignment = useCallback((data) => {
    persist({ ...state, atAssignments: [...state.atAssignments, { id: uid("at"), ...data }] });
  }, [state, persist]);

  const setCurrentUser = useCallback((u) => { persist({ ...state, currentUser: u }); }, [state, persist]);
  const updateUserName = useCallback((name) => { persist({ ...state, currentUser: { ...state.currentUser, name } }); }, [state, persist]);

  function goToPatient(id, tab = "resumo") {
    setOpenPatientId(id); setOpenPatientTab(tab); setPage("pacientes");
  }

  if (!state) {
    return (
      <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 400, gap: 8, color: C.neutral, fontFamily: "Inter, sans-serif" }}>
        <Loader2 size={18} className="spin" /> Carregando dados salvos...
        <style>{`.spin{animation:spin 1s linear infinite}@keyframes spin{to{transform:rotate(360deg)}}`}</style>
      </div>
    );
  }

  if (!state.currentUser.name) {
    return <LoginScreen onEnter={(name) => setCurrentUser({ name, role: "Administrador" })} />;
  }

  const openPatient = openPatientId ? state.patients.find(p => p.id === openPatientId) : null;

  const pageBody = (() => {
    if (page === "pacientes" && openPatient) {
      return <PatientDetailPage patient={openPatient} sessions={state.sessions} objectives={state.objectives}
        trainings={state.trainings} trainingLinks={state.trainingLinks} planAttachments={state.planAttachments}
        auditLog={state.auditLog} onBack={() => setOpenPatientId(null)} addSession={addSession}
        addObjective={addObjective} addAttachment={addAttachment} initialTab={openPatientTab}
        familyMessages={state.familyMessages} addFamilyMessage={addFamilyMessage} />;
    }
    switch (page) {
      case "area-trabalho": return <AreaDeTrabalhoPage patients={state.patients} sessions={state.sessions} trainings={state.trainings} setPage={setPage} currentUser={state.currentUser} />;
      case "pacientes": return <PacientesPage patients={state.patients} addPatient={addPatient} deletePatient={deletePatient} onOpenPatient={(id) => goToPatient(id, "resumo")} />;
      case "atendimentos": return <AtendimentosPage patients={state.patients} sessions={state.sessions} onGoToPatient={goToPatient} />;
      case "agenda": return <AgendaPage patients={state.patients} appointments={state.appointments} addAppointment={addAppointment}
        updateAppointmentStatus={updateAppointmentStatus}
        onStartSession={(appointmentId, patientId) => { updateAppointmentStatus(appointmentId, "realizado"); goToPatient(patientId, "novo-atendimento"); }} />;
      case "biblioteca": return <BibliotecaTreinoPage trainings={state.trainings} patients={state.patients} trainingLinks={state.trainingLinks} addTraining={addTraining} linkTraining={linkTraining} />;
      case "planos-tratamento": return (
        <div>
          <h1 style={{ fontSize: 22, color: C.blueDeepDark, marginBottom: 4 }}>Treatment Plans</h1>
          <p style={{ color: C.neutral, fontSize: 13, marginBottom: 16 }}>Abra a ficha de um paciente para ver e editar o plano de tratamento dele.</p>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 14 }}>
            {state.patients.filter(p => !p.deletedAt).map(p => (
              <Card key={p.id} onClick={() => goToPatient(p.id, "plano")}>
                <div style={{ fontWeight: 700, fontSize: 14, color: C.graphite, marginBottom: 4 }}>{p.name}</div>
                <div style={{ fontSize: 12, color: C.neutral }}>{state.objectives.filter(o => o.patientId === p.id).length} objetivo(s) no plano</div>
              </Card>
            ))}
          </div>
        </div>
      );
      case "avaliacoes": return <AvaliacoesPage patients={state.patients} assessments={state.assessments} addAssessment={addAssessment} addObjectivesBulk={addObjectivesBulk} />;
      case "reports": return <ReportsPage sessions={state.sessions} />;
      case "aba": return <ABAPage patients={state.patients} trainings={state.trainings} trainingLinks={state.trainingLinks} atAssignments={state.atAssignments} addAtAssignment={addAtAssignment} currentUser={state.currentUser} setCurrentUser={setCurrentUser} />;
      case "deleted": return <DeletedDataPage patients={state.patients} restorePatient={restorePatient} purgeExpired={purgeExpired} />;
      case "profissionais": return <ProfissionaisPage />;
      case "recursos": return <RecursosPage resources={state.resources} addResource={addResource} />;
      case "auditoria": return <AuditoriaPage patients={state.patients} auditLog={state.auditLog} />;
      case "planos": return <PlanosPage />;
      case "seguranca": return <SegurancaPage currentUser={state.currentUser} updateUserName={updateUserName} />;
      default: return null;
    }
  })();

  return (
    <div style={{ display: "flex", height: "100%", minHeight: 640, fontFamily: "Inter, -apple-system, sans-serif", background: "#F8FAFC" }}>
      <div style={{ width: 226, background: C.blueDeepDark, padding: "20px 14px", flexShrink: 0, overflowY: "auto" }}>
        <div style={{ padding: "0 6px 20px 6px" }}><Logo /></div>
        {NAV_ITEMS.map(item => {
          const Icon = item.icon;
          const active = page === item.id;
          const badgeCount = item.id === "deleted" ? state.patients.filter(p => p.deletedAt).length : 0;
          return (
            <div key={item.id} onClick={() => { setPage(item.id); setOpenPatientId(null); }} style={{
              display: "flex", alignItems: "center", justifyContent: "space-between", gap: 10, padding: "9px 12px", borderRadius: 8,
              marginBottom: 2, cursor: "pointer", fontSize: 12.5,
              background: active ? "rgba(255,255,255,0.12)" : "transparent",
              color: active ? "#fff" : "rgba(255,255,255,0.7)",
              fontWeight: active ? 700 : 500,
              borderLeft: active ? `3px solid ${C.teal}` : "3px solid transparent",
            }}>
              <span style={{ display: "flex", alignItems: "center", gap: 9 }}><Icon size={15} /> {item.label}</span>
              {badgeCount > 0 && <Badge tone="warn">{badgeCount}</Badge>}
            </div>
          );
        })}
        <div style={{ marginTop: 16, padding: "8px 12px", fontSize: 10.5, color: "rgba(255,255,255,0.5)", display: "flex", alignItems: "center", gap: 6 }}>
          {saving ? <><Loader2 size={12} /> Salvando...</> : <><Check size={12} /> Dados salvos</>}
        </div>
        <div style={{ padding: "4px 12px", fontSize: 10.5, color: "rgba(255,255,255,0.5)" }}>{state.currentUser.name}</div>
      </div>
      <div style={{ flex: 1, padding: "24px 28px", overflowY: "auto" }}>
        {pageBody}
      </div>
      <AIChatWidget />
    </div>
  );
}
