// Placeholder Badge component
export function Badge({ children, variant, className, ...props }: { children: React.ReactNode; variant?: string; className?: string; [key: string]: any }) {
  return <span className={className} data-variant={variant} {...props}>{children}</span>;
}
