import { useState } from 'react';
import { Button } from '../ui/Button';
import { Input } from '../ui/Input';

type RangeKey = 'today' | 'week' | 'month' | '30d' | 'custom';

export interface DateRange {
  date_from: string;
  date_to: string;
}

interface Props {
  value: DateRange;
  onChange: (range: DateRange) => void;
}

function todayStr(): string {
  return new Date().toISOString().slice(0, 10);
}

function weekStart(): string {
  const d = new Date();
  const day = d.getDay();
  d.setDate(d.getDate() - day + (day === 0 ? -6 : 1));
  return d.toISOString().slice(0, 10);
}

function monthStart(): string {
  const d = new Date();
  d.setDate(1);
  return d.toISOString().slice(0, 10);
}

function daysAgo(n: number): string {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

const RANGES: { key: RangeKey; label: string }[] = [
  { key: 'today', label: '今日' },
  { key: 'week', label: '本周' },
  { key: 'month', label: '本月' },
  { key: '30d', label: '最近30天' },
  { key: 'custom', label: '自定义' },
];

export function TimeRangeFilter({ value, onChange }: Props) {
  const [active, setActive] = useState<RangeKey>('today');
  const [customFrom, setCustomFrom] = useState('');
  const [customTo, setCustomTo] = useState('');

  const handleClick = (key: RangeKey) => {
    setActive(key);
    const t = todayStr();
    if (key === 'today') onChange({ date_from: t, date_to: t });
    else if (key === 'week') onChange({ date_from: weekStart(), date_to: t });
    else if (key === 'month') onChange({ date_from: monthStart(), date_to: t });
    else if (key === '30d') onChange({ date_from: daysAgo(29), date_to: t });
  };

  const handleCustom = (from: string, to: string) => {
    setCustomFrom(from);
    setCustomTo(to);
    if (from && to) onChange({ date_from: from, date_to: to });
  };

  return (
    <div className="flex items-center gap-2 mb-4 flex-wrap">
      {RANGES.map((r) => (
        <Button
          key={r.key}
          size="sm"
          variant={active === r.key ? 'primary' : 'secondary'}
          onClick={() => handleClick(r.key)}
        >
          {r.label}
        </Button>
      ))}
      {active === 'custom' && (
        <div className="flex items-center gap-1">
          <Input
            type="date"
            value={customFrom}
            onChange={(e) => handleCustom(e.target.value, customTo)}
          />
          <span className="text-gray-400 text-sm">至</span>
          <Input
            type="date"
            value={customTo}
            onChange={(e) => handleCustom(customFrom, e.target.value)}
          />
        </div>
      )}
    </div>
  );
}
