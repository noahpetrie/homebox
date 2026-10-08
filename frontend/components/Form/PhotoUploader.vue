<template>
  <div class="w-full">
    <div class="flex w-full flex-col gap-1.5">
      <Label for="photo-uploader" class="flex w-full px-1">
        {{ label }}
      </Label>

      <!-- Home fork: "Take photo" opens the camera directly on phones -->
      <div class="flex gap-2">
        <div v-if="camera" class="relative inline-block grow">
          <Button type="button" variant="outline" class="w-full" aria-hidden="true" @click.prevent="openCamera">
            <MdiCameraOutline class="mr-1 size-4" /> Take photo
          </Button>
          <input
            ref="cameraInput"
            class="absolute left-0 top-0 size-full cursor-pointer opacity-0"
            type="file"
            accept="image/*"
            capture="environment"
            @change="onFilesSelected"
          />
        </div>
        <div class="relative inline-block grow">
          <Button type="button" variant="outline" class="w-full" aria-hidden="true" @click.prevent="openFilePicker">
            {{ buttonLabel }}
          </Button>
          <Input
            id="photo-uploader"
            ref="fileInput"
            class="absolute left-0 top-0 size-full cursor-pointer opacity-0"
            type="file"
            accept="image/png,image/jpeg,image/gif,image/avif,image/webp,android/force-camera-workaround"
            multiple
            @change="onFilesSelected"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
  import { computed, ref } from "vue";
  import { useI18n } from "vue-i18n";
  import { Label } from "~/components/ui/label";
  import { Input } from "~/components/ui/input";
  import { Button } from "~/components/ui/button";
  import { filesToPhotoPreviews, type PhotoPreview } from "./photo-uploader";
  import MdiCameraOutline from "~icons/mdi/camera-outline";

  const props = withDefaults(
    defineProps<{
      label?: string;
      buttonLabel?: string;
      existingCount?: number;
      camera?: boolean;
    }>(),
    {
      label: undefined,
      buttonLabel: undefined,
      existingCount: 0,
      camera: false,
    }
  );

  const emit = defineEmits<{
    (e: "selected", photos: PhotoPreview[]): void;
  }>();

  const { t } = useI18n();
  const fileInput = ref<HTMLInputElement | null>(null);

  const label = computed(() => props.label || t("components.entity.create_modal.item_photo"));
  const buttonLabel = computed(() => props.buttonLabel || t("components.entity.create_modal.upload_photos"));

  const cameraInput = ref<HTMLInputElement | null>(null);

  function openFilePicker() {
    fileInput.value?.click();
  }

  function openCamera() {
    cameraInput.value?.click();
  }

  async function onFilesSelected(event: Event) {
    const input = event.target as HTMLInputElement;
    if (!input.files || input.files.length === 0) return;

    const photos = await filesToPhotoPreviews(input.files, props.existingCount);

    emit("selected", photos);
    input.value = "";
  }
</script>
