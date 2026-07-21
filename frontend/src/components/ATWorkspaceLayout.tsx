import { Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Addendum v2.1, RF-11 — espaço de trabalho restrito do AT (Auxiliar
// Terapêutico): só pacientes atribuídos e treinos vinculados a eles, sem
// nenhum outro item de menu do sistema (mesmo padrão do Family Portal).
export default function ATWorkspaceLayout() {
  const { user, logout } = useAuth();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-brand-navy text-white px-8 py-4 flex items-center justify-between">
        <div>
          <div className="text-lg font-bold">Behavior Hub</div>
          <div className="text-[10px] uppercase tracking-wide text-brand-turquoise">Espaço ABA</div>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span>{user?.name}</span>
          <button onClick={logout} className="rounded-btn bg-white/10 hover:bg-white/20 px-3 py-1.5">
            Sair
          </button>
        </div>
      </header>
      <div className="p-8">
        <Outlet />
      </div>
    </div>
  );
}
