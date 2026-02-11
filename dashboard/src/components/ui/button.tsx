// Placeholder Button component
export function Button({ children, ...props }: { children: React.ReactNode; [key: string]: any }) {
  return <button {...props}>{children}</button>;
}
