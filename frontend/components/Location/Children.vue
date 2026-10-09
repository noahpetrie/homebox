<script setup lang="ts">
  // Home fork: a location's sub-locations as full-width rows, top to bottom (like the drawers of
  // a unit). Each row shows how many things are in it, counting nested compartments, thumbnails
  // of them, and its own sub-locations as chips. Empty rows collapse to one line.
  import type { EntitySummary, TreeItem } from "~~/lib/api/types/data-contracts";
  import { Badge } from "@/components/ui/badge";
  import { Button } from "@/components/ui/button";
  import { packTarget, packVersion, startPacking } from "~/composables/use-packing";
  import MdiPackageVariant from "~icons/mdi/package-variant";
  import MdiPackageVariantClosed from "~icons/mdi/package-variant-closed";
  import MdiChevronRight from "~icons/mdi/chevron-right";

  const props = defineProps<{ parentId: string; areas: EntitySummary[] }>();

  const api = useUserApi();

  type Row = {
    id: string;
    name: string;
    description: string;
    total: number;
    items: EntitySummary[];
    subs: { id: string; name: string; total: number }[];
  };
  const rows = ref<Row[]>([]);

  function findNode(nodes: TreeItem[], id: string): TreeItem | null {
    for (const n of nodes) {
      if (n.id === id) return n;
      const hit = findNode(n.children ?? [], id);
      if (hit) return hit;
    }
    return null;
  }
  const descendants = (n: TreeItem): string[] => [n.id, ...(n.children ?? []).flatMap(descendants)];

  async function load() {
    const { data: tree } = await api.items.getTree();
    const parent = tree ? findNode(tree, props.parentId) : null;
    const out = await Promise.all(
      props.areas.map(async a => {
        const node = parent?.children?.find(c => c.id === a.id);
        const ids = node ? descendants(node) : [a.id];
        const { data } = await api.items.getAll({ parentIds: ids, pageSize: 100 });
        const items = data?.items ?? [];
        const subs = (node?.children ?? []).map(c => {
          const inside = new Set(descendants(c));
          return { id: c.id, name: c.name, total: items.filter(i => i.parent && inside.has(i.parent.id)).length };
        });
        return {
          id: a.id,
          name: a.name,
          description: a.description ?? "",
          total: data?.total ?? items.length,
          items,
          subs,
        };
      })
    );
    // natural order, so Drawer 2 comes before Drawer 10
    rows.value = out.sort((p, q) => p.name.localeCompare(q.name, undefined, { numeric: true }));
  }

  watch(() => props.areas.map(a => a.id).join(), load, { immediate: true });
  watch(packVersion, load);

  const thumb = (it: EntitySummary) =>
    it.imageId ? api.authURL(`/entities/${it.id}/attachments/${it.thumbnailId || it.imageId}`) : "";
</script>

<template>
  <section class="mt-6">
    <div class="flex flex-col gap-2">
      <div
        v-for="r in rows"
        :key="r.id"
        class="group rounded-lg border bg-card shadow-sm transition-colors hover:border-primary/50"
      >
        <!-- empty: one line -->
        <div v-if="!r.total" class="flex items-center gap-3 px-4 py-2.5">
          <NuxtLink :to="`/location/${r.id}`" class="font-semibold hover:underline">{{ r.name }}</NuxtLink>
          <span class="grow text-sm text-muted-foreground">· Empty</span>
          <Button
            v-if="packTarget?.id !== r.id"
            size="sm"
            variant="link"
            class="h-auto p-0 text-xs"
            @click="startPacking({ id: r.id, name: r.name })"
          >
            <MdiPackageVariantClosed class="mr-1 size-3.5" /> Pack here
          </Button>
          <NuxtLink :to="`/location/${r.id}`" :aria-label="`Open ${r.name}`">
            <MdiChevronRight class="size-5 opacity-40 group-hover:opacity-80" />
          </NuxtLink>
        </div>

        <!-- with contents -->
        <NuxtLink v-else :to="`/location/${r.id}`" class="block px-4 py-3">
          <div class="flex items-center gap-2">
            <span class="font-semibold">{{ r.name }}</span>
            <Badge>{{ r.total }}</Badge>
            <span v-if="r.description" class="hidden truncate text-sm text-muted-foreground sm:inline">
              · {{ r.description }}
            </span>
            <MdiChevronRight class="ml-auto size-5 shrink-0 opacity-40 group-hover:opacity-80" />
          </div>
          <div class="mt-2 flex flex-wrap gap-1.5">
            <span
              v-for="it in r.items.slice(0, 12)"
              :key="it.id"
              :title="it.name"
              class="flex size-11 items-center justify-center overflow-hidden rounded-md bg-muted ring-1 ring-black/5"
            >
              <img v-if="thumb(it)" :src="thumb(it)" alt="" class="max-h-full max-w-full object-contain p-0.5" />
              <MdiPackageVariant v-else class="size-4 opacity-50" />
            </span>
            <span
              v-if="r.total > 12"
              class="flex size-11 items-center justify-center rounded-md bg-muted text-xs font-medium text-muted-foreground"
            >
              +{{ r.total - 12 }}
            </span>
          </div>
          <div v-if="r.subs.length" class="mt-2 flex flex-wrap gap-1.5">
            <span
              v-for="s in r.subs"
              :key="s.id"
              class="rounded-full border px-2 py-0.5 text-xs"
              :class="s.total ? 'bg-background' : 'text-muted-foreground'"
            >
              {{ s.name }} <span class="font-medium">{{ s.total }}</span>
            </span>
          </div>
        </NuxtLink>
      </div>
    </div>
  </section>
</template>
