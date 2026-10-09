<script setup lang="ts">
  // Home fork: right-click (or long-press on a phone) menu for an item card on a location page:
  // take it out of a box, move it somewhere else, open it, or delete it.
  import {
    ContextMenuContent,
    ContextMenuItem,
    ContextMenuPortal,
    ContextMenuRoot,
    ContextMenuSeparator,
    ContextMenuTrigger,
  } from "reka-ui";
  import type { EntitySummary } from "~~/lib/api/types/data-contracts";
  import MdiOpenInNew from "~icons/mdi/open-in-new";
  import MdiTrayArrowUp from "~icons/mdi/tray-arrow-up";
  import MdiFolderMoveOutline from "~icons/mdi/folder-move-outline";
  import MdiDelete from "~icons/mdi/delete";

  defineProps<{
    item: EntitySummary;
    /** where "Take out" sends the item: the room the box sits in */
    outside?: { id: string; name: string } | null;
    containerName?: string;
  }>();
  const emit = defineEmits<{
    (e: "takeOut" | "move" | "delete", item: EntitySummary): void;
  }>();

  const itemClass =
    "relative flex cursor-default select-none items-center gap-2 rounded-sm px-2 py-1.5 text-sm outline-none transition-colors focus:bg-accent focus:text-accent-foreground data-[highlighted]:bg-accent [&>svg]:size-4 [&>svg]:shrink-0";
</script>

<template>
  <ContextMenuRoot>
    <ContextMenuTrigger as-child>
      <slot />
    </ContextMenuTrigger>
    <ContextMenuPortal>
      <ContextMenuContent
        class="z-50 min-w-48 overflow-hidden rounded-md border bg-popover p-1 text-popover-foreground shadow-md data-[state=open]:animate-in data-[state=open]:fade-in-0 data-[state=open]:zoom-in-95"
      >
        <div class="truncate px-2 py-1 text-xs font-medium text-muted-foreground">{{ item.name }}</div>
        <ContextMenuItem :class="itemClass" @select="navigateTo(`/item/${item.id}`)">
          <MdiOpenInNew /> Open
        </ContextMenuItem>
        <ContextMenuItem v-if="outside" :class="itemClass" @select="emit('takeOut', item)">
          <MdiTrayArrowUp /> Take out of {{ containerName }}
          <span class="ml-auto pl-3 text-xs text-muted-foreground">to {{ outside.name }}</span>
        </ContextMenuItem>
        <ContextMenuItem :class="itemClass" @select="emit('move', item)">
          <MdiFolderMoveOutline /> Move to…
        </ContextMenuItem>
        <ContextMenuSeparator class="-mx-1 my-1 h-px bg-muted" />
        <ContextMenuItem :class="[itemClass, 'text-destructive focus:text-destructive']" @select="emit('delete', item)">
          <MdiDelete /> Delete…
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenuPortal>
  </ContextMenuRoot>
</template>
