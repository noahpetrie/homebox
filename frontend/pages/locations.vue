<script setup lang="ts">
  import { packVersion } from "~/composables/use-packing";
  import { useI18n } from "vue-i18n";
  import { useTreeState } from "~~/components/Location/Tree/tree-state";
  import MdiCollapseAllOutline from "~icons/mdi/collapse-all-outline";
  import MdiExpandAllOutline from "~icons/mdi/expand-all-outline";
  import MdiPackageVariant from "~icons/mdi/package-variant";
  import MdiMapMarker from "~icons/mdi/map-marker";
  import MdiPlus from "~icons/mdi/plus";
  import MdiViewGridOutline from "~icons/mdi/view-grid-outline";
  import MdiFileTreeOutline from "~icons/mdi/file-tree-outline";
  import { Badge } from "@/components/ui/badge";
  import { Card } from "@/components/ui/card";
  import { DialogID } from "@/components/ui/dialog-provider/utils";
  import { useDialog } from "@/components/ui/dialog-provider";
  import type { EntitySummary, TreeItem } from "~/lib/api/types/data-contracts";

  import { Button, ButtonGroup } from "@/components/ui/button";
  import BaseContainer from "@/components/Base/Container.vue";
  import BaseSectionHeader from "@/components/Base/SectionHeader.vue";
  import LocationTreeRoot from "~/components/Location/Tree/Root.vue";
  import BaseCard from "@/components/Base/Card.vue";

  const { t } = useI18n();

  // TODO: eventually move to https://reka-ui.com/docs/components/tree#draggable-sortable-tree

  definePageMeta({
    middleware: ["auth"],
  });

  useHead({
    title: "HomeBox | " + t("menu.locations"),
  });

  const api = useUserApi();

  const { data: tree, refresh: refreshTree } = useAsyncData(async () => {
    const { data, error } = await api.items.getTree({
      withItems: true,
    });

    if (error) {
      return [];
    }

    return data;
  });

  const locationTreeId = "locationTree";
  const showItemsKey = "showItems";

  const treeState = useTreeState(locationTreeId);
  const showItems = ref(true);

  const route = useRouter();

  onMounted(() => {
    // set tree state from query params
    const query = route.currentRoute.value.query;

    if (query && query[locationTreeId]) {
      console.debug("setting tree state from query params");
      const data = JSON.parse(query[locationTreeId] as string);

      for (const key in data) {
        treeState.value[key] = data[key];
      }
    }

    if (query && query[showItemsKey] !== undefined) {
      showItems.value = query[showItemsKey] === "true";
    }
  });

  watch(
    treeState,
    () => {
      // Push the current state to the URL
      route.replace({
        query: {
          [locationTreeId]: JSON.stringify(treeState.value),
          [showItemsKey]: showItems.value.toString(),
        },
      });
    },
    { deep: true }
  );

  watch(showItems, () => {
    route.replace({
      query: {
        [locationTreeId]: JSON.stringify(treeState.value),
        [showItemsKey]: showItems.value.toString(),
      },
    });
  });

  function closeAll() {
    for (const key in treeState.value) {
      treeState.value[key] = false;
    }
  }

  function openItemChildren(items: TreeItem[]) {
    for (const item of items) {
      if (item.children.length > 0) {
        treeState.value[item.id.replace(/-/g, "").substring(0, 8)] = true;
        openItemChildren(item.children);
      }
    }
  }

  function openAll() {
    if (!tree.value) return;

    openItemChildren(tree.value);
  }

  // ---- Home fork: card view (default) -------------------------------------
  // One card per top-level location with its item count, a strip of item photos
  // and the sub-locations inside it. The tree is still one click away.
  const { openDialog } = useDialog();
  const VIEW_KEY = "homebox:locationsView";
  const view = ref<"cards" | "tree">("cards");
  onMounted(() => {
    try {
      if (localStorage.getItem(VIEW_KEY) === "tree") view.value = "tree";
    } catch {
      // storage unavailable (private mode); stay on cards
    }
  });
  watch(view, v => {
    try {
      localStorage.setItem(VIEW_KEY, v);
    } catch {
      // storage unavailable; the choice just isn't remembered
    }
  });

  const { data: locationSummaries, refresh: refreshSummaries } = useAsyncData(async () => {
    const { data } = await api.items.getLocations({ filterChildren: false });
    return data ?? [];
  });
  const { data: allItems, refresh: refreshAllItems } = useAsyncData(async () => {
    const { data } = await api.items.getAll({ pageSize: 1000, orderBy: "createdAt" });
    return data?.items ?? [];
  });

  type LocationCard = {
    id: string;
    name: string;
    description: string;
    children: { id: string; name: string }[];
    count: number;
    previews: EntitySummary[];
  };

  const locationCards = computed<LocationCard[]>(() => {
    const summaries = new Map((locationSummaries.value ?? []).map(l => [l.id, l]));
    const byParent = new Map<string, EntitySummary[]>();
    for (const it of allItems.value ?? []) {
      const pid = it.parent?.id;
      if (!pid) continue;
      if (!byParent.has(pid)) byParent.set(pid, []);
      byParent.get(pid)!.push(it);
    }
    const isLoc = (n: TreeItem) => n.type === "location";
    const collect = (node: TreeItem): EntitySummary[] => [
      ...(byParent.get(node.id) ?? []),
      ...node.children.filter(isLoc).flatMap(collect),
    ];

    return (
      (tree.value ?? [])
        .filter(isLoc)
        .map(node => {
          const items = collect(node);
          const withPhoto = items.filter(i => i.imageId);
          return {
            id: node.id,
            name: node.name,
            description: summaries.get(node.id)?.description ?? "",
            children: node.children.filter(isLoc).map(c => ({ id: c.id, name: c.name })),
            count: items.length,
            // newest first, photos first
            previews: [...withPhoto].reverse().slice(0, 8),
          };
        })
        // locations with things in them first, then alphabetical
        .sort((a, b) => Number(b.count > 0) - Number(a.count > 0) || a.name.localeCompare(b.name))
    );
  });

  const filledLocations = computed(() => locationCards.value.filter(l => l.count > 0 || l.children.length > 0));
  const emptyLocations = computed(() => locationCards.value.filter(l => l.count === 0 && l.children.length === 0));

  const totalItems = computed(() => (allItems.value ?? []).length);

  function thumbUrl(item: EntitySummary) {
    return api.authURL(`/entities/${item.id}/attachments/${item.thumbnailId || item.imageId}`);
  }

  function newLocation() {
    openDialog(DialogID.CreateEntity, { params: { baseType: "location" } });
  }

  // Home fork: keep counts current while packing items into a box
  watch(packVersion, () => {
    refreshTree();
    refreshSummaries();
    refreshAllItems();
  });
