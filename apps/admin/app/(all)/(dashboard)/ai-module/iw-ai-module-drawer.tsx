// IW: Shared slide-over drawer for AI Module create/edit forms.

import type { ReactNode } from "react";
import { X } from "lucide-react";
import { cn } from "@plane/utils";

type TIWDrawerProps = {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: ReactNode;
};

export function IWAIModuleDrawer({ isOpen, onClose, title, children }: TIWDrawerProps) {
  if (!isOpen) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-40 bg-black/20" onClick={onClose} aria-hidden="true" />
      {/* Panel */}
      <div
        className={cn(
          "shadow-xl fixed inset-y-0 right-0 z-50 flex w-full max-w-xl flex-col bg-surface-1 transition-transform duration-200",
          isOpen ? "translate-x-0" : "translate-x-full"
        )}
      >
        {/* Header */}
        <div className="flex items-center justify-between border-b border-subtle px-6 py-4">
          <h2 className="text-h5-semibold text-primary">{title}</h2>
          <button
            type="button"
            className="rounded-md p-1 text-secondary hover:bg-layer-transparent-hover hover:text-primary"
            onClick={onClose}
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {/* Body */}
        <div className="vertical-scrollbar scrollbar-sm flex-1 overflow-y-auto px-6 py-6">{children}</div>
      </div>
    </>
  );
}
