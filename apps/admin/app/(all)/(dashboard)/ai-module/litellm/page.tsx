// IW PP-79: /ai-module/litellm/ page

import type { Route } from "./+types/page";
import { IWLiteLLMConfig } from "./iw-litellm-config";

export const meta: Route.MetaFunction = () => [{ title: "LiteLLM Config — AI Setup | God Mode" }];

export default function LiteLLMPage(_props: Route.ComponentProps) {
  return <IWLiteLLMConfig />;
}
