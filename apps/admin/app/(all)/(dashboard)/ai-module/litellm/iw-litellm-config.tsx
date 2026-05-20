// IW PP-79: LiteLLM Config page — God-mode admin AI Module.

import { useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { ChevronDown, ChevronRight } from "lucide-react";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Input, ToggleSwitch } from "@plane/ui";
import { cn } from "@plane/utils";
import { ControllerInput } from "@/components/common/controller-input";

// ---- Types ------------------------------------------------------------------

export type TLiteLLMProvider = string; // any LiteLLM-supported provider slug

export type TLiteLLMConfig = {
  id?: string;
  endpoint: string;
  master_key: string;
  provider: TLiteLLMProvider;
  model_routing: string; // JSON string
  default_workspace_budget: string;
  max_workspace_budget: string;
  default_agent_budget: string;
  max_agent_budget: string;
  is_active: boolean;
};

const DEFAULT_VALUES: TLiteLLMConfig = {
  endpoint: "http://plane-litellm:4000",
  master_key: "",
  provider: "anthropic",
  model_routing: "",
  default_workspace_budget: "",
  max_workspace_budget: "",
  default_agent_budget: "",
  max_agent_budget: "",
  is_active: false,
};

// ---- Helpers ----------------------------------------------------------------

async function fetchLiteLLMConfig(): Promise<TLiteLLMConfig | null> {
  const res = await fetch("/api/god-mode/ai/litellm-config/");
  if (res.status === 404) return null;
  if (!res.ok) throw new Error("Failed to fetch LiteLLM config");
  return res.json() as Promise<TLiteLLMConfig>;
}

