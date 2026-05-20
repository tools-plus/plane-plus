// IW: /ai-module/ → redirect to /ai-module/litellm/

import { Navigate } from "react-router";

export default function IWAiModuleIndex() {
  return <Navigate to="/ai-module/litellm" replace />;
}
