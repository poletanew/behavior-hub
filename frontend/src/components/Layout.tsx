import { useEffect, useState } from "react";
import { NavLink, Outlet, useLocation } from "react-router-dom";
import {
  LayoutDashboard,
  Users,
  ClipboardList,
  BookOpen,
  ListChecks,
  ClipboardCheck,
  BarChart3,
  UserCog,
  ArchiveX,
  UserPlus,
  FolderOpen,
  History,
  CreditCard,
  KeyRound,
  CalendarDays,
  UploadCloud,
  Settings,
  Palette,
  ListTodo,
  Gauge,
  ShieldCheck,
} from "lucide-react";
import { apiRequest } from "../api/client";
import { useAuth } from "../context/AuthContext";
import NotificationBell from "./NotificationBell";
import { Logo } from "./BrandMark";
import AIChatWidget from "./AIChatWidget";

// Ordem e rótulos da navegação principal replicam o protótipo de referência
// (NAV_ITEMS) ponto a ponto. Itens que só existem no sistema real (não estavam
// no protótipo, que cobria só o Addendum v2.1) ficam agrupados ao final da
// mesma sidebar, em vez de serem descartados.
const navItems = [
  { to: "/dashboard", label: "Área de Trabalho", icon: LayoutDashboard },
  { to: "/patients", label: "Pacientes", icon: Users },
  { to: "/sessions", label: "Atendimentos", icon: ClipboardList },
  { to: "/training-library", label: "Biblioteca de Treino", icon: BookOpen },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const isAdmin = user?.user_type === "clinic_admin" || user?.user_type === "individual";
  const canSeeClinicSettings = user?.user_type === "clinic_admin" || user?.user_type === "supervisor";
  const canSeeABA = user?.user_type === "clinic_admin" || user?.user_type === "supervisor";
  const canSeeAuditLog = user?.user_type === "clinic_admin" || user?.user_type === "individual";
  const canSeeManagerDashboard = user?.user_type === "clinic_admin";
  const [requires2fa, setRequires2fa] = useState(false);
  const [bulkImportEnabled, setBulkImportEnabled] = useState(false);
  const [deletedCount, setDeletedCount] = useState(0);
  const location = useLocation();

  useEffect(() => {
    apiRequest<{ is_2fa_enabled: boolean; required: boolean }>("/auth/2fa/status")
      .then((s) => setRequires2fa(s.required))
      .catch(() => setRequires2fa(false));
    apiRequest<{ enabled: boolean }>("/patients/import/enabled")
      .then((s) => setBulkImportEnabled(s.enabled))
      .catch(() => setBulkImportEnabled(false));
  }, [user?.id]);

  useEffect(() => {
    if (!isAdmin) return;
    apiRequest<unknown[]>("/deleted-data")
      .then((items) => setDeletedCount(items.length))
      .catch(() => setDeletedCount(0));
  }, [isAdmin, user?.id]);

  const linkClass = ({ isActive }: { isActive: boolean }) =>
    `flex items-center justify-between gap-2 rounded-lg px-3 py-2 text-[13px] font-medium transition-colors border-l-[3px] ${
      isActive
        ? "bg-white/10 text-white font-bold border-brand-turquoise"
        : "text-white/70 hover:bg-white/5 border-transparent"
    }`;

  return (
    <div className="flex min-h-screen">
      <aside className="w-[226px] shrink-0 bg-brand-navy text-white flex flex-col py-5 px-3.5 overflow-y-auto">
        <div className="px-1.5 pb-5">
          <Logo />
        </div>
        <nav className="flex-1 space-y-0.5">
          {navItems.map((item) => (
            <NavLink key={item.to} to={item.to} className={linkClass}>
              <span className="flex items-center gap-2">
                <item.icon size={15} /> {item.label}
              </span>
            </NavLink>
          ))}

          <NavLink to="/treatment-plans" className={linkClass}>
            <span className="flex items-center gap-2">
              <ListChecks size={15} /> Treatment Plans
            </span>
          </NavLink>

          <NavLink to="/assessments" className={linkClass}>
            <span className="flex items-center gap-2">
              <ClipboardCheck size={15} /> Avaliações
            </span>
          </NavLink>

          <NavLink to="/reports" className={linkClass}>
            <span className="flex items-center gap-2">
              <BarChart3 size={15} /> Reports
            </span>
          </NavLink>

          {canSeeABA && (
            <NavLink to="/aba" className={linkClass}>
              <span className="flex items-center gap-2">
                <UserCog size={15} /> ABA
              </span>
            </NavLink>
          )}

          {isAdmin && (
            <NavLink to="/deleted-data" className={linkClass}>
              <span className="flex items-center gap-2">
                <ArchiveX size={15} /> Dados Excluídos
              </span>
              {deletedCount > 0 && (
                <span className="rounded-full bg-warning text-white text-[11px] font-bold px-2 py-0.5">
                  {deletedCount}
                </span>
              )}
            </NavLink>
          )}

          {user?.user_type === "clinic_admin" && (
            <NavLink to="/invitations" className={linkClass}>
              <span className="flex items-center gap-2">
                <UserPlus size={15} /> Profissionais
              </span>
            </NavLink>
          )}

          <NavLink to="/resources" className={linkClass}>
            <span className="flex items-center gap-2">
              <FolderOpen size={15} /> Recursos
            </span>
          </NavLink>

          {canSeeAuditLog && (
            <NavLink to="/audit-log" className={linkClass}>
              <span className="flex items-center gap-2">
                <History size={15} /> Auditoria
              </span>
            </NavLink>
          )}

          {isAdmin && (
            <NavLink to="/plans" className={linkClass}>
              <span className="flex items-center gap-2">
                <CreditCard size={15} /> Planos
              </span>
            </NavLink>
          )}

          <NavLink to="/security" className={linkClass}>
            <span className="flex items-center gap-2">
              <KeyRound size={15} /> Segurança
            </span>
          </NavLink>

          {/* Recursos adicionais das Fases 3-7 que não existiam no protótipo
              (que cobria só o Addendum v2.1) — mantidos, agrupados ao final. */}
          <div className="mt-3 mb-1 px-3 text-[10px] uppercase tracking-wide text-white/35 font-bold">Mais</div>

          <NavLink to="/agenda" className={linkClass}>
            <span className="flex items-center gap-2">
              <CalendarDays size={15} /> Agenda
            </span>
          </NavLink>

          <NavLink to="/waitlist" className={linkClass}>
            <span className="flex items-center gap-2">
              <ListTodo size={15} /> Lista de Espera
            </span>
          </NavLink>

          {bulkImportEnabled && (
            <NavLink to="/patients/import" className={linkClass}>
              <span className="flex items-center gap-2">
                <UploadCloud size={15} /> Importar Pacientes
              </span>
            </NavLink>
          )}

          {canSeeClinicSettings && (
            <NavLink to="/supervisor-dashboard" className={linkClass}>
              <span className="flex items-center gap-2">
                <Gauge size={15} /> Painel de Supervisão
              </span>
            </NavLink>
          )}

          {canSeeManagerDashboard && (
            <NavLink to="/manager-dashboard" className={linkClass}>
              <span className="flex items-center gap-2">
                <Gauge size={15} /> Painel de Gestão
              </span>
            </NavLink>
          )}

          {canSeeClinicSettings && (
            <NavLink to="/clinic-settings" className={linkClass}>
              <span className="flex items-center gap-2">
                <Settings size={15} /> Configurações
              </span>
            </NavLink>
          )}

          {user?.user_type === "clinic_admin" && (
            <NavLink to="/white-label" className={linkClass}>
              <span className="flex items-center gap-2">
                <Palette size={15} /> White-label
              </span>
            </NavLink>
          )}
        </nav>
        <div className="px-2 py-3 mt-2 border-t border-white/10 text-sm">
          <div className="font-medium">{user?.name}</div>
          <div className="text-white/50 text-xs mb-3">{user?.email}</div>
          <button onClick={logout} className="w-full rounded-btn bg-white/10 hover:bg-white/20 px-3 py-2 text-left">
            Sair
          </button>
        </div>
      </aside>
      <main className="flex-1 bg-brand-grayLight">
        {requires2fa && (
          <div className="bg-danger text-white text-sm px-8 py-2 flex items-center justify-between">
            <span className="flex items-center gap-2">
              <ShieldCheck size={15} />
              Seu plano Enterprise exige autenticação de dois fatores para administradores da clínica.
            </span>
            <NavLink to="/security" className="underline font-medium shrink-0 ml-4">
              Ativar agora
            </NavLink>
          </div>
        )}
        <div className="flex justify-end px-8 pt-4">
          <NotificationBell />
        </div>
        <div key={location.pathname} className="px-8 pb-8 animate-fade-in">
          <Outlet />
        </div>
      </main>
      <AIChatWidget />
    </div>
  );
}
