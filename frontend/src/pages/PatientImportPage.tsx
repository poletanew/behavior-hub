import { ChangeEvent, useState } from "react";
import { apiUpload, ApiError } from "../api/client";
import { PatientImportCommitResult, PatientImportPreview } from "../types";

export default function PatientImportPage() {
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<PatientImportPreview | null>(null);
  const [result, setResult] = useState<PatientImportCommitResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  function handleFileChange(e: ChangeEvent<HTMLInputElement>) {
    setFile(e.target.files?.[0] ?? null);
    setPreview(null);
    setResult(null);
    setError(null);
  }

  async function handlePreview() {
    if (!file) return;
    setError(null);
    setLoading(true);
    setResult(null);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const data = await apiUpload<PatientImportPreview>("/patients/import/preview", formData);
      setPreview(data);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Você não tem permissão para importar pacientes.");
      } else {
        setError("Não foi possível ler o arquivo CSV.");
      }
    } finally {
      setLoading(false);
    }
  }

  async function handleCommit() {
    if (!file) return;
    setError(null);
    setLoading(true);
    try {
      const formData = new FormData();
      formData.append("file", file);
      const data = await apiUpload<PatientImportCommitResult>("/patients/import/commit", formData);
      setResult(data);
      setPreview(null);
      setFile(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setError("Você não tem permissão para importar pacientes.");
      } else {
        setError("Não foi possível concluir a importação.");
      }
    } finally {
      setLoading(false);
    }
  }

  const validCount = preview?.rows.filter((r) => r.valid).length ?? 0;
  const invalidCount = (preview?.rows.length ?? 0) - validCount;

  return (
    <div>
      <h1 className="text-2xl font-bold text-brand-navy mb-2">Importar Pacientes (CSV)</h1>
      <p className="text-sm text-neutralState mb-6">
        Envie um arquivo CSV com colunas de nome e data de nascimento (aceita cabeçalhos em português, ex.:
        "nome", "data de nascimento", "responsável", "diagnóstico").
      </p>

      <div className="bg-white rounded-card shadow-sm p-6 mb-6 max-w-xl flex flex-wrap gap-3 items-end">
        <div className="flex-1 min-w-[200px]">
          <label className="block text-sm font-medium mb-1">Arquivo CSV</label>
          <input
            type="file"
            accept=".csv,text/csv"
            onChange={handleFileChange}
            className="w-full text-sm"
          />
        </div>
        <button
          type="button"
          disabled={!file || loading}
          onClick={handlePreview}
          className="h-10 rounded-btn border border-brand-navy text-brand-navy px-4 text-sm font-medium disabled:opacity-50"
        >
          Pré-visualizar
        </button>
      </div>

      {error && <p className="text-danger text-sm mb-4">{error}</p>}

      {preview && (
        <div className="mb-6">
          {preview.missing_required_columns.length > 0 ? (
            <div className="bg-danger/10 border border-danger rounded-card p-4 text-sm text-danger mb-4">
              Colunas obrigatórias não encontradas: {preview.missing_required_columns.join(", ")}
            </div>
          ) : (
            <>
              <div className="flex items-center justify-between mb-3 max-w-3xl">
                <p className="text-sm text-neutralState">
                  {preview.total_rows} linha(s) encontrada(s) — {validCount} válida(s), {invalidCount} com
                  erro.
                </p>
                <button
                  type="button"
                  disabled={loading || validCount === 0}
                  onClick={handleCommit}
                  className="h-10 rounded-btn bg-brand-turquoise text-white px-4 text-sm font-medium disabled:opacity-50"
                >
                  Confirmar importação
                </button>
              </div>
              <div className="bg-white rounded-card shadow-sm overflow-hidden max-w-3xl">
                <table className="w-full text-sm">
                  <thead className="bg-brand-navy text-white">
                    <tr>
                      <th className="text-left px-4 py-3">Linha</th>
                      <th className="text-left px-4 py-3">Nome</th>
                      <th className="text-left px-4 py-3">Nascimento</th>
                      <th className="text-left px-4 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row) => (
                      <tr key={row.row_number} className={row.valid ? undefined : "bg-danger/5"}>
                        <td className="px-4 py-3">{row.row_number}</td>
                        <td className="px-4 py-3">{row.name ?? "—"}</td>
                        <td className="px-4 py-3">{row.birth_date ?? "—"}</td>
                        <td className="px-4 py-3">
                          {row.valid ? (
                            <span className="text-success">Válido</span>
                          ) : (
                            <span className="text-danger">{row.error}</span>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </div>
      )}

      {result && (
        <div className="bg-white rounded-card shadow-sm p-6 max-w-xl">
          <h2 className="font-semibold text-brand-navy mb-2">Importação concluída</h2>
          <p className="text-sm mb-3">{result.imported_count} paciente(s) importado(s) com sucesso.</p>
          {result.rejected.length > 0 && (
            <>
              <p className="text-sm text-danger mb-2">{result.rejected.length} linha(s) rejeitada(s):</p>
              <ul className="text-sm space-y-1">
                {result.rejected.map((rej) => (
                  <li key={rej.row_number}>
                    Linha {rej.row_number} ({rej.name ?? "sem nome"}): {rej.reason}
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>
      )}
    </div>
  );
}
