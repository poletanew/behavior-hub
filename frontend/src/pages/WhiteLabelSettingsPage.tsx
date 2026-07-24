import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { apiRequest, ApiError } from "../api/client";
import { WhiteLabelSettings } from "../types";

export default function WhiteLabelSettingsPage() {
  const [settings, setSettings] = useState<WhiteLabelSettings | null>(null);
  const [displayName, setDisplayName] = useState("");
  const [brandColor, setBrandColor] = useState("#1D4ED8");
  const [logoUrl, setLogoUrl] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    apiRequest<WhiteLabelSettings>("/clinic/white-label").then((data) => {
      setSettings(data);
      setDisplayName(data.display_name ?? "");
      setBrandColor(data.brand_color ?? "#1D4ED8");
      setLogoUrl(data.logo_url ?? "");
    });
  }, []);

  async function handleSave(e: FormEvent) {
    e.preventDefault();
    setError(null);
    setSaved(false);
    try {
      const updated = await apiRequest<WhiteLabelSettings>("/clinic/white-label", {
        method: "PATCH",
        body: {
          display_name: displayName || null,
          brand_color: brandColor || null,
          logo_url: logoUrl || null,
        },
      });
      setSettings(updated);
      setSaved(true);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("White-label está disponível apenas para clínicas no plano Enterprise ativo.");
      } else if (err instanceof ApiError && err.status === 422) {
        setError("Cor de destaque inválida. Use um formato hexadecimal, por exemplo #1D4ED8.");
      } else {
        setError("Não foi possível salvar as configurações.");
      }
    }
  }

  if (!settings) return <p className="text-neutralState">Carregando...</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-1">White-label</h1>
      <p className="text-sm text-neutralState mb-6">
        Personalize o nome exibido e a cor de destaque nos relatórios exportados e no Portal da Família
        (Seção 32.9). A marca do Behavior Hub dentro do próprio produto não muda.
      </p>

      {!settings.enabled && (
        <div className="bg-brand-grayLight border border-brand-blueLight rounded-card p-4 mb-6 text-sm">
          Este recurso está disponível apenas para clínicas no plano <strong>Enterprise</strong> com
          assinatura ativa. Veja a página <Link to="/plans" className="text-brand-blue underline">Planos</Link>{" "}
          para fazer upgrade.
        </div>
      )}

      <form onSubmit={handleSave} className="bg-white rounded-card shadow-card p-6 max-w-lg space-y-4">
        <div>
          <label className="block text-sm font-medium mb-1">Nome exibido</label>
          <input
            value={displayName}
            onChange={(e) => setDisplayName(e.target.value)}
            placeholder="Nome da clínica nos relatórios e no Portal da Família"
            disabled={!settings.enabled}
            className="w-full h-10 rounded-btn border border-slate-300 px-3 disabled:bg-slate-50"
          />
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">Cor de destaque</label>
          <div className="flex items-center gap-3">
            <input
              type="color"
              value={brandColor}
              onChange={(e) => setBrandColor(e.target.value)}
              disabled={!settings.enabled}
              className="h-10 w-14 rounded-btn border border-slate-300"
            />
            <input
              value={brandColor}
              onChange={(e) => setBrandColor(e.target.value)}
              disabled={!settings.enabled}
              className="flex-1 h-10 rounded-btn border border-slate-300 px-3 disabled:bg-slate-50"
            />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">URL do logo</label>
          <input
            value={logoUrl}
            onChange={(e) => setLogoUrl(e.target.value)}
            placeholder="https://..."
            disabled={!settings.enabled}
            className="w-full h-10 rounded-btn border border-slate-300 px-3 disabled:bg-slate-50"
          />
          <p className="text-xs text-neutralState mt-1">
            Exibido no Portal da Família. Não aparece nos PDFs exportados (evitamos o backend buscar uma
            URL externa arbitrária ao gerar o arquivo).
          </p>
        </div>
        {error && <p className="text-danger text-sm">{error}</p>}
        {saved && <p className="text-success text-sm">Configurações salvas.</p>}
        <button
          type="submit"
          disabled={!settings.enabled}
          className="rounded-btn bg-brand-turquoise text-white px-4 py-2 text-sm font-medium disabled:opacity-50"
        >
          Salvar
        </button>
      </form>
    </div>
  );
}
