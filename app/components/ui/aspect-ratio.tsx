// Provides the shared Aspect Ratio UI.
"use client";

import * as AspectRatioPrimitive from "@radix-ui/react-aspect-ratio";

// Renders the Aspect Ratio component.
function AspectRatio({
  ...props
}: React.ComponentProps<typeof AspectRatioPrimitive.Root>) {
  return <AspectRatioPrimitive.Root data-slot="aspect-ratio" {...props} />;
}

export { AspectRatio };
