/**
 * Types for PageFolder — folder hierarchy support for wiki pages.
 * PP-3: Folder management for Pages
 */

export type TPageFolder = {
  id: string;
  name: string;
  description: string;
  icon: string;
  parent_folder: string | null;
  project: string | null;
  workspace: string;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type TPageFolderCreatePayload = {
  name: string;
  description?: string;
  icon?: string;
  parent_folder?: string | null;
};

export type TPageFolderUpdatePayload = Partial<TPageFolderCreatePayload>;

/**
 * Represents a node in the folder tree (either a folder or a page).
 */
export type TFolderTreeNode = {
  id: string;
  name: string;
  type: "folder" | "page";
  parentFolderId: string | null;
  children: TFolderTreeNode[];
  // For pages, holds page-specific data (emoji, etc.)
  data?: Record<string, unknown>;
};
