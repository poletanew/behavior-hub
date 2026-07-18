import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import NotificationBell from "./NotificationBell";

const navItems = [
  { to: "/dashboard", label: "Dashboard" },
  { to: "/patients", label: "Pacientes" },
  { to: "/sessions", label: "Atendimentos" },
  { to: "/training-library", label: "Training Library" },
  { to: "/resources", label: "Recursos" },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const isAdmin = user?.user_type === "clinic_admin" || user?.user_type === "individual";

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
