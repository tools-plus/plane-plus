/**
 * PP-3: PageFolder service — real API calls for folder CRUD.
 * Endpoints: /api/workspaces/{slug}/page-folders/
 */

import { API_BASE_URL } from "@plane/constants";
import type {
  TPageFolder,
  TPageFolderCreatePayload,
  TPageFolderUpdatePayload,
} from "@/store/wiki/iw-page-folder.types";
import { APIService } from "@/services/api.service";

export class PageFolderService extends APIService {
  constructor() {
    super(API_BASE_URL);
  }

  /**
   * Fetch all folders for a workspace.
   */
  async fetchAll(workspaceSlug: string): Promise<TPageFolder[]> {
    return this.get(`/api/workspaces/${workspaceSlug}/page-folders/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Fetch a single folder by ID.
   */
  async fetchById(workspaceSlug: string, folderId: string): Promise<TPageFolder> {
    return this.get(`/api/workspaces/${workspaceSlug}/page-folders/${folderId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Create a new folder.
   */
  async create(workspaceSlug: string, payload: TPageFolderCreatePayload): Promise<TPageFolder> {
    return this.post(`/api/workspaces/${workspaceSlug}/page-folders/`, payload)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Update an existing folder (rename, move parent, change icon).
   */
  async update(workspaceSlug: string, folderId: string, payload: TPageFolderUpdatePayload): Promise<TPageFolder> {
    return this.patch(`/api/workspaces/${workspaceSlug}/page-folders/${folderId}/`, payload)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Delete a folder. Backend promotes children to parent and unsets pages.
   */
  async remove(workspaceSlug: string, folderId: string): Promise<void> {
    return this.delete(`/api/workspaces/${workspaceSlug}/page-folders/${folderId}/`)
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }

  /**
   * Move a page into a folder (or to root if folderId is null).
   * Uses the existing page PATCH endpoint with the folder field.
   */
  async movePageToFolder(workspaceSlug: string, pageId: string, folderId: string | null): Promise<void> {
    return this.patch(`/api/workspaces/${workspaceSlug}/pages/${pageId}/`, { folder: folderId })
      .then((response) => response?.data)
      .catch((error) => {
        throw error?.response?.data;
      });
  }
}
