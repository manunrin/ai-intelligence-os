"use client";

import { useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { AppShell } from "@/components/layout/AppShell";
import { KnowledgePage } from "@/components/panels/KnowledgePage";
import { useKnowledgeItems } from "@/hooks/useKnowledge";
import { useDeleteKnowledge } from "@/hooks/useDelete";
import { useToast } from "@/lib/toast";
import { queryClient } from "@/lib/query-client";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import type { KnowledgeItem } from "@/types";
import { KnowledgeFormBody } from "@/components/knowledge/KnowledgeForm";
import { useState } from "react";

export default function KnowledgeRoute() {
  const router = useRouter();
  const pathname = usePathname();
  const { isAuthenticated, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace(`/login?callbackUrl=${encodeURIComponent(pathname)}`);
    }
  }, [isAuthenticated, isLoading, router, pathname]);

  if (isLoading || !isAuthenticated) {
    return null;
  }

  const { toast } = useToast();
  const { data: items = [], isLoading: loading } = useKnowledgeItems();
  const deleteMutation = useDeleteKnowledge();

  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [editingItem, setEditingItem] = useState<KnowledgeItem | null>(null);
  const [formError, setFormError] = useState<string | null>(null);

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await deleteMutation.mutateAsync(deleteConfirm);
      toast("Knowledge item deleted", "success");
    } catch (err) {
      toast(err instanceof Error ? err.message : "Delete failed", "error");
    } finally {
      setDeleteConfirm(null);
    }
  };

  return (
    <AppShell>
      <KnowledgePage
        items={items}
        onNew={() => { setEditingItem(null); setFormOpen(true); }}
        onEdit={(item) => { setEditingItem(item); setFormOpen(true); }}
        onDelete={(id) => setDeleteConfirm(id)}
      />

      {/* Create/Edit Modal */}
      <Modal
        open={formOpen}
        onClose={() => { setFormOpen(false); setEditingItem(null); }}
        title={editingItem ? "Edit Knowledge Item" : "New Knowledge Item"}
        footer={<Button variant="outline" onClick={() => { setFormOpen(false); setEditingItem(null); }}>Cancel</Button>}
      >
        <KnowledgeFormBody
          onSubmit={() => {
            setFormOpen(false);
            setEditingItem(null);
            queryClient.invalidateQueries({ queryKey: [["knowledge"]] });
          }}
          initialData={editingItem}
          error={formError}
          onError={setFormError}
        />
      </Modal>

      {/* Delete Confirmation */}
      <Modal open={!!deleteConfirm} onClose={() => setDeleteConfirm(null)} title="Delete knowledge item?"
        footer={
          <>
            <Button variant="outline" onClick={() => setDeleteConfirm(null)}>Cancel</Button>
            <Button variant="destructive" onClick={handleDelete}>Delete</Button>
          </>
        }
      >
        <p className="text-sm text-slate-600 dark:text-slate-300">Are you sure you want to delete this knowledge item? This action cannot be undone.</p>
      </Modal>
    </AppShell>
  );
}
