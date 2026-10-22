<script setup lang="ts">
  import type { DialogRootEmits, DialogRootProps } from "reka-ui";
  import { Dialog, DialogContent } from "@/components/ui/dialog";
  import { useForwardPropsEmits } from "reka-ui";
  import { computed } from "vue";
  import Command from "./Command.vue";
  import type { DialogID } from "@/components/ui/dialog-provider/utils";

  // Home fork: ignoreFilter turns off the built-in text filter (the menu filters its own items)
  const props = defineProps<DialogRootProps & { dialogId: DialogID; ignoreFilter?: boolean }>();
  const emits = defineEmits<DialogRootEmits>();

  const dialogProps = computed(() => {
    const { ignoreFilter: _, ...rest } = props;
    return rest;
  });
  const forwarded = useForwardPropsEmits(dialogProps, emits);
</script>

<template>
  <Dialog v-bind="forwarded">
    <!-- https://github.com/unovue/reka-ui/issues/1743 -->
    <DialogContent class="overflow-hidden p-0 shadow-lg" disable-portal>
      <Command
        :ignore-filter="ignoreFilter"
        class="[&_[cmdk-group-heading]]:px-2 [&_[cmdk-group-heading]]:font-medium [&_[cmdk-group-heading]]:text-muted-foreground [&_[cmdk-group]:not([hidden])_~[cmdk-group]]:pt-0 [&_[cmdk-group]]:px-2 [&_[cmdk-input-wrapper]_svg]:size-5 [&_[cmdk-input]]:h-12 [&_[cmdk-item]]:px-2 [&_[cmdk-item]]:py-3 [&_[cmdk-item]_svg]:size-5"
      >
        <slot />
      </Command>
    </DialogContent>
  </Dialog>
</template>
