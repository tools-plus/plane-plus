/**
 * PP-3: Breadcrumb navigation for wiki folders.
 * Shows: Wiki > FolderA > SubFolder > PageName
 */

import { observer } from "mobx-react";
import { ChevronRight } from "lucide-react";
// hooks
import { usePageFolders } from "@/hooks/store/use-page-folders";

type Props = {
  workspaceSlug: string;
  pageId?: string;
  pageName?: string;
};

export const FolderBreadcrumb = observer(function FolderBreadcrumb(props: Props) {
  const { pageId, pageName } = props;
  const folderStore = usePageFolders();

  const folderId = pageId ? folderStore.getPageFolderId(pageId) : null;
  const folderPath = folderStore.getFolderPath(folderId);

  // If no folder path and no page, just show Wiki
  if (folderPath.length === 0 && !pageName) return null;
  // If no folder path, just show Wiki > Page (no breadcrumb needed since it is at root)
  if (folderPath.length === 0) return null;

  return (
    <nav className="flex items-center gap-1 px-4 py-2 text-13 text-secondary" aria-label="Breadcrumb">
      {/* Folder path — Wiki heading is now in the layout header, so breadcrumb starts from the first folder */}
      {folderPath.map((folder, index) => (
        <span key={folder.id} className="flex items-center gap-1">
          {index > 0 && <ChevronRight className="size-3 text-tertiary" />}
          <button
            type="button"
            className="transition-colors hover:text-primary"
            onClick={() => {
              // Expand the folder in sidebar
              folderStore.setFolderExpanded(folder.id, true);
            }}
          >
            {folder.name}
          </button>
        </span>
      ))}

      {/* Current page */}
      {pageName && (
        <span className="flex items-center gap-1">
          <ChevronRight className="size-3 text-tertiary" />
          <span className="max-w-[200px] truncate font-medium text-primary">{pageName}</span>
        </span>
      )}
    </nav>
  );
});
