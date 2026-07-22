import { Outlet, useLocation } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

export default function FamilyPortalLayout() {
  const { user, logout } = useAuth();
  const location = useLocation();

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-brand-navy text-white px-8 py-4 flex items-center justify-between">
        <div>
          <div className="text-lg font-bold">Behavior Hub</div>
          <div className="text-[10px] uppercase tracking-wide text-brand-turquoise">Portal da Família</div>
        </div>
        <div className="flex items-center gap-4 text-sm">
          <span>{user?.name}</span>
          <button onClick={logout} className="rounded-btn bg-white/10 hover:bg-white/20 px-3 py-1.5">
            Sair
          </button>
        </div>
      </header>
      <div key={location.pathname} className="animate-fade-in">
        <Outlet />
      </div>
    </div>
  );
}
