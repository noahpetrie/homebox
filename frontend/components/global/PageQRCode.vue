<script setup lang="ts">
  import { DialogID } from "@/components/ui/dialog-provider/utils";
  import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
  import { route } from "~/lib/api/base";
  import MdiQrcode from "~icons/mdi/qrcode";
  import { Button } from "@/components/ui/button";
  import { Tooltip, TooltipContent, TooltipTrigger } from "@/components/ui/tooltip";
  import { useDialog } from "@/components/ui/dialog-provider";

  // Home fork: dialogOnly renders just the dialog, for pages that open it from a menu.
  defineProps<{ dialogOnly?: boolean }>();

  const { openDialog } = useDialog();

  function getQRCodeUrl(): string {
    const currentURL = window.location.href;
    // Adjust route import as needed
    return route(`/qrcode`, { data: encodeURIComponent(currentURL) });
  }
</script>

<template>
  <Dialog :dialog-id="DialogID.PageQRCode">
    <DialogContent>
      <DialogHeader>
        <DialogTitle>
          {{ $t("components.global.page_qr_code.page_url") }}
        </DialogTitle>
      </DialogHeader>
      <img :src="getQRCodeUrl()" />
    </DialogContent>
  </Dialog>

  <Tooltip v-if="!dialogOnly">
    <TooltipTrigger as-child>
      <Button size="icon" @click="openDialog(DialogID.PageQRCode)">
        <MdiQrcode name="mdi-qrcode" />
      </Button>
    </TooltipTrigger>
    <TooltipContent>
      {{ $t("components.global.page_qr_code.qr_tooltip") }}
    </TooltipContent>
  </Tooltip>
</template>
