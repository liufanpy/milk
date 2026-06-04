import { useQuery } from '@tanstack/react-query';
import { dashboardApi } from '../services/api';

export default function OperationLogsPage() {
  const { data: logs = [], isLoading } = useQuery({ queryKey: ['logs'], queryFn: dashboardApi.getOperationLogs });

  return (
    <div>
      <h2 className="text-xl font-bold mb-4">操作日志</h2>
      <div className="bg-white rounded-lg border overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b bg-gray-50 text-left text-gray-600">
            <th className="px-4 py-3">#</th><th className="px-4 py-3">操作</th><th className="px-4 py-3">实体类型</th><th className="px-4 py-3">实体ID</th><th className="px-4 py-3">时间</th>
          </tr></thead>
          <tbody>
            {isLoading ? <tr><td colSpan={5} className="text-center py-8 text-gray-400">加载中...</td></tr> :
              logs.length === 0 ? <tr><td colSpan={5} className="text-center py-8 text-gray-400">暂无日志</td></tr> :
                logs.map((log: any) => (
                  <tr key={log.id} className="border-b hover:bg-gray-50">
                    <td className="px-4 py-3">#{log.id}</td>
                    <td className="px-4 py-3">{log.action}</td>
                    <td className="px-4 py-3">{log.entity_type}</td>
                    <td className="px-4 py-3">{log.entity_id || '-'}</td>
                    <td className="px-4 py-3 text-gray-500">{new Date(log.created_at).toLocaleString()}</td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
