import { useState, useRef } from 'react';
import { Modal } from '../ui/Modal';
import { Button } from '../ui/Button';
import { Badge } from '../ui/Badge';

interface ImportRow {
  index: number;
  data: Record<string, string>;
  status: 'ok' | 'error';
  msg: string;
}

interface Props {
  open: boolean;
  onClose: () => void;
  title: string;
  onImport: (file: File) => Promise<{ headers: string[]; rows: ImportRow[]; summary: { total: number; ok: number; error: number } }>;
  onConfirm: (selected: ImportRow[]) => Promise<{ success: number; errors: any[] }>;
  onDone: () => void;
}

export default function CsvImportModal({ open, onClose, title, onImport, onConfirm, onDone }: Props) {
  const [stage, setStage] = useState<'upload' | 'preview' | 'result'>('upload');
  const [headers, setHeaders] = useState<string[]>([]);
  const [rows, setRows] = useState<ImportRow[]>([]);
  const [summary, setSummary] = useState({ total: 0, ok: 0, error: 0 });
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<{ success: number; errors: any[] } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setLoading(true);
    try {
      const data = await onImport(file);
      setHeaders(data.headers);
      setRows(data.rows);
      setSummary(data.summary);
      const okIndices = new Set(data.rows.filter((r: ImportRow) => r.status === 'ok').map((r: ImportRow) => r.index));
      setSelected(okIndices);
      setStage('preview');
    } catch (err: any) {
      alert('解析失败: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const toggleRow = (index: number) => {
    setSelected(prev => {
      const next = new Set(prev);
      if (next.has(index)) next.delete(index);
      else next.add(index);
      return next;
    });
  };

  const toggleAll = () => {
    const okRows = rows.filter(r => r.status === 'ok');
    if (okRows.every(r => selected.has(r.index))) {
      setSelected(new Set());
    } else {
      setSelected(new Set(okRows.map(r => r.index)));
    }
  };

  const handleConfirm = async () => {
    const toImport = rows.filter(r => selected.has(r.index) && r.status === 'ok');
    if (toImport.length === 0) { alert('请至少选择一条'); return; }
    setLoading(true);
    try {
      const res = await onConfirm(toImport);
      setResult(res);
      setStage('result');
    } catch (err: any) {
      alert('导入失败: ' + (err?.response?.data?.detail || err.message));
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setStage('upload');
    setRows([]);
    setSelected(new Set());
    setResult(null);
    if (fileRef.current) fileRef.current.value = '';
    onClose();
    if (stage === 'result') onDone();
  };

  return (
    <Modal open={open} onClose={handleClose} title={title}>
      {stage === 'upload' && (
        <div className="space-y-3">
          <p className="text-sm text-gray-500">支持 CSV 文件，表头支持中英文双名，编码自动识别 UTF-8/GBK</p>
          <input type="file" accept=".csv" ref={fileRef} onChange={handleFile} className="w-full text-sm" />
          {loading && <p className="text-sm text-gray-400">解析中...</p>}
        </div>
      )}

      {stage === 'preview' && (
        <div className="space-y-3">
          <div className="flex gap-3 text-sm">
            <Badge variant="success">{summary.ok} 条正常</Badge>
            <Badge variant="danger">{summary.error} 条错误</Badge>
            <Badge>{selected.size} 条已选</Badge>
          </div>
          <div className="max-h-64 overflow-auto border rounded">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 text-left text-gray-600 sticky top-0">
                  <th className="px-2 py-1 w-8">
                    <input type="checkbox" onChange={toggleAll} checked={rows.filter(r => r.status === 'ok').every(r => selected.has(r.index))} />
                  </th>
                  <th className="px-2 py-1">#</th>
                  {headers.slice(0, 6).map(h => <th key={h} className="px-2 py-1">{h}</th>)}
                  <th className="px-2 py-1">状态</th>
                </tr>
              </thead>
              <tbody>
                {rows.map(row => (
                  <tr key={row.index} className={`border-t ${row.status === 'error' ? 'bg-red-50' : ''}`}>
                    <td className="px-2 py-1">
                      <input type="checkbox" checked={selected.has(row.index)} onChange={() => toggleRow(row.index)} disabled={row.status === 'error'} />
                    </td>
                    <td className="px-2 py-1 text-gray-400">{row.index + 1}</td>
                    {headers.slice(0, 6).map(h => (
                      <td key={h} className="px-2 py-1 max-w-[120px] truncate">{row.data[h] || ''}</td>
                    ))}
                    <td className="px-2 py-1">
                      {row.status === 'error' ? <span className="text-red-500 text-xs" title={row.msg}>{row.msg}</span> : <Badge variant="success">OK</Badge>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="flex gap-2">
            <Button onClick={handleConfirm} disabled={loading}>确认导入 ({selected.size} 条)</Button>
            <Button variant="secondary" onClick={handleClose}>取消</Button>
          </div>
        </div>
      )}

      {stage === 'result' && (
        <div className="space-y-3">
          <p className="text-lg font-medium text-green-600">导入完成</p>
          <p className="text-sm text-gray-600">成功: {result?.success} 条</p>
          {result?.errors && result.errors.length > 0 && (
            <div className="text-sm text-red-500">
              失败: {result.errors.length} 条
              {result.errors.map((e: any, i: number) => <div key={i}>#{e.row}: {e.msg}</div>)}
            </div>
          )}
          <Button onClick={handleClose}>完成</Button>
        </div>
      )}
    </Modal>
  );
}
