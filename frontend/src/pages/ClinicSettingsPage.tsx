import { useEffect, useState } from "react";
import { apiRequest, ApiError } from "../api/client";
import { useAuth } from "../context/AuthContext";
import { BillingStatus, ClinicPermissionSettings } from "../types";

type NumberSettingKey = {
  [K in keyof ClinicPermissionSettings]: ClinicPermissionSettings[K] extends number ? K : never;
}[keyof ClinicPermissionSettings];

type BooleanSettingKey = {
  [K in keyof ClinicPermissionSettings]: ClinicPermissionSettings[K] extends boolean ? K : never;
}[keyof ClinicPermissionSettings];

const THRESHOLD_FIELDS: { key: NumberSettingKey; label: string; help: string; suffix: string }[] = [
  {
    key: "no_collection_days",
    label: "Dias sem coleta para alertar",
    help: "Nenhuma tentativa registrada para o objetivo há mais desse número de dias.",
    suffix: "dias",
  },
  {
    key: "regression_window_sessions",
    label: "Janela de sessões para regressão",
    help: "Quantas sessões compõem a média móvel recente e a anterior.",
    suffix: "sessões",
  },
  {
    key: "regression_drop_pp",
    label: "Queda mínima para alertar regressão",
    help: "Queda na média móvel de percentual de acerto, em pontos percentuais.",
    suffix: "p.p.",
  },
  {
    key: "stagnation_session_count",
    label: "Sessões consecutivas para estagnação",
    help: "Quantas sessões consecutivas sem variação relevante disparam o alerta.",
    suffix: "sessões",
  },
  {
    key: "stagnation_band_pp",
    label: "Variação máxima para estagnação",
    help: "Variação (máximo − mínimo) de percentual de acerto tolerada nessas sessões.",
    suffix: "p.p.",
  },
  {
    key: "fading_session_count",
    label: "Sessões consecutivas para candidato a fading",
    help: "Quantas sessões consecutivas de alta independência sugerem reduzir a ajuda.",
    suffix: "sessões",
  },
  {
    key: "fading_independence_pct",
    label: "Independência mínima para candidato a fading",
    help: "Percentual de independência mínimo nessas sessões.",
    suffix: "%",
  },
  {
    key: "mastery_suggestion_session_count",
    label: "Sessões consecutivas para sugestão de domínio",
    help: "Quantas sessões consecutivas de alto acerto sugerem considerar o objetivo dominado.",
    suffix: "sessões",
  },
  {
    key: "mastery_suggestion_accuracy_pct",
    label: "Acerto mínimo para sugestão de domínio",
    help: "Percentual de acerto mínimo nessas sessões.",
    suffix: "%",
  },
];

