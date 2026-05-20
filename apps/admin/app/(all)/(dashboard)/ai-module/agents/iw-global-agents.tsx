// IW PP-83: Global Agents page — God-mode admin AI Module.

import { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Input, Loader, ToggleSwitch } from "@plane/ui";
import { IWAIModuleDrawer } from "../iw-ai-module-drawer";

// ---- Types ------------------------------------------------------------------

type TGlobalAgent = {
  slug: string;
  name: string;
  instructions: string;
  model_pref: string; // matches the Django field name
  default_monthly_budget: string;
  is_active: boolean;
  skills: string[];
  tools: string[];
  mcp_connections: string[];
};

type TMultiSelectOption = { slug: string; name: string };

// ---- API helpers ------------------------------------------------------------

const API_BASE = "/api/god-mode/ai";

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!res.ok) throw new Error(`API error ${res.status}`);
  return res.json() as Promise<T>;
}

// ---- Sub-components ---------------------------------------------------------

function AgentRow({
  agent,
  onEdit,
  onDelete,
}: {
  agent: TGlobalAgent;
  onEdit: (a: TGlobalAgent) => void;
  onDelete: (slug: string) => void;
}) {
  return (
    <tr className="border-b border-subtle hover:bg-layer-transparent-hover">
      <td className="px-4 py-3 text-body-sm-medium text-primary">{agent.name}</td>
      <td className="font-mono px-4 py-3 text-body-xs-regular text-secondary">{agent.slug}</td>
      <td className="px-4 py-3 text-body-xs-regular text-secondary">{agent.model_pref || "—"}</td>
      <td className="px-4 py-3 text-body-xs-regular text-secondary">
        {agent.default_monthly_budget ? `$${agent.default_monthly_budget}` : "—"}
      </td>
      <td className="px-4 py-3">
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-caption-sm-regular ${
            agent.is_active ? "bg-green-500/10 text-green-600" : "bg-layer-transparent-hover text-secondary"
          }`}
        >
          {agent.is_active ? "Active" : "Inactive"}
        </span>
      </td>
      <td className="px-4 py-3">
        <div className="flex items-center gap-2">
          <button
            type="button"
            className="rounded p-1 text-secondary hover:bg-layer-transparent-hover hover:text-primary"
            onClick={() => onEdit(agent)}
            title="Edit"
          >
            <Pencil className="h-4 w-4" />
          </button>
          <button
            type="button"
            className="hover:bg-red-500/10 hover:text-red-600 rounded p-1 text-secondary"
            onClick={() => onDelete(agent.slug)}
            title="Delete"
          >
            <Trash2 className="h-4 w-4" />
          </button>
        </div>
      </td>
    </tr>
  );
}

// ---- Drawer form ------------------------------------------------------------

const AGENT_DEFAULTS: TAgentForm = {
  slug: "",
  name: "",
  instructions: "",
  model_pref: "",
  default_monthly_budget: "",
  is_active: true,
  skills: [],
  tools: [],
  mcp_connections: [],
};

async function testAgentModelCall(model: string): Promise<{ success: boolean; message: string }> {
  const res = await fetch("/api/god-mode/ai/litellm-config/test-model/", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(model ? { model } : {}),
  });
  const body = (await res.json().catch(() => ({}))) as { detail?: string; reply?: string; model?: string };
  if (!res.ok) return { success: false, message: body?.detail ?? "Model call failed" };
  return { success: true, message: `Model replied (${body.model ?? "unknown"}): "${body.reply}"` };
}

function AgentDrawerForm({
  initial,
  skills,
  tools,
  mcpConnections,
  onSave,
  onClose,
}: {
  initial: TGlobalAgent | null;
  skills: TMultiSelectOption[];
  tools: TMultiSelectOption[];
  mcpConnections: TMultiSelectOption[];
  onSave: (data: TAgentForm, isNew: boolean) => Promise<void>;
  onClose: () => void;
}) {
  const isNew = !initial;
  const [modelTestResult, setModelTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [isTestingModel, setIsTestingModel] = useState(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { isSubmitting },
  } = useForm<TAgentForm>({ defaultValues: initial ?? AGENT_DEFAULTS });

  useEffect(() => {
    reset(initial ?? AGENT_DEFAULTS);
    setModelTestResult(null);
  }, [initial, reset]);

  const watchedName = watch("name");
  const watchedIsActive = watch("is_active");
  const watchedSkills = watch("skills");
  const watchedTools = watch("tools");
  const watchedMcp = watch("mcp_connections");

  // Auto-slug from name (only when creating)
  useEffect(() => {
    if (isNew) {
      const slug = watchedName
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      setValue("slug", slug);
    }
  }, [watchedName, isNew, setValue]);

  const toggleMultiSelect = (field: "skills" | "tools" | "mcp_connections", slug: string) => {
    const current = watch(field);
    if (current.includes(slug)) {
      setValue(
        field,
        current.filter((s) => s !== slug)
      );
    } else {
      setValue(field, [...current, slug]);
    }
  };

  const onSubmit = async (data: TAgentForm) => {
    await onSave(data, isNew);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
      {/* Name */}
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">Name</span>
        <Input {...register("name")} placeholder="My Global Agent" className="w-full rounded-md" />
      </div>

      {/* Slug */}
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">Slug</span>
        <Input {...register("slug")} placeholder="my-global-agent" className="font-mono w-full rounded-md" />
      </div>

      {/* Instructions */}
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">Instructions (system prompt)</span>
        <textarea
          {...register("instructions")}
          rows={6}
          placeholder="You are a helpful assistant…"
          className="focus:ring-accent-primary w-full resize-y rounded-md border border-subtle bg-layer-transparent p-3 text-body-xs-regular text-primary placeholder:text-placeholder focus:ring-1 focus:outline-none"
        />
      </div>

      {/* Model preference */}
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">Model preference</span>
        <p className="text-11 text-tertiary">LiteLLM model string, e.g. anthropic/claude-sonnet-4-5, openrouter/…</p>
        <div className="flex gap-2">
          <Input {...register("model_pref")} placeholder="anthropic/claude-sonnet-4-5" className="w-full rounded-md" />
          <Button
            type="button"
            variant="secondary"
            size="base"
            loading={isTestingModel}
            onClick={async () => {
              const model = watch("model_pref");
              if (!model) return;
              setIsTestingModel(true);
              setModelTestResult(null);
              try {
                const result = await testAgentModelCall(model);
                setModelTestResult(result);
              } finally {
                setIsTestingModel(false);
              }
            }}
          >
            {isTestingModel ? "Testing…" : "Test"}
          </Button>
        </div>
        {modelTestResult && (
          <p className={`mt-1 text-11 ${modelTestResult.success ? "text-green-600" : "text-red-600"}`}>
            {modelTestResult.message}
          </p>
        )}
      </div>

      {/* Budget */}
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">Default monthly budget ($)</span>
        <Input
          type="number"
          {...register("default_monthly_budget")}
          placeholder="10.00"
          min="0"
          step="0.01"
          className="w-full rounded-md"
        />
      </div>

      {/* Active */}
      <div className="flex items-center justify-between">
        <span className="text-body-sm-medium text-primary">Active</span>
        <ToggleSwitch value={watchedIsActive} onChange={(val) => setValue("is_active", val)} size="sm" />
      </div>

      {/* Skills multi-select */}
      {skills.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-13 text-tertiary">Skills</span>
          <div className="flex flex-wrap gap-2">
            {skills.map((s) => (
              <button
                type="button"
                key={s.slug}
                className={`rounded-full border px-3 py-1 text-caption-sm-regular transition-colors ${
                  watchedSkills.includes(s.slug)
                    ? "border-accent-primary bg-accent-subtle text-accent-primary"
                    : "hover:border-accent-primary border-subtle text-secondary"
                }`}
                onClick={() => toggleMultiSelect("skills", s.slug)}
              >
                {s.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Tools multi-select */}
      {tools.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-13 text-tertiary">Tools</span>
          <div className="flex flex-wrap gap-2">
            {tools.map((t) => (
              <button
                type="button"
                key={t.slug}
                className={`rounded-full border px-3 py-1 text-caption-sm-regular transition-colors ${
                  watchedTools.includes(t.slug)
                    ? "border-accent-primary bg-accent-subtle text-accent-primary"
                    : "hover:border-accent-primary border-subtle text-secondary"
                }`}
                onClick={() => toggleMultiSelect("tools", t.slug)}
              >
                {t.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* MCP Connections multi-select */}
      {mcpConnections.length > 0 && (
        <div className="flex flex-col gap-2">
          <span className="text-13 text-tertiary">MCP Connections</span>
          <div className="flex flex-wrap gap-2">
            {mcpConnections.map((m) => (
              <button
                type="button"
                key={m.slug}
                className={`rounded-full border px-3 py-1 text-caption-sm-regular transition-colors ${
                  watchedMcp.includes(m.slug)
                    ? "border-accent-primary bg-accent-subtle text-accent-primary"
                    : "hover:border-accent-primary border-subtle text-secondary"
                }`}
                onClick={() => toggleMultiSelect("mcp_connections", m.slug)}
              >
                {m.name}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Actions */}
      <div className="flex gap-3 pt-2">
        <Button type="submit" variant="primary" size="base" loading={isSubmitting}>
          {isSubmitting ? "Saving…" : isNew ? "Create Agent" : "Save Changes"}
        </Button>
        <Button type="button" variant="secondary" size="base" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

// ---- Main component ---------------------------------------------------------

export function IWGlobalAgents() {
  const [agents, setAgents] = useState<TGlobalAgent[]>([]);
  const [skills, setSkills] = useState<TMultiSelectOption[]>([]);
  const [tools, setTools] = useState<TMultiSelectOption[]>([]);
  const [mcpConnections, setMcpConnections] = useState<TMultiSelectOption[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<TGlobalAgent | null>(null);

  const loadData = useCallback(async () => {
    try {
      const [agentsData, skillsData, toolsData, mcpData] = await Promise.all([
        apiFetch<TGlobalAgent[]>("/agents/"),
        apiFetch<TMultiSelectOption[]>("/skills/").catch(() => []),
        apiFetch<TMultiSelectOption[]>("/tools/").catch(() => []),
        apiFetch<TMultiSelectOption[]>("/mcps/").catch(() => []),
      ]);
      setAgents(agentsData);
      setSkills(skillsData);
      setTools(toolsData);
      setMcpConnections(mcpData);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to load agents." });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleOpenCreate = () => {
    setEditingAgent(null);
    setDrawerOpen(true);
  };

  const handleOpenEdit = (agent: TGlobalAgent) => {
    setEditingAgent(agent);
    setDrawerOpen(true);
  };

  const handleDelete = async (slug: string) => {
    if (!window.confirm("Delete this agent?")) return;
    try {
      await apiFetch(`/agents/${slug}/`, { method: "DELETE" });
      setAgents((prev) => prev.filter((a) => a.slug !== slug));
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Deleted", message: "Agent deleted." });
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to delete agent." });
    }
  };

  const handleSave = async (data: TAgentForm, isNew: boolean) => {
    try {
      if (isNew) {
        const created = await apiFetch<TGlobalAgent>("/agents/", {
          method: "POST",
          body: JSON.stringify(data),
        });
        setAgents((prev) => [...prev, created]);
        setToast({ type: TOAST_TYPE.SUCCESS, title: "Created", message: "Agent created." });
      } else {
        const updated = await apiFetch<TGlobalAgent>(`/agents/${data.slug}/`, {
          method: "PATCH",
          body: JSON.stringify(data),
        });
        setAgents((prev) => prev.map((a) => (a.slug === updated.slug ? updated : a)));
        setToast({ type: TOAST_TYPE.SUCCESS, title: "Saved", message: "Agent updated." });
      }
      setDrawerOpen(false);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to save agent." });
    }
  };

  if (isLoading) {
    return (
      <Loader className="space-y-4">
        <Loader.Item height="40px" width="100%" />
        <Loader.Item height="40px" width="100%" />
        <Loader.Item height="40px" width="100%" />
      </Loader>
    );
  }

  return (
    <>
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <p className="text-body-sm-regular text-secondary">
            {agents.length} global agent{agents.length !== 1 ? "s" : ""}
          </p>
          <Button variant="primary" size="sm" onClick={handleOpenCreate}>
            <Plus className="mr-1 h-4 w-4" />
            New Agent
          </Button>
        </div>

        {agents.length === 0 ? (
          <div className="rounded-md border border-subtle px-6 py-10 text-center text-body-sm-regular text-secondary">
            No global agents configured yet.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-md border border-subtle">
            <table className="w-full">
              <thead>
                <tr className="border-b border-subtle bg-layer-transparent-hover">
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Name</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Slug</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Model</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Budget</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Status</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Actions</th>
                </tr>
              </thead>
              <tbody>
                {agents.map((agent) => (
                  <AgentRow key={agent.slug} agent={agent} onEdit={handleOpenEdit} onDelete={handleDelete} />
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <IWAIModuleDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editingAgent ? "Edit Agent" : "New Agent"}
      >
        <AgentDrawerForm
          initial={editingAgent}
          skills={skills}
          tools={tools}
          mcpConnections={mcpConnections}
          onSave={handleSave}
          onClose={() => setDrawerOpen(false)}
        />
      </IWAIModuleDrawer>
    </>
  );
}
