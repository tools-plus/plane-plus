// IW PP-83: /ai-module/skills/ page

import type { Route } from "./+types/page";
import { IWGlobalSkills } from "./iw-global-skills";

export const meta: Route.MetaFunction = () => [{ title: "Global Skills — AI Setup | God Mode" }];

export default function SkillsPage(_props: Route.ComponentProps) {
  return <IWGlobalSkills />;
}
