import { useEffect, useState } from "react";
import { NavLink, Outlet } from "react-router-dom";
import { apiRequest } from "../api/client";
import { useAuth } from "../context/AuthContext";
import NotificationBell from "./NotificationBell";

const navItems = [
  { to: "/dashboard", label: "Área de Trabalho" },
  { to: "/patients", label: "Pacientes" },
  { to: "/agenda", label: "Agenda" },
  { to: "/sessions", label: "Atendimentos" },
  { to: "/training-library", label: "Training Library" },
  { to: "/resources", label: "Recursos" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const isAdmin = user?.user_type === "clinic_admin" || user?.user_type === "individual";
  const canSeeClinicSettings = user?.user_type === "clinic_admin" || user?.user_type === "supervisor";
  const canSeeAuditLog = user?.user_type === "clinic_admin" || user?.user_type === "individual";
  const canSeeManagerDashboard = user?.user_type === "clinic_admin";
  const [requires2fa, setRequires2fa] = useState(false);

  useEffect(() => {
    apiRequest<{ is_2fa_enabled: boolean; required: boolean }>("/auth/2fa/status")
      .then((s) => setRequires2fa(s.required))
      .catch(() => setRequires2fa(false));
  }, [user?.id]);

  return (
    <div className="flex min-h-screen">
      <aside className="w-60 shrink-0 bg-brand-navy text-white flex flex-col">
        <div className="px-6 py-6">
          <div className="text-lg font-bold">Behavior Hub</div>
          <div className="text-[10px] uppercase tracking-wide text-brand-turquoise mt-1">
            Dados. Comportamento. Inteligência.
          </div>
        </div>
        <nav className="flex-1 px-3 space-y-1">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `block rounded-btn px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-turquoise text-white" : "text-slate-200 hover:bg-white/10"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
          {user?.user_type === "clinic_admin" && (
            <NavLink
              to="/invitations"
              className={({ isActive }) =>
                `block rounded-btn px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-turquoise text-white" : "text-slate-200 hover:bg-white/10"
                }`
              }
            >
              Profissionais
            </NavLink>
          )}
          {isAdmin && (
            <NavLink
              to="/deleted-data"
              className={({ isActive }) =>
                `block rounded-btn px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-turquoise text-white" : "text-slate-200 hover:bg-white/10"
                }`
              }
            >
              Dados Excluídos
            </NavLink>
          )}
          <NavLink
            to="/waitlist"
            className={({ isActive }) =>
              `block rounded-btn px-3 py-2 text-sm font-medium transition-colors ${
                isActive ? "bg-brand-turquoise text-white" : "text-slate-200 hover:bg-white/10"
              }`
            }
          >
            Lista de Espera
          </NavLink>
          <NavLink
            to="/patients/import"
            className={({ isActive }) =>
              `block rounded-btn px-3 py-2 text-sm font-medium transition-colors ${
                isActive ? "bg-brand-turquoise text-white" : "text-slate-200 hover:bg-white/10"
              }`
            }
          >
            Importar Pacientes
          </NavLink>
          {canSeeClinicSettings && (
            <NavLink
              to="/supervisor-dashboard"
              className={({ isActive }) =>
                `block rounded-btn px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-turquoise text-white" : "text-slate-200 hover:bg-white/10"
                }`
              }
            >
              Painel de Supervisão
            </NavLink>
          )}
          {canSeeManagerDashboard && (
            <NavLink
              to="/manager-dashboard"
              className={({ isActive }) =>
                `block rounded-btn px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-turquoise text-white" : "text-slate-200 hover:bg-white/10"
                }`
              }
            >
              Painel de Gestão
            </NavLink>
          )}
          {canSeeAuditLog && (
            <NavLink
              to="/audit-log"
              className={({ isActive }) =>
                `block rounded-btn px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-turquoise text-white" : "text-slate-200 hover:bg-white/10"
                }`
              }
            >
              Auditoria
            </NavLink>
          )}
          {canSeeClinicSettings && (
            <NavLink
              to="/clinic-settings"
              className={({ isActive }) =>
                `block rounded-btn px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-turquoise text-white" : "text-slate-200 hover:bg-white/10"
                }`
              }
            >
              Configurações
            </NavLink>
          )}
          <NavLink
            to="/security"
            className={({ isActive }) =>
              `block rounded-btn px-3 py-2 text-sm font-medium transition-colors ${
                isActive ? "bg-brand-turquoise text-white" : "text-slate-200 hover:bg-white/10"
              }`
            }
          >
            Segurança
          </NavLink>
          {user?.user_type === "clinic_admin" && (
            <NavLink
              to="/white-label"
              className={({ isActive }) =>
                `block rounded-btn px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-turquoise text-white" : "text-slate-200 hover:bg-white/10"
                }`
              }
            >
              White-label
            </NavLink>
          )}
          {isAdmin && (
            <NavLink
              to="/billing-sessions"
              className={({ isActive }) =>
                `block rounded-btn px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-turquoise text-white" : "text-slate-200 hover:bg-white/10"
                }`
              }
            >
              Faturamento
            </NavLink>
          )}
          {isAdmin && (
            <NavLink
              to="/plans"
              className={({ isActive }) =>
                `block rounded-btn px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-turquoise text-white" : "text-slate-200 hover:bg-white/10"
                }`
              }
            >
              Planos
            </NavLink>
          )}
        </nav>
        <div className="px-4 py-4 border-t border-white/10 text-sm">
          <div className="font-medium">{user?.name}</div>
          <div className="text-slate-300 text-xs mb-3">{user?.email}</div>
          <button
            onClick={logout}
            className="w-full rounded-btn bg-white/10 hover:bg-white/20 px-3 py-2 text-left"
          >
            Sair
          </button>
        </div>
      </aside>
      <main className="flex-1">
        {requires2fa && (
          <div className="bg-danger text-white text-sm px-8 py-2 flex items-center justify-between">
            <span>
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
        <div className="px-8 pb-8">
          <Outlet />
        </div>
      </main>
    </div>
  );
}
