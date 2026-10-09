<template>
  <!-- Home fork: small square thumbnails with their actions underneath, instead of each photo
       at full dialog width with the rest of the form pushed far below it. -->
  <div v-if="photos.length > 0" class="flex flex-wrap gap-3 px-1">
    <div v-for="(photo, index) in photos" :key="index" class="w-24">
      <div
        class="relative flex size-24 items-center justify-center overflow-hidden rounded-md border bg-muted"
        :class="photo.primary ? 'ring-2 ring-primary' : ''"
      >
        <img
          :src="photo.fileBase64"
          class="max-h-full max-w-full object-contain"
          :alt="$t('components.entity.create_modal.uploaded')"
        />
      </div>

      <div class="mt-1 flex justify-center gap-0.5">
        <TooltipProvider :delay-duration="0">
          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                size="icon"
                type="button"
                variant="ghost"
                class="size-7 text-destructive hover:text-destructive"
                @click.prevent="emit('delete', index)"
              >
                <MdiDelete class="size-4" />
                <span class="sr-only">{{ $t("components.entity.create_modal.delete_photo") }}</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{{ $t("components.entity.create_modal.delete_photo") }}</p>
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger as-child>
              <Button size="icon" type="button" variant="ghost" class="size-7" @click.prevent="emit('rotate', index)">
                <MdiRotateClockwise class="size-4" />
                <span class="sr-only">{{ $t("components.entity.create_modal.rotate_photo") }}</span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{{ $t("components.entity.create_modal.rotate_photo") }}</p>
            </TooltipContent>
          </Tooltip>

          <Tooltip>
            <TooltipTrigger as-child>
              <Button
                size="icon"
                type="button"
                variant="ghost"
                class="size-7"
                :class="photo.primary ? 'text-primary' : ''"
                @click.prevent="emit('setPrimary', index)"
              >
                <MdiStar v-if="photo.primary" class="size-4" />
                <MdiStarOutline v-else class="size-4" />
                <span class="sr-only">
                  {{ $t("components.entity.create_modal.set_as_primary_photo", { isPrimary: photo.primary }) }}
                </span>
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              <p>{{ $t("components.entity.create_modal.set_as_primary_photo", { isPrimary: photo.primary }) }}</p>
            </TooltipContent>
          </Tooltip>
        </TooltipProvider>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { Button } from "~/components/ui/button";
  import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "~/components/ui/tooltip";
  import MdiDelete from "~icons/mdi/delete";
  import MdiRotateClockwise from "~icons/mdi/rotate-clockwise";
  import MdiStarOutline from "~icons/mdi/star-outline";
  import MdiStar from "~icons/mdi/star";
  import type { PhotoPreview } from "./photo-uploader";

  defineProps<{
    photos: PhotoPreview[];
  }>();

  const emit = defineEmits<{
    (e: "delete", index: number): void;
    (e: "rotate", index: number): void;
    (e: "setPrimary", index: number): void;
  }>();
</script>
