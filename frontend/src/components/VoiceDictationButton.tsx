import { useSpeechToText } from "../hooks/useSpeechToText";

/**
 * Seção 32.12 — ditar a observação por voz durante o atendimento (mãos
 * ocupadas conduzindo a sessão). O texto transcrito só é anexado ao campo
 * já existente — nunca salva sozinho, sempre editável antes do envio.
 */
export default function VoiceDictationButton({
  onTranscript,
  className,
}: {
  onTranscript: (transcript: string) => void;
  className?: string;
}) {
  const { isSupported, isListening, start, stop } = useSpeechToText(onTranscript);

  if (!isSupported) return null;

  return (
    <button
      type="button"
      onClick={() => (isListening ? stop() : start())}
      title={isListening ? "Parar ditado" : "Ditar por voz"}
      className={
        className ??
        `h-9 shrink-0 rounded-btn border px-3 text-sm font-medium ${
          isListening ? "bg-danger text-white border-danger" : "bg-white border-slate-300 text-brand-navy"
        }`
      }
    >
      {isListening ? "Parar" : "Ditar"}
    </button>
  );
}
