// IW PP-83: Global Tools page — God-mode admin AI Module.
// Built-in tools are read-only. Custom tools support full CRUD.

import { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Input, Loader, ToggleSwitch } from "@plane/ui";
import { IWAIModuleDrawer } from "../iw-ai-module-drawer";

// ---- Types ------------------------------------------------------------------

type TToolImplementationType = "builtin" | "custom";

type TGlobalTool = {
  slug: string;
  name: string;
  description: string;
  implementation_type: TToolImplementationType;
  input_schema: string; // JSON string
  is_destructive: boolean;
  is_active: boolean;
};

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

// ---- Drawer form (custom tools only) ----------------------------------------

function ToolDrawerForm({
  initial,
  onSave,
  onClose,
}: {
  initial: TGlobalTool | null;
  onSave: (data: TGlobalTool, isNew: boolean) => Promise<void>;
  onClose: () => void;
}) {
  const isNew = !initial;
  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { isSubmitting },
  } = useForm<TGlobalTool>({
    defaultValues: initial ?? {
      slug: "",
      name: "",
      description: "",
      implementation_type: "custom",
      input_schema: "",
      is_destructive: false,
      is_active: true,
    },
  });

  useEffect(() => {
    reset(
      initial ?? {
        slug: "",
        name: "",
        description: "",
        implementation_type: "custom",
        input_schema: "",
        is_destructive: false,
        is_active: true,
      }
    );
  }, [initial, reset]);

  const watchedName = watch("name");
  const watchedIsDestructive = watch("is_destructive");
  const watchedIsActive = watch("is_active");

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
        <span className="text-13 text-tertiary">Name</span>
        <Input {...register("name")} placeholder="Send Email" className="w-full rounded-md" />
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">Slug</span>
        <Input {...register("slug")} placeholder="send-email" className="font-mono w-full rounded-md" />
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">Description</span>
        <Input {...register("description")} placeholder="Send an email to a recipient." className="w-full rounded-md" />
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">Input Schema (JSON)</span>
        <textarea
          {...register("input_schema")}
          rows={8}
          placeholder='{"type":"object","properties":{"to":{"type":"string"}}}'
          className="focus:ring-accent-primary font-mono w-full resize-y rounded-md border border-subtle bg-layer-transparent p-3 text-body-xs-regular text-primary placeholder:text-placeholder focus:ring-1 focus:outline-none"
        />
      </div>
      <div className="flex items-center justify-between">
        <div>
          <div className="text-body-sm-medium text-primary">Destructive</div>
          <div className="text-11 text-tertiary">Mark if this tool can cause data loss.</div>
        </div>
        <ToggleSwitch value={watchedIsDestructive} onChange={(val) => setValue("is_destructive", val)} size="sm" />
      </div>
      <div className="flex items-center justify-between">
        <span className="text-body-sm-medium text-primary">Active</span>
        <ToggleSwitch value={watchedIsActive} onChange={(val) => setValue("is_active", val)} size="sm" />
      </div>
      <div className="flex gap-3 pt-2">
        <Button type="submit" variant="primary" size="base" loading={isSubmitting}>
          {isSubmitting ? "Saving…" : isNew ? "Create Tool" : "Save Changes"}
        </Button>
        <Button type="button" variant="secondary" size="base" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

// ---- Main component ---------------------------------------------------------

