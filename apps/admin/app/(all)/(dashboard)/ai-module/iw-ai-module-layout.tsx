// IW: AI Module sub-layout — header, top tab bar, and Outlet for sub-pages.

import { NavLink, Outlet } from "react-router";
import { cn } from "@plane/utils";

const AI_MODULE_TABS = [
  { label: "LiteLLM", href: "/ai-module/litellm" },
  { label: "Agents", href: "/ai-module/agents" },
  { label: "Skills", href: "/ai-module/skills" },
  { label: "MCP Connections", href: "/ai-module/mcp-connections" },
  { label: "Tools", href: "/ai-module/tools" },
] as const;

export default function IWAiModuleLayout() {
  return (
    <div className="mx-auto flex h-full w-full max-w-[1000px] flex-col py-4 md:px-4 2xl:max-w-[1200px]">
      {/* Page header */}
      <div className="mx-4 mb-0 shrink-0 border-b border-subtle pb-4">
        <div className="text-h5-semibold text-primary">AI Setup</div>
        <div className="text-body-sm-regular text-secondary">
          Configure LiteLLM, global agents, skills, tools and MCP connections.
        </div>
      </div>

      {/* Sub-nav tabs */}
      <div className="mx-4 flex shrink-0 items-center gap-0 border-b border-subtle">
        {AI_MODULE_TABS.map((tab) => (
          <NavLink
            key={tab.href}
            to={tab.href}
            className={({ isActive }) =>
              cn(
                "-mb-px border-b-2 px-4 py-2.5 text-body-sm-medium whitespace-nowrap transition-colors",
                isActive
                  ? "border-accent-primary text-accent-primary"
                  : "border-transparent text-secondary hover:text-primary"
              )
            }
          >
            {tab.label}
          </NavLink>
        ))}
      </div>

      {/* Sub-page content — scrollable */}
      <div className="vertical-scrollbar scrollbar-sm flex-1 overflow-y-auto px-4 py-6">
        <Outlet />
      </div>
    </div>
  );
}
