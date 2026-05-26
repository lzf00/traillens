import { Slot } from "@radix-ui/react-slot";
import { forwardRef } from "react";
import { cn } from "@/lib/cn";

type Variant = "primary" | "secondary" | "ghost" | "danger";

const variantClass: Record<Variant, string> = {
  primary: "bg-accent-aurora text-bg-base hover:bg-accent-aurora/90",
  secondary: "border border-divider text-fg-primary hover:border-accent-glacier hover:text-accent-glacier",
  ghost: "text-fg-secondary hover:text-fg-primary hover:bg-bg-raised",
  danger: "bg-accent-danger/15 text-accent-danger hover:bg-accent-danger/25",
};

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: Variant;
  asChild?: boolean;
};

export const Button = forwardRef<HTMLButtonElement, Props>(function Button(
  { variant = "primary", asChild, className, ...rest },
  ref,
) {
  const Comp = asChild ? Slot : "button";
  return (
    <Comp
      ref={ref}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-md px-4 py-2 text-sm font-medium",
        "transition-all duration-DEFAULT ease-trail",
        "disabled:opacity-40 disabled:pointer-events-none",
        variantClass[variant],
        className,
      )}
      {...rest}
    />
  );
});
