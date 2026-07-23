/**
 * PP-3: WikiPageNode — renders a single page in the wiki sidebar tree.
 * Supports drag (to move between folders) and delete.
 */

import { observer } from "mobx-react";
import Link from "next/link";
import { Trash2 } from "lucide-react";
import { cn } from "@plane/utils";
// components
import { SidebarNavItem } from "@/components/sidebar/sidebar-navigation";

// Helper to get emoji from page logo_props
const getPageEmoji = (page: { logo_props?: Record<string, unknown> }): string => {
  const logoProps = page.logo_props as { in_use?: string; emoji?: { value?: string } } | undefined;
  if (logoProps?.in_use === "emoji" && logoProps?.emoji?.value) {
    return logoProps.emoji.value;
  }
  return "\uD83D\uDCC4"; // default page emoji
};

type Props = {
  pageId: string;
  page: { id?: string | null; name?: string; logo_props?: Record<string, unknown> };
  wikiBasePath: string;
  depth: number;
  isActive: boolean;
  onDelete?: (e: React.MouseEvent, pageId: string) => void;
};

export const WikiPageNode = observer(function WikiPageNode(props: Props) {
  const { pageId, page, wikiBasePath, depth, isActive, onDelete } = props;

  // Offset page icon to align with folder icon (skip past chevron 16px + gap 6px = 22px)
  const chevronSpace = 16;
  const indentPx = depth * 16 + chevronSpace;

  const handleDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData("text/plain", pageId);
    e.dataTransfer.setData("application/x-wiki-page-id", pageId);
    e.dataTransfer.effectAllowed = "move";
  };

  return (
    <div style={{ paddingLeft: `${indentPx}px` }}>
      <Link href={`${wikiBasePath}/${pageId}`}>
        <div draggable onDragStart={handleDragStart}>
          <SidebarNavItem isActive={isActive}>
            <div className="group flex w-full items-center justify-between gap-1 py-[1px]">
              <div className="flex min-w-0 items-center gap-1.5">
                <span className="text-sm flex size-4 flex-shrink-0 items-center justify-center">
                  {getPageEmoji(page)}
                </span>
                <p className={cn("truncate text-13 leading-5 font-medium")}>{page.name || "Untitled"}</p>
              </div>
              {onDelete && (
                <button
                  type="button"
                  className="hover:text-danger flex-shrink-0 rounded p-0.5 text-secondary opacity-0 group-hover:opacity-100 hover:bg-layer-transparent-hover"
                  onClick={(e) => onDelete(e, pageId)}
                  title="Delete page"
                >
                  <Trash2 className="size-3.5" />
                </button>
              )}
            </div>
          </SidebarNavItem>
        </div>
      </Link>
    </div>
  );
});
