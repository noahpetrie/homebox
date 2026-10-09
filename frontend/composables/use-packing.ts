// Home fork: "packing mode". Pick a location (usually a Box) and every barcode scanned after
// that, from the handheld scanner or the phone camera, moves the matching item into it.
// Barcodes Homebox doesn't know open the usual product lookup, and the new item is created
// in the box. The target survives page reloads in this tab (sessionStorage).
import { ref } from "vue";
import { useSessionStorage } from "@vueuse/core";
import { toast } from "@/components/ui/sonner";
import type { EntityFieldData, EntitySummary, EntityUpdate } from "~~/lib/api/types/data-contracts";
import type { UserClient } from "~~/lib/api/user";

export type PackTarget = { id: string; name: string };
export type PackedEntry = { id: string; name: string; moved: boolean };

export const packTarget = useSessionStorage<PackTarget | null>("homebox:pack.target", null, {
  serializer: { read: v => (v ? JSON.parse(v) : null), write: v => JSON.stringify(v) },
});
export const packedLog = useSessionStorage<PackedEntry[]>("homebox:pack.log", []);
// bumped after every move, so open pages (the box, Locations) can reload their lists
export const packVersion = ref(0);

export function startPacking(target: PackTarget) {
  packTarget.value = target;
  packedLog.value = [];
  // so items created from an unknown barcode land in the box too
  try {
    localStorage.setItem("homebox:create.lastLocationId", target.id);
  } catch {
    // storage unavailable
  }
}

export function stopPacking() {
  packTarget.value = null;
}

export async function findByCode(api: UserClient, code: string): Promise<EntitySummary[]> {
  const fieldName = /^97[89]\d{10}$/.test(code) ? "ISBN" : "Barcode";
  const [byField, bySearch] = await Promise.all([
    api.items.getAll({ fields: [`${fieldName}=${code}`], pageSize: 10 }),
    api.items.getAll({ q: code, pageSize: 10 }),
  ]);
  const seen = new Map<string, EntitySummary>();
  for (const it of [...(byField.data?.items ?? []), ...(bySearch.data?.items ?? [])]) seen.set(it.id, it);
  return [...seen.values()];
}

// Where a packed item came from is kept on the item itself, as a "Packed from" field holding
// a link to that location, so "Take out" can put it back there (on any device).
export const PACKED_FROM = "Packed from";
export type Place = { id: string; name: string };

export function parsePackedFrom(value: string | undefined | null): Place | null {
  const m = value?.match(/^\[(.*)\]\(\/location\/([0-9a-f-]{36})\)$/i);
  return m ? { name: m[1]!, id: m[2]! } : null;
}

/** Moves an item, recording where it came from (packedFrom) or clearing that record (null). */
export async function moveItem(api: UserClient, id: string, target: Place, packedFrom: Place | null) {
  const { data: item, error } = await api.items.get(id);
  if (error || !item) return { error: error ?? new Error("not found") };
  const fields = (item.fields || []).filter(f => f.name !== PACKED_FROM);
  if (packedFrom) {
    fields.push({
      id: null,
      name: PACKED_FROM,
      type: "text",
      textValue: `[${packedFrom.name}](/location/${packedFrom.id})`,
      numberValue: 0,
      booleanValue: false,
    } as unknown as EntityFieldData);
  }
  return await api.items.update(id, {
    ...item,
    parentId: target.id,
    tagIds: (item.tags || []).map(t => t.id),
    entityTypeId: item.entityType!.id,
    purchasePrice: item.purchasePrice || 0,
    soldPrice: item.soldPrice || 0,
    fields,
  } as unknown as EntityUpdate);
}

/**
 * Moves the item with this barcode into the pack target. Returns "unknown" when nothing in
 * Homebox has the code (the caller then starts the product lookup), otherwise "done".
 */
export async function packCode(api: UserClient, code: string): Promise<"done" | "unknown"> {
  const target = packTarget.value;
  if (!target) return "unknown";
  const found = (await findByCode(api, code)).filter(it => it.id !== target.id);
  if (!found.length) return "unknown";

  // with several copies, move one that isn't in the box yet
  const outside = found.filter(it => it.parent?.id !== target.id);
  if (!outside.length) {
    toast.info(`${found[0]!.name} is already in ${target.name}`);
    return "done";
  }
  if (outside.length > 1 && new Set(outside.map(it => it.name)).size > 1) {
    toast.warning(`${outside.length} different items match ${code}. Move one from its page.`);
    await navigateTo({ path: "/items", query: { q: code } });
    return "done";
  }
  const item = outside[0]!;
  const from = item.parent && item.parent.id !== target.id ? { id: item.parent.id, name: item.parent.name } : null;
  const { error } = await moveItem(api, item.id, target, from);
  if (error) {
    toast.error(`Couldn't move ${item.name}`);
    return "done";
  }
  packedLog.value = [{ id: item.id, name: item.name, moved: true }, ...packedLog.value];
  packVersion.value++;
  toast.success(`${item.name} → ${target.name}`);
  navigator.vibrate?.(40);
  return "done";
}
