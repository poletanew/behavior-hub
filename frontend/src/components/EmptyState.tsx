import { ReactNode } from "react";

interface EmptyStateProps {
  icon?: string;
  title?: string;
  message: string;
  action?: ReactNode;
}

/** Addendum v2.1, RF-17 — estado vazio com ícone amigável em vez de só texto
 * cinza: o primeiro contato de uma clínica nova com uma tela deve parecer um
 * convite, não uma tela quebrada. */
export default function EmptyState({ icon = "🌱", title, message, action }: EmptyStateProps) {
  return (
    <div className="bg-white rounded-card shadow-sm p-10 text-center animate-fade-in">
      <div className="mx-auto mb-3 flex h-14 w-14 items-center justify-center rounded-full bg-brand-turquoise/10 text-2xl">
        {icon}
      </div>
      {title && <p className="font-medium text-brand-navy mb-1">{title}</p>}
      <p className="text-neutralState text-sm">{message}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
