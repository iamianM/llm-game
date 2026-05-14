import clsx from "clsx";
import type React from "react";

type Props = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost";
};

export function Button({ className, variant = "primary", ...props }: Props) {
  return (
    <button
      {...props}
      className={clsx(
        "rounded-[var(--r-md)] px-5 py-3 text-sm font-semibold transition disabled:cursor-not-allowed disabled:opacity-50",
        variant === "primary" && "bg-accent text-[var(--card)] shadow-[var(--shadow-sm)] hover:-translate-y-0.5 hover:shadow-[var(--shadow-md)]",
        variant === "secondary" && "border border-line bg-transparent text-[var(--card)] hover:border-accent",
        variant === "ghost" && "text-accent hover:underline",
        className
      )}
    />
  );
}
