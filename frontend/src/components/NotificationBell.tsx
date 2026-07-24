import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { apiRequest } from "../api/client";
import { AppNotification, Objective } from "../types";

function timeAgo(value: string): string {
  const diffMs = Date.now() - new Date(value).getTime();
  const minutes = Math.floor(diffMs / 60000);
  if (minutes < 1) return "agora";
  if (minutes < 60) return `${minutes} min atrás`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h atrás`;
  return `${Math.floor(hours / 24)}d atrás`;
}

export default function NotificationBell() {
  const [notifications, setNotifications] = useState<AppNotification[]>([]);
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  function load() {
    apiRequest<AppNotification[]>("/notifications").then(setNotifications);
  }

  useEffect(() => {
    load();
    const interval = setInterval(load, 30000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const unreadCount = notifications.filter((n) => !n.read_at).length;

  async function handleOpenNotification(notification: AppNotification) {
    if (!notification.read_at) {
      await apiRequest(`/notifications/${notification.id}/read`, { method: "POST" });
    }
    setOpen(false);
    load();
    if (notification.entity_type === "objective") {
      const objective = await apiRequest<Objective>(`/objectives/${notification.entity_id}`);
      navigate(`/patients/${objective.patient_id}/treatment-plan`);
    }
  }

  async function handleMarkAllRead() {
    await apiRequest("/notifications/read-all", { method: "POST" });
    load();
  }

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="relative w-9 h-9 rounded-full bg-white shadow-card hover:bg-slate-50 flex items-center justify-center"
        aria-label="Notificações"
      >
        🔔
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 bg-danger text-white text-[10px] rounded-full w-4 h-4 flex items-center justify-center">
            {unreadCount > 9 ? "9+" : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white text-brand-graphite rounded-card shadow-lg border border-slate-200 z-50 max-h-96 overflow-y-auto">
          <div className="flex items-center justify-between px-4 py-2 border-b border-slate-100">
            <span className="font-semibold text-sm">Notificações</span>
            {unreadCount > 0 && (
              <button onClick={handleMarkAllRead} className="text-xs text-brand-blue underline">
                Marcar todas como lidas
              </button>
            )}
          </div>
          {notifications.length === 0 ? (
            <div className="px-4 py-6 text-center text-sm text-neutralState">Nenhuma notificação.</div>
          ) : (
            <ul>
              {notifications.map((n) => (
                <li key={n.id}>
                  <button
                    onClick={() => handleOpenNotification(n)}
                    className={`w-full text-left px-4 py-3 text-sm border-b border-slate-50 hover:bg-slate-50 ${
                      !n.read_at ? "bg-info/5" : ""
                    }`}
                  >
                    <div>{n.message}</div>
                    <div className="text-xs text-neutralState mt-1">{timeAgo(n.created_at)}</div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}
