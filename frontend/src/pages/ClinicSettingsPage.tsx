import { useEffect, useState } from "react";
import { apiRequest, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { ClinicPermissionSettings } from "../types";

const TOGGLES: { key: keyof ClinicPermissionSettings; label: string; help: string }[] = [
  {
    key: "professionals_can_create_patients",
    label: "Profissionais podem cadastrar pacientes",
    help: "Por padrão, somente administradores da clínica cadastram novos pacientes.",
  },
  {
    key: "supervisors_can_register_sessions",
    label: "Supervisores podem registrar atendimentos",
    help: "Habilitado por padrão.",
  },
  {
    key: "supervisors_can_edit_any_objective_area",
    label: "Supervisores podem editar objetivos de qualquer área",
    help: "Por padrão, supervisores só editam objetivos das próprias atribuições.",
  },
  {
    key: "admins_can_edit_any_objective_area",
    label: "Administradores podem editar objetivos de qualquer área",
    help: "Habilitado por padrão.",
  },
  {
    key: "supervisors_can_restore_deleted_data",
    label: "Supervisores podem restaurar dados excluídos",
    help: "Por padrão, somente administradores restauram registros excluídos.",
  },
  {
    key: "supervisors_can_generate_invitations",
    label: "Supervisores podem gerar convites de profissionais",
    help: "Por padrão, somente administradores geram convites.",
  },
];

export default function ClinicSettingsPage() {
  const { user } = useAuth();
  const isAdmin = user?.user_type === "clinic_admin";
  const [settings, setSettings] = useState<ClinicPermissionSettings | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function load() {
    setLoading(true);
    apiRequest<ClinicPermissionSettings>("/clinic/permission-settings")
      .then(setSettings)
      .catch(() => setError("Não foi possível carregar as configurações."))
      .finally(() => setLoading(false));
  }

  useEffect(load, []);

  async function handleToggle(key: keyof ClinicPermissionSettings, value: boolean) {
    if (!settings) return;
    setError(null);
    const previous = settings;
    setSettings({ ...settings, [key]: value });
    setSaving(true);
    try {
      const updated = await apiRequest<ClinicPermissionSettings>("/clinic/permission-settings", {
        method: "PATCH",
        body: { [key]: value },
      });
      setSettings(updated);
    } catch (err) {
      setSettings(previous);
      if (err instanceof ApiError && err.status === 403) {
        setError("Somente administradores da clínica podem alterar estas configurações.");
      } else {
        setError("Não foi possível salvar a alteração.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-2">Configurações da Clínica</h1>
      <p className="text-sm text-neutralState mb-6">
        Permissões configuráveis para profissionais e supervisores (Seção 17.1 do PRD).
      </p>

      {!isAdmin && (
        <div className="bg-brand-grayLight border border-brand-blueLight rounded-card p-4 mb-6 text-sm">
          Apenas administradores da clínica podem alterar estas configurações. Você pode visualizá-las.
        </div>
      )}
      {error && <p className="text-danger text-sm mb-4">{error}</p>}

      {loading || !settings ? (
        <p className="text-neutralState">Carregando...</p>
      ) : (
        <div className="bg-white rounded-card shadow-sm divide-y divide-slate-100 max-w-2xl">
          {TOGGLES.map((toggle) => (
            <div key={toggle.key} className="flex items-start justify-between gap-4 px-6 py-4">
              <div>
                <div className="font-medium text-sm">{toggle.label}</div>
                <div className="text-xs text-neutralState mt-1">{toggle.help}</div>
              </div>
              <label className="relative inline-flex items-center cursor-pointer shrink-0">
                <input
                  type="checkbox"
                  checked={settings[toggle.key]}
                  disabled={!isAdmin || saving}
                  onChange={(e) => handleToggle(toggle.key, e.target.checked)}
                  className="sr-only peer"
                />
                <div className="w-11 h-6 bg-slate-300 peer-checked:bg-brand-turquoise rounded-full peer-disabled:opacity-50 transition-colors" />
                <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
              </label>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
