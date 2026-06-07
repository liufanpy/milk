import { Badge } from './Badge';

interface StatusConfig {
  [status: string]: {
    label: string;
    variant: 'success' | 'warning' | 'danger' | 'default';
  };
}

interface StatusBadgeProps {
  status: string;
  config: StatusConfig;
}

export function StatusBadge({ status, config }: StatusBadgeProps) {
  const item = config[status] ?? { label: status, variant: 'default' as const };
  return <Badge variant={item.variant}>{item.label}</Badge>;
}
