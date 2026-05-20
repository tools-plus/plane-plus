// IW PP-83: Global Skills page — God-mode admin AI Module.

import { useCallback, useEffect, useState } from "react";
import { useForm } from "react-hook-form";
import { Pencil, Plus, Trash2 } from "lucide-react";
import { Button } from "@plane/propel/button";
import { TOAST_TYPE, setToast } from "@plane/propel/toast";
import { Input, Loader, ToggleSwitch } from "@plane/ui";
import { IWAIModuleDrawer } from "../iw-ai-module-drawer";

// ---- Types ------------------------------------------------------------------

type TGlobalSkill = {
  slug: string;
  name: string;
  category: string;
  knowledge: string;
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

// ---- Drawer form ------------------------------------------------------------

function SkillDrawerForm({
  initial,
  onSave,
  onClose,
}: {
  initial: TGlobalSkill | null;
  onSave: (data: TGlobalSkill, isNew: boolean) => Promise<void>;
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
  } = useForm<TGlobalSkill>({
    defaultValues: initial ?? { slug: "", name: "", category: "", knowledge: "", is_active: true },
  });

  useEffect(() => {
    reset(initial ?? { slug: "", name: "", category: "", knowledge: "", is_active: true });
  }, [initial, reset]);

  const watchedName = watch("name");
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
        <Input {...register("name")} placeholder="Code Review" className="w-full rounded-md" />
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">Slug</span>
        <Input {...register("slug")} placeholder="code-review" className="font-mono w-full rounded-md" />
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">Category</span>
        <Input {...register("category")} placeholder="engineering" className="w-full rounded-md" />
      </div>
      <div className="flex flex-col gap-1">
        <span className="text-13 text-tertiary">Knowledge (injected into agent context)</span>
        <textarea
          {...register("knowledge")}
          rows={10}
          placeholder="# Code Review Guidelines&#10;…"
          className="focus:ring-accent-primary font-mono w-full resize-y rounded-md border border-subtle bg-layer-transparent p-3 text-body-xs-regular text-primary placeholder:text-placeholder focus:ring-1 focus:outline-none"
        />
      </div>
      <div className="flex items-center justify-between">
        <span className="text-body-sm-medium text-primary">Active</span>
        <ToggleSwitch value={watchedIsActive} onChange={(val) => setValue("is_active", val)} size="sm" />
      </div>
      <div className="flex gap-3 pt-2">
        <Button type="submit" variant="primary" size="base" loading={isSubmitting}>
          {isSubmitting ? "Saving…" : isNew ? "Create Skill" : "Save Changes"}
        </Button>
        <Button type="button" variant="secondary" size="base" onClick={onClose}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

// ---- Main component ---------------------------------------------------------

export function IWGlobalSkills() {
  const [skills, setSkills] = useState<TGlobalSkill[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [editingSkill, setEditingSkill] = useState<TGlobalSkill | null>(null);

  const loadData = useCallback(async () => {
    try {
      const data = await apiFetch<TGlobalSkill[]>("/skills/");
      setSkills(data);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to load skills." });
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadData();
  }, [loadData]);

  const handleDelete = async (slug: string) => {
    if (!window.confirm("Delete this skill?")) return;
    try {
      await apiFetch(`/skills/${slug}/`, { method: "DELETE" });
      setSkills((prev) => prev.filter((s) => s.slug !== slug));
      setToast({ type: TOAST_TYPE.SUCCESS, title: "Deleted", message: "Skill deleted." });
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to delete skill." });
    }
  };

  const handleSave = async (data: TGlobalSkill, isNew: boolean) => {
    try {
      if (isNew) {
        const created = await apiFetch<TGlobalSkill>("/skills/", {
          method: "POST",
          body: JSON.stringify(data),
        });
        setSkills((prev) => [...prev, created]);
        setToast({ type: TOAST_TYPE.SUCCESS, title: "Created", message: "Skill created." });
      } else {
        const updated = await apiFetch<TGlobalSkill>(`/skills/${data.slug}/`, {
          method: "PATCH",
          body: JSON.stringify(data),
        });
        setSkills((prev) => prev.map((s) => (s.slug === updated.slug ? updated : s)));
        setToast({ type: TOAST_TYPE.SUCCESS, title: "Saved", message: "Skill updated." });
      }
      setDrawerOpen(false);
    } catch {
      setToast({ type: TOAST_TYPE.ERROR, title: "Error", message: "Failed to save skill." });
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
            {skills.length} skill{skills.length !== 1 ? "s" : ""}
          </p>
          <Button
            variant="primary"
            size="sm"
            onClick={() => {
              setEditingSkill(null);
              setDrawerOpen(true);
            }}
          >
            <Plus className="mr-1 h-4 w-4" />
            New Skill
          </Button>
        </div>

        {skills.length === 0 ? (
          <div className="rounded-md border border-subtle px-6 py-10 text-center text-body-sm-regular text-secondary">
            No global skills configured yet.
          </div>
        ) : (
          <div className="overflow-x-auto rounded-md border border-subtle">
            <table className="w-full">
              <thead>
                <tr className="border-b border-subtle bg-layer-transparent-hover">
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Name</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Slug</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Category</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Status</th>
                  <th className="px-4 py-3 text-left text-caption-sm-medium text-secondary">Actions</th>
                </tr>
              </thead>
              <tbody>
                {skills.map((skill) => (
                  <tr key={skill.slug} className="border-b border-subtle hover:bg-layer-transparent-hover">
                    <td className="px-4 py-3 text-body-sm-medium text-primary">{skill.name}</td>
                    <td className="font-mono px-4 py-3 text-body-xs-regular text-secondary">{skill.slug}</td>
                    <td className="px-4 py-3 text-body-xs-regular text-secondary">{skill.category || "—"}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`inline-flex items-center rounded-full px-2 py-0.5 text-caption-sm-regular ${
                          skill.is_active
                            ? "bg-green-500/10 text-green-600"
                            : "bg-layer-transparent-hover text-secondary"
                        }`}
                      >
                        {skill.is_active ? "Active" : "Inactive"}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          className="rounded p-1 text-secondary hover:bg-layer-transparent-hover hover:text-primary"
                          onClick={() => {
                            setEditingSkill(skill);
                            setDrawerOpen(true);
                          }}
                          title="Edit"
                        >
                          <Pencil className="h-4 w-4" />
                        </button>
                        <button
                          type="button"
                          className="hover:bg-red-500/10 hover:text-red-600 rounded p-1 text-secondary"
                          onClick={() => handleDelete(skill.slug)}
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
        title={editingSkill ? "Edit Skill" : "New Skill"}
      >
        <SkillDrawerForm initial={editingSkill} onSave={handleSave} onClose={() => setDrawerOpen(false)} />
      </IWAIModuleDrawer>
    </>
  );
}