async function saveLiteLLMConfig(data: Partial<TLiteLLMConfig>): Promise<TLiteLLMConfig> {
  const res = await fetch("/api/god-mode/ai/litellm-config/", {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error("Failed to save LiteLLM config");
  return res.json() as Promise<TLiteLLMConfig>;
}

async function testLiteLLMConnection(): Promise<{ success: boolean; message: string }> {
  const res = await fetch("/api/god-mode/ai/litellm-config/test-connection/", { method: "POST" });
  if (!res.ok) {
    const body = (await res.json().catch(() => ({ detail: "Connection failed" }))) as { detail?: string };
    return { success: false, message: body?.detail ?? "Connection failed" };
  }
  return { success: true, message: "Connection successful" };
}

// ---- Component --------------------------------------------------------------

export function IWLiteLLMConfig() {
  const [isLoading, setIsLoading] = useState(true);
  const [notConfigured, setNotConfigured] = useState(false);
  const [modelRoutingExpanded, setModelRoutingExpanded] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [isTesting, setIsTesting] = useState(false);

  const {
    handleSubmit,
    control,
    reset,
    formState: { errors, isSubmitting, isDirty },
  } = useForm<TLiteLLMConfig>({ defaultValues: DEFAULT_VALUES });

  // Load config on mount
  useEffect(() => {
    fetchLiteLLMConfig()
      .then((config) => {
        if (!config) {
          setNotConfigured(true);
        } else {
          reset({ ...config, master_key: "" }); // master_key not returned on GET
        }
      })
      .catch(() =>
        setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to load LiteLLM configuration." })
      )
      .finally(() => setIsLoading(false));
  }, [reset]);

  const onSubmit = async (formData: TLiteLLMConfig) => {
    try {
      await saveLiteLLMConfig(formData);
      setNotConfigured(false);
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Saved", message: "LiteLLM configuration updated." });
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to save LiteLLM configuration." });
    }
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const result = await testLiteLLMConnection();
      setTestResult(result);
    } catch {
      setTestResult({ success: false, message: "An unexpected error occurred." });
    } finally {
      setIsTesting(false);
    }
  };

  if (isLoading) {
    return (
      <div className="animate-pulse space-y-4">
        <div className="h-10 w-2/3 rounded bg-layer-transparent-hover" />
        <div className="h-10 w-1/2 rounded bg-layer-transparent-hover" />
        <div className="h-10 w-1/3 rounded bg-layer-transparent-hover" />
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="max-w-4xl space-y-8">
      {notConfigured && (
        <div className="rounded-md border border-subtle bg-layer-transparent-hover px-4 py-3 text-body-sm-regular text-secondary">
          No LiteLLM configuration found. Fill in the details below to get started.
        </div>
      )}

      {/* Core connection fields */}
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        <ControllerInput
          control={control}
          type="text"
          name="endpoint"
          label="Endpoint"
          placeholder="http://plane-litellm:4000"
          error={Boolean(errors.endpoint)}
          required={false}
        />
        <ControllerInput
          control={control}
          type="password"
          name="master_key"
          label="Master Key"
          placeholder="sk-••••••••"
          error={Boolean(errors.master_key)}
          required={false}
        />
      </div>

      {/* Provider — free text, any LiteLLM-supported provider slug */}
      <div className="flex max-w-xs flex-col gap-1">
        <h4 className="text-13 text-tertiary">Provider</h4>
        <p className="text-11 text-tertiary">Any LiteLLM provider slug (e.g. anthropic, openai, bedrock, ollama)</p>
        <Controller
          control={control}
          name="provider"
          render={({ field }) => <Input {...field} placeholder="anthropic" className="rounded-md border-subtle" />}
        />
      </div>

      {/* Budget fields */}
      <div>
        <div className="pb-3 text-body-sm-medium text-primary">Budget limits ($/month)</div>
        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          {(
            [
              { name: "default_workspace_budget", label: "Default workspace budget" },
              { name: "max_workspace_budget", label: "Max workspace budget" },
              { name: "default_agent_budget", label: "Default agent budget" },
              { name: "max_agent_budget", label: "Max agent budget" },
            ] as const
          ).map((f) => (
            <div key={f.name} className="flex flex-col gap-1">
              <h4 className="text-13 text-tertiary">{f.label}</h4>
              <Controller
                control={control}
                name={f.name}
                render={({ field }) => (
                  <Input
                    type="number"
                    value={field.value}
                    onChange={field.onChange}
                    placeholder="0.00"
                    className="w-full rounded-md font-medium"
                    min="0"
                    step="0.01"
                  />
                )}
              />
            </div>
          ))}
        </div>
      </div>

      {/* Model Routing — collapsible */}
      <div className="space-y-2">
        <button
          type="button"
          className="flex items-center gap-2 text-body-sm-medium text-primary"
          onClick={() => setModelRoutingExpanded((prev) => !prev)}
        >
          {modelRoutingExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
          Model Routing (advanced)
        </button>
        {modelRoutingExpanded && (
          <div className="flex flex-col gap-1">
            <p className="text-11 text-tertiary">Paste a JSON model routing config.</p>
            <Controller
              control={control}
              name="model_routing"
              render={({ field }) => (
                <textarea
                  value={field.value}
                  onChange={field.onChange}
                  rows={8}
                  placeholder='{"model_list": []}'
                  className="font-mono focus:ring-accent-primary w-full resize-y rounded-md border border-subtle bg-layer-transparent p-3 text-body-xs-regular text-primary placeholder:text-placeholder focus:ring-1 focus:outline-none"
                />
              )}
            />
          </div>
        )}
      </div>

      {/* Active toggle */}
      <div className="flex items-center gap-4">
        <div className="grow">
          <div className="text-body-sm-medium text-primary">Active</div>
          <div className="text-11 text-tertiary">Enable LiteLLM integration for all workspaces.</div>
        </div>
        <Controller
          control={control}
          name="is_active"
          render={({ field }) => <ToggleSwitch value={field.value} onChange={(val) => field.onChange(val)} size="sm" />}
        />
      </div>

      {/* Test connection result */}
      {testResult && (
        <div
          className={cn(
            "rounded-md border px-4 py-2 text-body-sm-regular",
            testResult.success
              ? "border-green-500/30 bg-green-500/10 text-green-600"
              : "border-red-500/30 bg-red-500/10 text-red-600"
          )}
        >
          {testResult.message}
        </div>
      )}

      {/* Actions */}
      <div className="flex items-center gap-4">
        <Button type="submit" variant="primary" size="lg" loading={isSubmitting} disabled={!isDirty && !notConfigured}>
          {isSubmitting ? "Saving…" : "Save"}
        </Button>
        <Button type="button" variant="secondary" size="lg" loading={isTesting} onClick={handleTestConnection}>
          {isTesting ? "Testing…" : "Test Connection"}
        </Button>
      </div>
    </form>
  );
}
