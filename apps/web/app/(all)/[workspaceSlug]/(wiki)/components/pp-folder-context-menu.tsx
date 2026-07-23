/**
 * PP-3: Context menu for folder actions (rename, delete, new sub-folder, new page).
 */

import { useEffect, useRef } from "react";
import { observer } from "mobx-react";
import { Edit3, FolderPlus, FilePlus, Trash2 } from "lucide-react";
import { cn } from "@plane/utils";

type Props = {
  isOpen: boolean;
  position: { x: number; y: number };
  onClose: () => void;
  onRename: () => void;
  onDelete: () => void;
  onNewSubFolder: () => void;
  onNewPage: () => void;
  canCreateSubFolder: boolean;
};

export const FolderContextMenu = observer(function FolderContextMenu(props: Props) {
  const { isOpen, position, onClose, onRename, onDelete, onNewSubFolder, onNewPage, canCreateSubFolder } = props;
  const menuRef = useRef<HTMLDivElement>(null);

  // Close on click outside
  useEffect(() => {
    if (!isOpen) return;
    const handleClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        onClose();
      }
    };
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    document.addEventListener("mousedown", handleClick);
    document.addEventListener("keydown", handleEscape);
    return () => {
      document.removeEventListener("mousedown", handleClick);
      document.removeEventListener("keydown", handleEscape);
    };
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const items = [
    { label: "Rename", icon: Edit3, onClick: onRename },
    ...(canCreateSubFolder ? [{ label: "New sub-folder", icon: FolderPlus, onClick: onNewSubFolder }] : []),
    { label: "New page here", icon: FilePlus, onClick: onNewPage },
    { label: "Delete folder", icon: Trash2, onClick: onDelete, danger: true },
  ];

  return (
    <div
      ref={menuRef}
      className="shadow-lg fixed z-50 min-w-[180px] rounded-md border border-subtle bg-surface-1 py-1"
      style={{ left: Math.max(40, position.x - 80) }}
    >
      {items.map((item) => (
        <button
          key={item.label}
          type="button"
          className={cn(
            "flex w-full items-center gap-2 px-3 py-1.5 text-13 font-medium hover:bg-layer-transparent-hover",
            "danger" in item && item.danger ? "text-red-500" : "text-secondary"
          )}
          onClick={() => {
            item.onClick();
            onClose();
          }}
        >
          <item.icon className="size-3.5 flex-shrink-0" />
          <span>{item.label}</span>
        </button>
      ))}
    </div>
  );
});
