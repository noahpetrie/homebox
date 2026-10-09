<script setup lang="ts">
  // Home fork: the items section of a location page. Search (title, author, ISBN, maker,
  // model), type filter chips, sort, and Grid / List / Table views. Table is the original
  // selectable view, so bulk actions are still available there.
  import type { EntitySummary } from "~~/lib/api/types/data-contracts";
  import MdiMagnify from "~icons/mdi/magnify";
  import MdiViewGridOutline from "~icons/mdi/view-grid-outline";
  import MdiViewListOutline from "~icons/mdi/view-list-outline";
  import MdiTable from "~icons/mdi/table";
  import MdiChevronRight from "~icons/mdi/chevron-right";
  import MdiPackageVariant from "~icons/mdi/package-variant";
  import { Badge } from "@/components/ui/badge";
  import { Button, ButtonGroup } from "@/components/ui/button";
  import { Input } from "@/components/ui/input";
  import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
  import ItemCard from "~/components/Item/Card.vue";
  import ItemViewSelectable from "~/components/Item/View/Selectable.vue";
  import ItemContextMenu from "~/components/Location/ItemContextMenu.vue";
  import { moveItem, PACKED_FROM, parsePackedFrom, type Place } from "~/composables/use-packing";
  import LocationSelector from "~/components/Location/Selector.vue";
  import { toast } from "@/components/ui/sonner";
  import { DialogRoot } from "reka-ui";
  import { DialogContent, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";

  const props = defineProps<{
    items: EntitySummary[];
    /** the location being viewed (e.g. a box) and where "Take out" puts things (its room) */
    container?: { id: string; name: string } | null;
    outside?: { id: string; name: string } | null;
  }>();
  const emit = defineEmits<{ (e: "refresh"): void }>();

  // Home fork: right-click / long-press actions on an item (see ItemContextMenu)
  const confirm = useConfirm();
  const moving = ref<EntitySummary | null>(null);
  const moveTo = ref<EntitySummary | null>(null);
  const moveOpen = computed({
    get: () => !!moving.value,
    set: v => {
      if (!v) moving.value = null;
    },
  });

  async function relocate(item: EntitySummary, target: { id: string; name: string }) {
    const { error } = await moveItem(api, item.id, target, null);
    if (error) {
      toast.error(`Couldn't move ${item.name}`);
      return;
    }
    toast.success(`${item.name} → ${target.name}`);
    emit("refresh");
  }

  // back to where packing took it from; otherwise the room the box is in
  const takeOutTo = (item: EntitySummary): Place | null => extras.value[item.id]?.packedFrom ?? props.outside ?? null;

  function takeOut(item: EntitySummary) {
    const to = takeOutTo(item);
    if (to) relocate(item, to);
  }

  function startMove(item: EntitySummary) {
    moveTo.value = null;
    moving.value = item;
  }

  async function confirmMove() {
    const item = moving.value;
    const target = moveTo.value;
    if (!item || !target) return;
    moving.value = null;
    await relocate(item, { id: target.id, name: target.name });
  }

  async function remove(item: EntitySummary) {
    const result = await confirm.open(`Delete "${item.name}"? This removes it from Homebox completely.`);
    if (result.isCanceled) return;
    const { error } = await api.items.delete(item.id);
    if (error) {
      toast.error(`Couldn't delete ${item.name}`);
      return;
    }
    toast.success(`Deleted ${item.name}`);
    emit("refresh");
  }

  const api = useUserApi();

  type View = "grid" | "list" | "table";
  type Sort = "recent" | "name" | "author" | "year";
  const view = useLocalStorage<View>("homebox:location.view", "grid");
  const sort = useLocalStorage<Sort>("homebox:location.sort", "recent");
  const query = ref("");
  const typeFilter = ref<string>("all");

  // Custom fields aren't in the list response, so load each item's details in the background
  // (a few at a time) for the author / year / ISBN shown and searched here.
  type Extra = {
    author: string;
    year: string;
    isbn: string;
    manufacturer: string;
    model: string;
    packedFrom: Place | null;
  };
  const extras = ref<Record<string, Extra>>({});
  const seenAt: Record<string, string> = {};
  const field = (fields: { name: string; textValue: string }[], name: string) =>
    fields.find(f => f.name.toLowerCase() === name)?.textValue ?? "";

  watch(
    () => props.items.map(i => i.id + i.updatedAt).join(),
    async () => {
      const todo = props.items.filter(i => !extras.value[i.id] || seenAt[i.id] !== String(i.updatedAt));
      for (const i of todo) seenAt[i.id] = String(i.updatedAt);
      const queue = [...todo];
      const worker = async () => {
        while (queue.length) {
          const it = queue.shift()!;
          const { data } = await api.items.get(it.id);
          if (!data) continue;
          const published = field(data.fields, "published") || field(data.fields, "year");
          extras.value[it.id] = {
            author: field(data.fields, "author"),
            year: published.match(/\b(1[5-9]|20)\d{2}\b/)?.[0] ?? "",
            isbn: field(data.fields, "isbn") || field(data.fields, "barcode"),
            manufacturer: data.manufacturer ?? "",
            model: data.modelNumber ?? "",
            packedFrom: parsePackedFrom(data.fields.find(f => f.name === PACKED_FROM)?.textValue),
          };
        }
      };
      await Promise.all([worker(), worker(), worker(), worker(), worker(), worker()]);
    },
    { immediate: true }
  );

  const typeCounts = computed(() => {
    const counts = new Map<string, number>();
    for (const it of props.items) {
      const name = it.entityType?.name ?? "Item";
      counts.set(name, (counts.get(name) ?? 0) + 1);
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1]);
  });

  // "Book" → "Books", but "Electronics" and "Furniture & Decor" stay as they are
  const plural = (name: string) => (/s$|&/i.test(name) ? name : `${name}s`);

  function subtitle(it: EntitySummary): string {
    const x = extras.value[it.id];
    if (!x) return "";
    if (x.author) return [x.author, x.year].filter(Boolean).join(" · ");
    return [x.manufacturer, x.model === x.isbn ? "" : x.model].filter(Boolean).join(" · ");
  }

  const visible = computed(() => {
    const q = query.value.trim().toLowerCase();
    let list = props.items.filter(it => {
      if (typeFilter.value !== "all" && (it.entityType?.name ?? "Item") !== typeFilter.value) return false;
      if (!q) return true;
      const x = extras.value[it.id];
      const hay = [it.name, it.description, x?.author, x?.isbn, x?.manufacturer, x?.model].join(" ").toLowerCase();
      return q.split(/\s+/).every(word => hay.includes(word));
    });
    const by = sort.value;
    const authorKey = (it: EntitySummary) => {
      // sort by surname: last word of the first listed author
      const a = extras.value[it.id]?.author.split(/,| and /)[0]?.trim() ?? "";
      return (a.split(" ").pop() ?? "").toLowerCase() || "~"; // no author sorts last
    };
    list = [...list].sort((a, b) => {
      if (by === "name") return a.name.localeCompare(b.name);
      if (by === "author") return authorKey(a).localeCompare(authorKey(b)) || a.name.localeCompare(b.name);
      if (by === "year") return (extras.value[b.id]?.year ?? "").localeCompare(extras.value[a.id]?.year ?? "");
      return String(b.createdAt).localeCompare(String(a.createdAt));
    });
    return list;
  });

  function thumbUrl(it: EntitySummary) {
    return it.imageId ? api.authURL(`/entities/${it.id}/attachments/${it.thumbnailId || it.imageId}`) : "";
  }
