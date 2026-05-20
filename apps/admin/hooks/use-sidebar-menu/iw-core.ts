// IW-custom sidebar menu entries — keeps our additions separate from upstream for clean merges.

import { Bot } from "lucide-react";
// types
import type { TSidebarMenuItem } from "./types";

export type TIWSidebarMenuKey = "aiModule";

export const iwSidebarMenuLinks: Record<TIWSidebarMenuKey, TSidebarMenuItem> = {
  aiModule: {
    Icon: Bot,
    name: "AI Setup",
    description: "Configure LiteLLM, global agents, skills, tools and MCP connections.",
    href: `/ai-module/`,
  },
};
