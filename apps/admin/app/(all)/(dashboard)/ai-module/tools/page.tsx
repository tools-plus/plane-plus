// IW PP-83: /ai-module/tools/ page

import type { Route } from "./+types/page";
import { IWGlobalTools } from "./iw-global-tools";

export const meta: Route.MetaFunction = () => [{ title: "Global Tools — AI Setup | God Mode" }];

export default function ToolsPage(_props: Route.ComponentProps) {
  return <IWGlobalTools />;
}
