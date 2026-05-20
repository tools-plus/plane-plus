// IW PP-83: Global MCP Connections page — God-mode admin AI Module.

import { useCallback, useEffect, useState } from "react";
import { useForm, Controller } from "react-hook-form";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Input, Loader, ToggleSwitch } from "@plane/ui";
import { CustomSelect } from "@plane/ui";
import { IWAIModuleDrawer } from "../iw-ai-module-drawer";

// ---- Types ------------------------------------------------------------------

type TAuthType = "none" | "api_key" | "oauth";

type TMCPConnection = {
  slug: string;
  name: string;
  server_url: string;
  auth_type: TAuthType;
  auth_config: string; // JSON string, masked on display
  env_vars: string; // JSON key-value string, masked values
  is_active: boolean;
};

const AUTH_TYPE_OPTIONS: { value: TAuthType; label: string }[] = [
  { value: "none", label: "None" },
  { value: "api_key", label: "API Key" },
  { value: "oauth", label: "OAuth" },
];

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

// ---- Drawer form ------------------------------------------------------------

function MCPConnectionDrawerForm({
  initial,
  onSave,
  onClose,
}: {
  initial: TMCPConnection | null;
  onSave: (data: TMCPConnection, isNew: boolean) => Promise<void>;
  onClose: () => void;
}) {
  const isNew = !initial;
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    control,
    formState: { isSubmitting, errors },
  } = useForm<TMCPConnection>({
    defaultValues: initial ?? {
      slug: "",
      name: "",
      server_url: "",
      auth_type: "none",
      auth_config: "",
      env_vars: "",
      is_active: true,
    },
  });

  useEffect(() => {
    reset(
      initial ?? {
        slug: "",
        name: "",
        server_url: "",
        auth_type: "none",
        auth_config: "",
        env_vars: "",
        is_active: true,
      }
    );
  }, [initial, reset]);

  const watchedName = watch("name");
  const watchedIsActive = watch("is_active");
  const watchedAuthType = watch("auth_type");

  useEffect(() => {
    if (isNew) {
      const slug = watchedName
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "-")
        .replace(/^-|-$/g, "");
      setValue("slug", slug);
    }
  }, [watchedName, isNew, setValue]);

  return (
    <form onSubmit={handleSubmit((data) => onSave(data, isNew))} className="space-y-6">
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">
          Name <span className="text-red-500">*</span>
        </span>
        <Input
          {...register("name", { required: "Name is required." })}
          placeholder="GitHub MCP"
          className={`w-full rounded-md ${errors.name ? "border-red-500" : ""}`}
        />
        {errors.name && <p className="text-red-500 text-11">{errors.name.message}</p>}
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">
          Slug <span className="text-red-500">*</span>
        </span>
        <Input
          {...register("slug", { required: "Slug is required." })}
          placeholder="github-mcp"
          className={`font-mono w-full rounded-md ${errors.slug ? "border-red-500" : ""}`}
        />
        {errors.slug && <p className="text-red-500 text-11">{errors.slug.message}</p>}
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">
          Server URL <span className="text-red-500">*</span>
        </span>
        <Input
          {...register("server_url", { required: "Server URL is required." })}
          placeholder="https://mcp.example.com/sse"
          className={`w-full rounded-md ${errors.server_url ? "border-red-500" : ""}`}
        />
        {errors.server_url && <p className="text-red-500 text-11">{errors.server_url.message}</p>}
      </div>

      {/* Auth type */}
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">Auth Type</span>
        <Controller
          control={control}
          name="auth_type"
          render={({ field }) => (
            <CustomSelect
              value={field.value}
              label={AUTH_TYPE_OPTIONS.find((o) => o.value === watchedAuthType)?.label ?? "None"}
              onChange={(val: TAuthType) => field.onChange(val)}
              buttonClassName="rounded-md border-subtle"
              input
            >
              {AUTH_TYPE_OPTIONS.map((o) => (
                <CustomSelect.Option key={o.value} value={o.value} className="w-full">
                  {o.label}
                </CustomSelect.Option>
              ))}
            </CustomSelect>
          )}
        />
      </div>

      {/* Auth config — only shown if auth_type != none */}
      {watchedAuthType !== "none" && (
        <div className="flex flex-col gap-1">
          <span className="text-13 text-tertiary">Auth Config (JSON)</span>
          <p className="text-11 text-tertiary">Values are masked in display.</p>
          <textarea
            {...register("auth_config")}
            rows={5}
            placeholder='{"api_key": "sk-••••••••"}'
            className="focus:ring-accent-primary font-mono w-full resize-y rounded-md border border-subtle bg-layer-transparent p-3 text-body-xs-regular text-primary placeholder:text-placeholder focus:ring-1 focus:outline-none"
          />
        </div>
      )}

      {/* Env vars */}
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">Env Vars (JSON key-value, masked values)</span>
        <textarea
          {...register("env_vars")}
          rows={4}
          placeholder='{"MY_SECRET": "••••••••"}'
          className="focus:ring-accent-primary font-mono w-full resize-y rounded-md border border-subtle bg-layer-transparent p-3 text-body-xs-regular text-primary placeholder:text-placeholder focus:ring-1 focus:outline-none"
        />
      </div>

      <div className="flex items-center justify-between">
        <span className="text-body-sm-medium text-primary">Active</span>
        <ToggleSwitch value={watchedIsActive} onChange={(val) => setValue("is_active", val)} size="sm" />
      </div>

      <div className="flex gap-3 pt-2">
        <Button type="submit" variant="primary" size="base" loading={isSubmitting}>
          {isSubmitting ? "Saving…" : isNew ? "Create Connection" : "Save Changes"}
        </Button>
        <Button type="button" variant="secondary" size="base" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

// ---- Main component ---------------------------------------------------------

export function IWGlobalMCPConnections() {
  const [connections, setConnections] = useState<TMCPConnection[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingConnection, setEditingConnection] = useState<TMCPConnection | null>(null);

  const loadData = useCallback(async () => {
    try {
      const data = await apiFetch<TMCPConnection[]>("/mcps/");
      setConnections(data);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to load MCP connections." });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleDelete = async (slug: string) => {
    if (!window.confirm("Delete this MCP connection?")) return;
    try {
      await apiFetch(`/mcps/${slug}/`, { method: "DELETE" });
      setConnections((prev) => prev.filter((c) => c.slug !== slug));
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Deleted", message: "MCP connection deleted." });
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to delete MCP connection." });
    }
  };

  const handleSave = async (data: TMCPConnection, isNew: boolean) => {
    try {
      if (isNew) {
        const created = await apiFetch<TMCPConnection>("/mcps/", {
          method: "POST",
          body: JSON.stringify(data),
        });
        setConnections((prev) => [...prev, created]);
        setToast({ type: TOAST_TYPE.SUCCESS, title: "Created", message: "MCP connection created." });
      } else {
        const updated = await apiFetch<TMCPConnection>(`/mcps/${data.slug}/`, {
          method: "PATCH",
          body: JSON.stringify(data),
        });
        setConnections((prev) => prev.map((c) => (c.slug === updated.slug ? updated : c)));
        setToast({ type: TOAST_TYPE.SUCCESS, title: "Saved", message: "MCP connection updated." });
      }
      setDrawerOpen(false);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to save MCP connection." });
    }
  };

  if (isLoading) {
    return (
      <Loader className="space-y-4">
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
            {connections.length} connection{connections.length !== 1 ? "s" : ""}
          </p>
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              setEditingConnection(null);
              setDrawerOpen(true);
            }}
          >
            <Plus className="mr-1 h-4 w-4" />
            New Connection
          </Button>
        </div>

        {connections.length === 0 ? (
          <div className="rounded-md border border-subtle px-6 py-10 text-center text-body-sm-regular text-secondary">
            No MCP connections configured yet.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-md border border-subtle">
            <table className="w-full">
              <thead>
                <tr className="border-b border-subtle bg-layer-transparent-hover">
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Name</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Slug</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">URL</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Auth Type</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Status</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Actions</th>
                </tr>
              </thead>
              <tbody>
                {connections.map((conn) => (
                  <tr key={conn.slug} className="border-b border-subtle hover:bg-layer-transparent-hover">
                    <td className="px-4 py-3 text-body-sm-medium text-primary">{conn.name}</td>
                    <td className="font-mono px-4 py-3 text-body-xs-regular text-secondary">{conn.slug}</td>
                    <td className="max-w-xs truncate px-4 py-3 text-body-xs-regular text-secondary">
                      {conn.server_url}
                    </td>
                    <td className="px-4 py-3 text-body-xs-regular text-secondary capitalize">
                      {conn.auth_type.replace("_", " ")}
                    </td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-caption-sm-regular ${
                          conn.is_active
                            ? "bg-green-500/10 text-green-600"
                            : "bg-layer-transparent-hover text-secondary"
                        }`}
                      >
                        {conn.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          className="rounded p-1 text-secondary hover:bg-layer-transparent-hover hover:text-primary"
                          onClick={() => {
                            setEditingConnection(conn);
                            setDrawerOpen(true);
                          }}
                          title="Edit"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          className="hover:bg-red-500/10 hover:text-red-600 rounded p-1 text-secondary"
                          onClick={() => handleDelete(conn.slug)}
                          title="Delete"
                        >
                          <Trash2 className="h-4 w-4" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <IWAIModuleDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editingConnection ? "Edit MCP Connection" : "New MCP Connection"}
      >
        <MCPConnectionDrawerForm initial={editingConnection} onSave={handleSave} onClose={() => setDrawerOpen(false)} />
      </IWAIModuleDrawer>
    </>
  );
}