const TOGGLES: { key: BooleanSettingKey; label: string; help: string }[] = [
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
  const [billingStatus, setBillingStatus] = useState<BillingStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [thresholdError, setThresholdError] = useState<string | null>(null);
  const [thresholdMessage, setThresholdMessage] = useState<string | null>(null);
  const [bulkImportError, setBulkImportError] = useState<string | null>(null);
  const [bulkImportSaving, setBulkImportSaving] = useState(false);

  const isEnterprise = billingStatus?.subscription_plan === "enterprise" && billingStatus.has_paid_access;

  function load() {
    setLoading(true);
    apiRequest<ClinicPermissionSettings>("/clinic/permission-settings")
      .then(setSettings)
      .catch(() => setError("Não foi possível carregar as configurações."))
      .finally(() => setLoading(false));
    apiRequest<BillingStatus>("/billing/status").then(setBillingStatus);
  }

  useEffect(load, []);

  async function handleThresholdSave(key: NumberSettingKey, value: number) {
    if (!settings) return;
    setThresholdError(null);
    setThresholdMessage(null);
    const previous = settings;
    setSettings({ ...settings, [key]: value });
    try {
      const updated = await apiRequest<ClinicPermissionSettings>("/clinic/alert-thresholds", {
        method: "PATCH",
        body: { [key]: value },
      });
      setSettings(updated);
      setThresholdMessage("Limiar atualizado.");
    } catch (err) {
      setSettings(previous);
      if (err instanceof ApiError && err.status === 403) {
        setThresholdError("Limiares de alertas clínicos são configuráveis apenas no plano Enterprise.");
      } else {
        setThresholdError("Não foi possível salvar o limiar.");
      }
    }
  }

  async function handleBulkImportToggle(value: boolean) {
    if (!settings) return;
    setBulkImportError(null);
    const previous = settings;
    setSettings({ ...settings, bulk_import_enabled: value });
    setBulkImportSaving(true);
    try {
      const updated = await apiRequest<ClinicPermissionSettings>("/clinic/permission-settings/bulk-import", {
        method: "POST",
        body: { enabled: value },
      });
      setSettings(updated);
    } catch (err) {
      setSettings(previous);
      if (err instanceof ApiError && err.status === 403) {
        setBulkImportError("Disponível apenas para clínicas no plano Enterprise ativo.");
      } else {
        setBulkImportError("Não foi possível salvar a alteração.");
      }
    } finally {
      setBulkImportSaving(false);
    }
  }

  async function handleToggle(key: BooleanSettingKey, value: boolean) {
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

      <h2 className="text-lg font-semibold text-brand-navy mt-8 mb-2">Alertas Clínicos Inteligentes</h2>
      <p className="text-sm text-neutralState mb-4">
        Limiares das regras automáticas de sem coleta, regressão, estagnação e candidato a fading
        (Seção 29.1 do PRD). Configuráveis apenas no plano Enterprise; os demais planos usam o padrão
        de fábrica.
      </p>

      {!isEnterprise && (
        <div className="bg-brand-grayLight border border-brand-blueLight rounded-card p-4 mb-4 text-sm">
          Estes limiares só podem ser alterados no plano Enterprise. Sua clínica está usando os
          valores padrão de fábrica.
        </div>
      )}
      {thresholdError && <p className="text-danger text-sm mb-4">{thresholdError}</p>}
      {thresholdMessage && <p className="text-success text-sm mb-4">{thresholdMessage}</p>}

      {settings && (
        <div className="bg-white rounded-card shadow-sm divide-y divide-slate-100 max-w-2xl">
          {THRESHOLD_FIELDS.map((field) => (
            <div key={field.key} className="flex items-center justify-between gap-4 px-6 py-4">
              <div>
                <div className="font-medium text-sm">{field.label}</div>
                <div className="text-xs text-neutralState mt-1">{field.help}</div>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <input
                  type="number"
                  min={1}
                  value={settings[field.key] as number}
                  disabled={!isAdmin || !isEnterprise}
                  onChange={(e) => handleThresholdSave(field.key, Number(e.target.value))}
                  className="w-20 h-9 rounded-btn border border-slate-300 px-2 text-sm disabled:opacity-50"
                />
                <span className="text-xs text-neutralState">{field.suffix}</span>
              </div>
            </div>
          ))}
        </div>
      )}

      <h2 className="text-lg font-semibold text-brand-navy mt-8 mb-2">Importação de Pacientes</h2>
      <p className="text-sm text-neutralState mb-4">
        Fica oculta do menu principal por padrão. Libere apenas se a clínica precisar migrar
        pacientes em lote de outro sistema (Addendum v2.1, RF-13) — disponível somente no plano
        Enterprise ativo.
      </p>

      {!isEnterprise && (
        <div className="bg-brand-grayLight border border-brand-blueLight rounded-card p-4 mb-4 text-sm">
          A importação em lote só pode ser habilitada no plano Enterprise.
        </div>
      )}
      {bulkImportError && <p className="text-danger text-sm mb-4">{bulkImportError}</p>}

      {settings && (
        <div className="bg-white rounded-card shadow-sm max-w-2xl">
          <div className="flex items-start justify-between gap-4 px-6 py-4">
            <div>
              <div className="font-medium text-sm">Mostrar "Importar Pacientes" no menu</div>
              <div className="text-xs text-neutralState mt-1">
                Desligado por padrão. Uma vez habilitada, a importação em lote fica visível para
                quem já tem permissão de cadastrar pacientes.
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer shrink-0">
              <input
                type="checkbox"
                checked={settings.bulk_import_enabled}
                disabled={!isAdmin || !isEnterprise || bulkImportSaving}
                onChange={(e) => handleBulkImportToggle(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-11 h-6 bg-slate-300 peer-checked:bg-brand-turquoise rounded-full peer-disabled:opacity-50 transition-colors" />
              <div className="absolute left-1 top-1 w-4 h-4 bg-white rounded-full transition-transform peer-checked:translate-x-5" />
            </label>
          </div>
        </div>
      )}
    </div>
  );
}
