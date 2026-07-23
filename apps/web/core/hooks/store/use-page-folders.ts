/**
 * PP-3: Hook to access the PageFolderStore from React components.
 */

import { useContext } from "react";
import { StoreContext } from "@/lib/store-context";
import type { IPageFolderStore } from "@/store/wiki/pp-page-folder.store";

export const usePageFolders = (): IPageFolderStore => {
  const context = useContext(StoreContext);
  if (context === undefined) throw new Error("usePageFolders must be used within StoreProvider");
  return context.pageFolders;
};
