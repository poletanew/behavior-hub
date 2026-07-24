import { useEffect, useRef, useState } from "react";
import { Loader2, MessageCircle, Send, Sparkles, X } from "lucide-react";
import { apiRequest } from "../api/client";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

const GREETING: ChatMessage = {
  role: "assistant",
  content:
    "Olá! Sou a IA do Behavior Hub. Posso ajudar com dúvidas sobre o sistema, sugerir estratégias e treinos, ou tirar dúvidas gerais sobre análise do comportamento. Como posso ajudar?",
};

// Botão flutuante "Fale com a IA do Behavior Hub" (Seção 12.1/14.5) —
// presente em todas as telas autenticadas (montado no Layout). O texto e o
// comportamento replicam o protótipo de referência; a chamada real à IA
// passa pelo backend (POST /ai/chat), que guarda a chave da Anthropic como
// variável de ambiente no servidor — nunca exposta aqui no frontend.
export default function AIChatWidget() {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([GREETING]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
  }, [messages, open, loading]);

  async function send() {
    if (!input.trim() || loading) return;
    const userMsg: ChatMessage = { role: "user", content: input.trim() };
    const nextMessages = [...messages, userMsg];
    setMessages(nextMessages);
    setInput("");
    setLoading(true);
    setError("");
    try {
      const result = await apiRequest<{ reply: string }>("/ai/chat", {
        method: "POST",
        body: { messages: nextMessages },
      });
      setMessages([...nextMessages, { role: "assistant", content: result.reply }]);
    } catch {
      setError("Não foi possível falar com a IA agora. Tente novamente em instantes.");
    } finally {
      setLoading(false);
    }
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="fixed bottom-5 right-5 z-[70] flex items-center gap-2 rounded-full px-5 py-3.5 text-white text-[13px] font-bold shadow-[0_8px_24px_rgba(15,37,87,0.35)]"
        style={{ background: "linear-gradient(135deg, #1D4ED8, #14B8A6)" }}
      >
        <Sparkles size={16} /> Fale com a IA do Behavior Hub
      </button>
    );
  }

  return (
    <div className="fixed bottom-5 right-5 z-[70] w-[350px] h-[480px] bg-white rounded-2xl shadow-[0_16px_48px_rgba(15,37,87,0.35)] flex flex-col overflow-hidden border border-borderMuted">
      <div className="bg-brand-navy px-4 py-3.5 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-2 text-white font-bold text-[13.5px]">
          <MessageCircle size={16} className="text-brand-turquoise" /> IA Behavior Hub
        </div>
        <X size={17} className="cursor-pointer text-white" onClick={() => setOpen(false)} />
      </div>

      <div ref={scrollRef} className="flex-1 overflow-y-auto p-3.5 flex flex-col gap-2.5 bg-brand-grayLight">
        {messages.map((m, i) => (
          <div
            key={i}
            className={`max-w-[85%] px-3.5 py-2.5 rounded-2xl text-[12.5px] leading-relaxed whitespace-pre-wrap ${
              m.role === "user"
                ? "self-end bg-brand-blue text-white"
                : "self-start bg-white text-brand-graphite shadow-card"
            }`}
          >
            {m.content}
          </div>
        ))}
        {loading && (
          <div className="self-start px-3.5 py-2.5 rounded-2xl bg-white shadow-card flex items-center gap-1.5">
            <Loader2 size={13} className="animate-spin" />
            <span className="text-xs text-neutralState">digitando...</span>
          </div>
        )}
        {error && <div className="text-[11.5px] text-danger">{error}</div>}
      </div>

      <div className="flex gap-1.5 p-2.5 border-t border-borderMuted shrink-0 bg-white">
        <input
          className="flex-1 rounded-lg border border-borderMuted px-3 py-2 text-[13.5px] focus:outline-none focus:ring-2 focus:ring-brand-blueLight"
          placeholder="Pergunte alguma coisa..."
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && send()}
          disabled={loading}
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="rounded-lg bg-brand-turquoise text-white px-3 py-2 disabled:opacity-50"
        >
          <Send size={15} />
        </button>
      </div>
      <div className="text-[9.5px] text-neutralState text-center px-2.5 pb-2 bg-white">
        As respostas são sugestões — sempre use seu julgamento clínico.
      </div>
    </div>
  );
}