export function IWGlobalTools() {
  const [tools, setTools] = useState<TGlobalTool[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingTool, setEditingTool] = useState<TGlobalTool | null>(null);

  const loadData = useCallback(async () => {
    try {
      const data = await apiFetch<TGlobalTool[]>("/tools/");
      setTools(data);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to load tools." });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleDelete = async (slug: string) => {
    if (!window.confirm("Delete this tool?")) return;
    try {
      await apiFetch(`/tools/${slug}/`, { method: "DELETE" });
      setTools((prev) => prev.filter((t) => t.slug !== slug));
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Deleted", message: "Tool deleted." });
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to delete tool." });
    }
  };

  const handleSave = async (data: TGlobalTool, isNew: boolean) => {
    try {
      if (isNew) {
        const created = await apiFetch<TGlobalTool>("/tools/", {
          method: "POST",
          body: JSON.stringify(data),
        });
        setTools((prev) => [...prev, created]);
        setToast({ type: TOAST_TYPE.SUCCESS, title: "Created", message: "Tool created." });
      } else {
        const updated = await apiFetch<TGlobalTool>(`/tools/${data.slug}/`, {
          method: "PATCH",
          body: JSON.stringify(data),
        });
        setTools((prev) => prev.map((t) => (t.slug === updated.slug ? updated : t)));
        setToast({ type: TOAST_TYPE.SUCCESS, title: "Saved", message: "Tool updated." });
      }
      setDrawerOpen(false);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to save tool." });
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
            {tools.length} tool{tools.length !== 1 ? "s" : ""}
          </p>
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              setEditingTool(null);
              setDrawerOpen(true);
            }}
          >
            <Plus className="mr-1 h-4 w-4" />
            New Tool
          </Button>
        </div>

        {tools.length === 0 ? (
          <div className="rounded-md border border-subtle px-6 py-10 text-center text-body-sm-regular text-secondary">
            No tools configured yet.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-md border border-subtle">
            <table className="w-full">
              <thead>
                <tr className="border-b border-subtle bg-layer-transparent-hover">
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Name</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Slug</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Type</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Destructive</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Status</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Actions</th>
                </tr>
              </thead>
              <tbody>
                {tools.map((tool) => {
                  const isBuiltin = tool.implementation_type === "builtin";
                  return (
                    <tr key={tool.slug} className="border-b border-subtle hover:bg-layer-transparent-hover">
                      <td className="px-4 py-3 text-body-sm-medium text-primary">{tool.name}</td>
                      <td className="font-mono px-4 py-3 text-body-xs-regular text-secondary">{tool.slug}</td>
                      <td className="px-4 py-3">
                        {isBuiltin ? (
                          <span className="inline-flex items-center rounded-full bg-accent-subtle px-2 py-0.5 text-caption-sm-regular text-accent-primary">
                            Built-in
                          </span>
                        ) : (
                          <span className="text-body-xs-regular text-secondary">Custom</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        {tool.is_destructive ? (
                          <span className="bg-red-500/10 text-red-600 inline-flex items-center rounded-full px-2 py-0.5 text-caption-sm-regular">
                            Yes
                          </span>
                        ) : (
                          <span className="text-body-xs-regular text-secondary">No</span>
                        )}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`inline-flex items-center rounded-full px-2 py-0.5 text-caption-sm-regular ${
                            tool.is_active
                              ? "bg-green-500/10 text-green-600"
                              : "bg-layer-transparent-hover text-secondary"
                          }`}
                        >
                          {tool.is_active ? "Active" : "Inactive"}
                        </span>
                      </td>
                      <td className="px-4 py-3">
                        {isBuiltin ? (
                          <span className="text-caption-sm-regular text-placeholder">Read-only</span>
                        ) : (
                          <div className="flex items-center gap-2">
                            <button
                              type="button"
                              className="rounded p-1 text-secondary hover:bg-layer-transparent-hover hover:text-primary"
                              onClick={() => {
                                setEditingTool(tool);
                                setDrawerOpen(true);
                              }}
                              title="Edit"
                            >
                              <Pencil className="h-4 w-4" />
                            </button>
                            <button
                              type="button"
                              className="hover:bg-red-500/10 hover:text-red-600 rounded p-1 text-secondary"
                              onClick={() => handleDelete(tool.slug)}
                              title="Delete"
                            >
                              <Trash2 className="h-4 w-4" />
                            </button>
                          </div>
                        )}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>

      <IWAIModuleDrawer
        isOpen={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        title={editingTool ? "Edit Tool" : "New Tool"}
      >
        <ToolDrawerForm initial={editingTool} onSave={handleSave} onClose={() => setDrawerOpen(false)} />
      </IWAIModuleDrawer>
    </>
  );
}
