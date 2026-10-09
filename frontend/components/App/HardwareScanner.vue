<script setup lang="ts">
  // Home fork: support for a handheld Bluetooth/USB barcode scanner. These pair as a keyboard
  // and "type" the code followed by Enter, much faster than a person types. When such a burst
  // arrives while no text field has focus, look the code up: open the item if we already have
  // it, otherwise start the same product lookup the camera scanner uses. With a text field
  // focused the scanner just types into it as usual (handy for search or the Barcode field).
  import { toast } from "@/components/ui/sonner";
  import { DialogID, useDialog } from "~/components/ui/dialog-provider/utils";
  import type { EntitySummary } from "~~/lib/api/types/data-contracts";

  const api = useUserApi();
  const { activeDialog, openDialog, closeDialog } = useDialog();

  const MAX_GAP_MS = 80; // scanners send a key every few ms; people are far slower
  const MIN_LENGTH = 6;

  let buffer = "";
  let lastKeyAt = 0;
  let busy = false;

  function isEditable(el: Element | null): boolean {
    if (!el) return false;
    const tag = el.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (el as HTMLElement).isContentEditable;
  }

  function onKeydown(e: KeyboardEvent) {
    if (e.ctrlKey || e.metaKey || e.altKey) return;
    const now = performance.now();
    if (now - lastKeyAt > MAX_GAP_MS) buffer = "";
    lastKeyAt = now;

    if (e.key === "Enter") {
      const code = buffer.trim();
      buffer = "";
      if (code.length < MIN_LENGTH || isEditable(document.activeElement)) return;
      // Leave other dialogs alone; the camera scanner is replaced by the handheld one.
      if (activeDialog.value && activeDialog.value !== DialogID.Scanner) return;
      e.preventDefault();
      handleScan(code);
      return;
    }
    if (e.key.length === 1) buffer += e.key;
  }

  async function findExisting(code: string): Promise<EntitySummary[]> {
    const fieldName = /^97[89]\d{10}$/.test(code) ? "ISBN" : "Barcode";
    const [byField, bySearch] = await Promise.all([
      api.items.getAll({ fields: [`${fieldName}=${code}`], pageSize: 10 }),
      api.items.getAll({ q: code, pageSize: 10 }),
    ]);
    const seen = new Map<string, EntitySummary>();
    for (const it of [...(byField.data?.items ?? []), ...(bySearch.data?.items ?? [])]) seen.set(it.id, it);
    return [...seen.values()];
  }

  async function handleScan(code: string) {
    if (busy) return;
    busy = true;
    try {
      if (activeDialog.value === DialogID.Scanner) closeDialog(DialogID.Scanner);

      // Homebox label QR codes hold a link to the item or location.
      if (/^https?:\/\//i.test(code)) {
        const path = new URL(code).pathname.replace(/[^a-zA-Z0-9-_/]/g, "");
        await navigateTo(path);
        return;
      }

      const found = await findExisting(code);
      if (found.length === 1) {
        toast.success(`Scanned: ${found[0]!.name}`);
        await navigateTo(`/item/${found[0]!.id}`);
      } else if (found.length > 1) {
        toast.info(`${found.length} items match ${code}`);
        await navigateTo({ path: "/items", query: { q: code } });
      } else {
        openDialog(DialogID.ProductImport, { params: { barcode: code } });
      }
    } catch (err) {
      console.error(err);
      toast.error(`Couldn't look up ${code}`);
    } finally {
      busy = false;
    }
  }

  onMounted(() => window.addEventListener("keydown", onKeydown, true));
  onBeforeUnmount(() => window.removeEventListener("keydown", onKeydown, true));
</script>

<template>
  <span class="hidden" />
</template>
