/**
 * Copyright (c) 2023-present Plane Software, Inc. and contributors
 * SPDX-License-Identifier: AGPL-3.0-only
 * See the LICENSE file for details.
 */

import { index, layout, route } from "@react-router/dev/routes";
import type { RouteConfig } from "@react-router/dev/routes";

export default [
  layout("./(all)/(home)/layout.tsx", [index("./(all)/(home)/page.tsx")]),
  layout("./(all)/(dashboard)/layout.tsx", [
    route("general", "./(all)/(dashboard)/general/page.tsx"),
    route("workspace", "./(all)/(dashboard)/workspace/page.tsx"),
    route("workspace/create", "./(all)/(dashboard)/workspace/create/page.tsx"),
    route("email", "./(all)/(dashboard)/email/page.tsx"),
    route("authentication", "./(all)/(dashboard)/authentication/page.tsx"),
    route("authentication/github", "./(all)/(dashboard)/authentication/github/page.tsx"),
    route("authentication/gitlab", "./(all)/(dashboard)/authentication/gitlab/page.tsx"),
    route("authentication/google", "./(all)/(dashboard)/authentication/google/page.tsx"),
    route("authentication/gitea", "./(all)/(dashboard)/authentication/gitea/page.tsx"),
    route("ai", "./(all)/(dashboard)/ai/page.tsx"),
    route("image", "./(all)/(dashboard)/image/page.tsx"),
    // IW: AI Setup tab (PP-79, PP-83) — separate from Plane's "Artificial intelligence" tab
    route("ai-module", "./(all)/(dashboard)/ai-module/iw-ai-module-layout.tsx", [
      index("./(all)/(dashboard)/ai-module/iw-ai-module-index.tsx"),
      route("litellm", "./(all)/(dashboard)/ai-module/litellm/page.tsx"),
      route("agents", "./(all)/(dashboard)/ai-module/agents/page.tsx"),
      route("skills", "./(all)/(dashboard)/ai-module/skills/page.tsx"),
      route("tools", "./(all)/(dashboard)/ai-module/tools/page.tsx"),
      route("mcp-connections", "./(all)/(dashboard)/ai-module/mcp-connections/page.tsx"),
    ]),
  ]),
  // Catch-all route for 404 handling - must be last
  route("*", "./components/404.tsx"),
] satisfies RouteConfig;
