import { Sparkles } from "lucide-react";

// Seção 12.1 do PRD — regra de produto, não só detalhe visual: todo conteúdo
// gerado por IA precisa exibir este aviso, sempre com o mesmo texto, antes de
// qualquer ação de salvar/publicar/ativar.
export default function AiDraftNote() {
  return (
    <div className="flex items-center gap-1.5 bg-[#F5F3FF] border border-brand-purple rounded-lg px-2.5 py-1.5 mb-2.5 text-[11.5px] text-brand-purple font-bold">
      <Sparkles size={13} /> Gerado por IA — revise antes de salvar/publicar/ativar
    </div>
  );
}
