/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

/**
 * IW: app-section registry — single source of truth for top-level app sections
 * (Projects, Wiki, AI, Settings) consumed by:
 *  - the always-visible 3x3 app-switcher in the top navigation chrome
 *  - the Power-K command palette (Cmd+K) section-nav commands
 *
 * Adding a new top-level section in the future = one entry here, not two
 * separate edits. Both surfaces re-render off the same definition.
 */

import type { ComponentType, ReactNode } from "react";
import { Settings as SettingsIcon, Sparkles } from "lucide-react";
import { WikiIcon } from "@plane/propel/icons";
import type { useWorkspacePaths } from "@/hooks/use-workspace-paths";

export type TAppSectionId = "projects" | "wiki" | "ai" | "settings";

type TWorkspacePaths = ReturnType<typeof useWorkspacePaths>;

export type TAppSectionDefinition = {
  /** Stable id for keys/telemetry. */
  id: TAppSectionId;
  /** English label — also used as the i18n key fallback. */
  label: string;
  /**
   * i18n key. The Power-K palette uses `i18n_title` to look up labels;
   * the app-switcher menu falls back to `label` when the key is unresolved.
   */
  i18nKey: string;
  /** Inline JSX node for the app-switcher menu (supports the IW logo PNG). */
  iconNode: ReactNode;
  /** Lucide-style component for the Power-K command icon slot. */
  icon: ComponentType<{ className?: string }>;
  /** Builds the destination href for a given workspace slug. */
  hrefBuilder: (workspaceSlug: string) => string;
  /**
   * Pure selector over `useWorkspacePaths()` output. Keeps the registry
   * free of hook calls so it can be imported from anywhere.
   */
  isActiveSelector: (paths: TWorkspacePaths) => boolean;
};

/** Lucide-style wrapper around the IW PNG so it satisfies the ComponentType
 * shape Power-K commands expect. The 3x3 menu uses iconNode directly. */
const IWLogoIcon: ComponentType<{ className?: string }> = ({ className }) => (
  // eslint-disable-next-line @next/next/no-img-element
  <img src="/favicon/pp-icon-32.png" alt="PP" className={className} />
);

export const APP_SECTIONS: TAppSectionDefinition[] = [
  {
    id: "projects",
    label: "Projects",
    i18nKey: "iw.app_switcher.projects",
    iconNode: <img src="/favicon/pp-icon-32.png" alt="PP" className="size-4" />,
    icon: IWLogoIcon,
    hrefBuilder: (slug) => `/${slug}/`,
    isActiveSelector: (p) => p.isProjectsPath && !p.isNotificationsPath,
  },
  {
    id: "wiki",
    label: "Wiki",
    i18nKey: "iw.app_switcher.wiki",
    iconNode: <WikiIcon className="size-4" />,
    icon: WikiIcon,
    hrefBuilder: (slug) => `/${slug}/wiki/`,
    isActiveSelector: (p) => p.isWikiPath,
  },
  {
    id: "ai",
    label: "AI",
    i18nKey: "iw.app_switcher.ai",
    iconNode: <Sparkles className="size-4" />,
    icon: Sparkles,
    hrefBuilder: (slug) => `/${slug}/ai/`,
    isActiveSelector: (p) => p.isAIPath || p.isAgentDocsPath,
  },
  {
    id: "settings",
    label: "Settings",
    i18nKey: "iw.app_switcher.settings",
    iconNode: <SettingsIcon className="size-4" />,
    icon: SettingsIcon,
    hrefBuilder: (slug) => `/${slug}/settings/`,
    isActiveSelector: (p) => p.isSettingsPath,
  },
];