</script>

<template>
  <section class="mt-6">
    <div class="mb-3 flex flex-wrap items-center gap-2">
      <h2 class="mr-1 flex items-center gap-2 text-xl font-semibold">
        Items <Badge>{{ items.length }}</Badge>
      </h2>
      <div class="relative min-w-48 grow sm:max-w-sm">
        <MdiMagnify class="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 opacity-60" />
        <Input v-model="query" type="search" placeholder="Search title, author, ISBN…" class="h-9 pl-8" />
      </div>
      <div class="ml-auto flex flex-wrap items-center gap-2">
        <Select v-if="view !== 'table'" v-model="sort">
          <SelectTrigger class="h-9 w-40"><SelectValue /></SelectTrigger>
          <SelectContent>
            <SelectItem value="recent">Recently added</SelectItem>
            <SelectItem value="name">Title A–Z</SelectItem>
            <SelectItem value="author">Author</SelectItem>
            <SelectItem value="year">Newest first</SelectItem>
          </SelectContent>
        </Select>
        <ButtonGroup>
          <Button
            size="sm"
            :variant="view === 'grid' ? 'default' : 'outline'"
            data-pos="start"
            aria-label="Grid"
            @click="view = 'grid'"
          >
            <MdiViewGridOutline />
          </Button>
          <Button
            size="sm"
            :variant="view === 'list' ? 'default' : 'outline'"
            data-pos="middle"
            aria-label="List"
            @click="view = 'list'"
          >
            <MdiViewListOutline />
          </Button>
          <Button
            size="sm"
            :variant="view === 'table' ? 'default' : 'outline'"
            data-pos="end"
            aria-label="Table"
            @click="view = 'table'"
          >
            <MdiTable />
          </Button>
        </ButtonGroup>
      </div>
    </div>

    <div v-if="typeCounts.length > 1 && view !== 'table'" class="mb-3 flex flex-wrap gap-1.5">
      <Button
        size="sm"
        class="h-7 rounded-full"
        :variant="typeFilter === 'all' ? 'default' : 'outline'"
        @click="typeFilter = 'all'"
      >
        All {{ items.length }}
      </Button>
      <Button
        v-for="[name, count] in typeCounts"
        :key="name"
        size="sm"
        class="h-7 rounded-full"
        :variant="typeFilter === name ? 'default' : 'outline'"
        @click="typeFilter = typeFilter === name ? 'all' : name"
      >
        {{ plural(name) }} {{ count }}
      </Button>
    </div>

    <p v-if="view !== 'table' && visible.length === 0" class="py-10 text-center text-muted-foreground">
      <template v-if="query.trim() || typeFilter !== 'all'">Nothing matches “{{ query }}”.</template>
      <template v-else>Nothing here yet.</template>
    </p>

    <!-- Grid -->
    <div v-if="view === 'grid'" class="grid grid-cols-1 gap-4 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4">
      <ItemContextMenu
        v-for="it in visible"
        :key="it.id"
        :item="it"
        :outside="takeOutTo(it)"
        :container-name="container?.name"
        @take-out="takeOut"
        @move="startMove"
        @delete="remove"
      >
        <ItemCard :item="it" hide-location :subtitle="subtitle(it)" />
      </ItemContextMenu>
    </div>

    <!-- List -->
    <div v-else-if="view === 'list'" class="overflow-hidden rounded-lg border bg-card">
      <ItemContextMenu
        v-for="it in visible"
        :key="it.id"
        :item="it"
        :outside="takeOutTo(it)"
        :container-name="container?.name"
        @take-out="takeOut"
        @move="startMove"
        @delete="remove"
      >
        <NuxtLink
          :to="`/item/${it.id}`"
          class="flex items-center gap-3 border-b px-3 py-2 last:border-b-0 hover:bg-accent/60"
        >
          <img
            v-if="thumbUrl(it)"
            :src="thumbUrl(it)"
            :alt="it.name"
            loading="lazy"
            class="h-14 w-10 shrink-0 rounded-sm object-contain"
          />
          <div v-else class="flex h-14 w-10 shrink-0 items-center justify-center rounded-sm bg-muted">
            <MdiPackageVariant class="size-5 opacity-50" />
          </div>
          <div class="min-w-0 grow">
            <div class="truncate font-medium">{{ it.name }}</div>
            <div class="truncate text-sm text-muted-foreground">{{ subtitle(it) || it.description }}</div>
          </div>
          <span v-if="extras[it.id]?.isbn" class="hidden shrink-0 font-mono text-xs text-muted-foreground md:block">
            {{ extras[it.id]!.isbn }}
          </span>
          <span class="hidden shrink-0 text-xs text-muted-foreground sm:block">{{ it.entityType?.name }}</span>
          <MdiChevronRight class="size-5 shrink-0 opacity-40" />
        </NuxtLink>
      </ItemContextMenu>
    </div>

    <!-- Table: the original selectable view (bulk actions) -->
    <ItemViewSelectable v-else :items="items" view="table" @refresh="$emit('refresh')" />

    <p v-if="view !== 'table' && visible.length" class="mt-3 text-center text-xs text-muted-foreground">
      Right-click an item (long-press on a phone) to
      {{ outside ? `take it out of ${container?.name}, ` : "" }}move or delete it.
    </p>

    <DialogRoot v-model:open="moveOpen">
      <DialogContent class="max-w-md">
        <DialogHeader>
          <DialogTitle>Move {{ moving?.name }}</DialogTitle>
        </DialogHeader>
        <LocationSelector v-model="moveTo" />
        <DialogFooter>
          <Button variant="outline" @click="moving = null">Cancel</Button>
          <Button :disabled="!moveTo" @click="confirmMove">Move</Button>
        </DialogFooter>
      </DialogContent>
    </DialogRoot>
  </section>
</template>
