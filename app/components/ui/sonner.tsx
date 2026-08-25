// Provides the shared Sonner UI.
"use client";

import { Toaster as Sonner, ToasterProps } from "sonner";

// Renders the Toaster component.
const Toaster = ({ ...props }: ToasterProps) => {
  return (
    <Sonner
      // The application uses a light UI; avoid system dark mode making toast descriptions unreadable.
      theme="light"
      className="toaster group"
      style={
        {
          "--normal-bg": "var(--popover)",
          "--normal-text": "var(--popover-foreground)",
          "--normal-border": "var(--border)",
        } as React.CSSProperties
      }
      {...props}
    />
  );
};

export { Toaster };