</script>

<template>
  <BaseContainer>
    <div class="mb-4 flex flex-wrap items-end justify-between gap-3">
      <div>
        <BaseSectionHeader class="pb-0"> {{ $t("menu.locations") }} </BaseSectionHeader>
        <p v-if="locationCards.length" class="text-sm text-muted-foreground">
          {{ locationCards.length }} {{ locationCards.length === 1 ? "location" : "locations" }} · {{ totalItems }}
          {{ totalItems === 1 ? "item" : "items" }}
        </p>
      </div>
      <div class="flex flex-wrap items-center gap-2">
        <ButtonGroup>
          <Button
            size="sm"
            :variant="view === 'cards' ? 'default' : 'outline'"
            data-pos="start"
            @click="view = 'cards'"
          >
            <MdiViewGridOutline class="mr-1" /> Cards
          </Button>
          <Button size="sm" :variant="view === 'tree' ? 'default' : 'outline'" data-pos="end" @click="view = 'tree'">
            <MdiFileTreeOutline class="mr-1" /> Tree
          </Button>
        </ButtonGroup>
        <Button size="sm" @click="newLocation"> <MdiPlus class="mr-1" /> New location </Button>
      </div>
    </div>

    <!-- Card view: rooms with things in them as cards, empty rooms as a compact strip -->
    <template v-if="view === 'cards'">
      <div class="grid grid-cols-1 items-start gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <NuxtLink v-for="loc in filledLocations" :key="loc.id" :to="`/location/${loc.id}`" class="group">
          <Card class="flex flex-col gap-3 p-4 transition-colors group-hover:border-primary/60">
            <div class="flex items-start gap-3">
              <div class="flex size-9 shrink-0 items-center justify-center rounded-md bg-accent text-accent-foreground">
                <MdiMapMarker class="size-5" />
              </div>
              <div class="min-w-0 grow">
                <h3 class="truncate text-base font-semibold group-hover:underline">{{ loc.name }}</h3>
                <p v-if="loc.description" class="truncate text-sm text-muted-foreground">{{ loc.description }}</p>
              </div>
              <Badge class="shrink-0">{{ loc.count }} {{ loc.count === 1 ? "item" : "items" }}</Badge>
            </div>

            <div v-if="loc.previews.length" class="flex items-center gap-2">
              <div class="flex h-16 min-w-0 grow items-center gap-1.5 overflow-hidden">
                <!-- book covers keep their shape; other photos get a square tile showing the whole photo -->
                <img
                  v-for="p in loc.previews"
                  :key="p.id"
                  :src="thumbUrl(p)"
                  :alt="p.name"
                  :title="p.name"
                  loading="lazy"
                  class="h-16 shrink-0 rounded-sm border shadow-sm"
                  :class="p.entityType?.name === 'Book' ? 'w-11 object-cover' : 'w-16 bg-white object-contain p-1'"
                />
              </div>
              <span v-if="loc.count > loc.previews.length" class="shrink-0 text-xs text-muted-foreground">
                +{{ loc.count - loc.previews.length }} more
              </span>
            </div>

            <div v-if="loc.children.length" class="flex flex-wrap gap-1 text-xs">
              <span class="text-muted-foreground">Inside:</span>
              <span
                v-for="c in loc.children"
                :key="c.id"
                class="rounded bg-accent px-1.5 py-0.5 text-accent-foreground"
              >
                {{ c.name }}
              </span>
            </div>
          </Card>
        </NuxtLink>
      </div>

      <div class="mt-4 flex flex-wrap items-center gap-2 text-sm">
        <span v-if="emptyLocations.length" class="mr-1 text-muted-foreground">Empty:</span>
        <NuxtLink
          v-for="loc in emptyLocations"
          :key="loc.id"
          :to="`/location/${loc.id}`"
          class="flex items-center gap-1.5 rounded-full border bg-card px-3 py-1.5 hover:border-primary/60"
        >
          <MdiMapMarker class="size-4 opacity-60" />
          {{ loc.name }}
        </NuxtLink>
        <button
          type="button"
          class="flex items-center gap-1 rounded-full border border-dashed border-foreground/30 px-3 py-1.5 text-muted-foreground hover:border-primary hover:text-foreground"
          @click="newLocation"
        >
          <MdiPlus class="size-4" />
          New location
        </button>
      </div>
    </template>

    <!-- Tree view -->
    <template v-else>
      <div class="mb-2 flex flex-wrap justify-end gap-2">
        <Button size="sm" variant="outline" @click="openAll">
          <MdiExpandAllOutline class="mr-1" /> {{ $t("locations.expand_tree") }}
        </Button>
        <Button size="sm" variant="outline" @click="closeAll">
          <MdiCollapseAllOutline class="mr-1" /> {{ $t("locations.collapse_tree") }}
        </Button>
        <Button size="sm" :variant="showItems ? 'default' : 'outline'" @click="showItems = !showItems">
          <MdiPackageVariant class="mr-1" /> {{ showItems ? $t("locations.hide_items") : $t("locations.show_items") }}
        </Button>
      </div>
      <BaseCard>
        <div class="p-2">
          <LocationTreeRoot
            v-if="tree && Array.isArray(tree)"
            :locs="tree"
            :tree-id="locationTreeId"
            :show-items="showItems"
          />
        </div>
      </BaseCard>
    </template>
  </BaseContainer>
</template>
